"""The list of apps to audit: package, which sheet tab, how to drive it.

Each app is one tab in the same checklist sheet, so an entry is mostly a
package plus that tab's `gid`. Optional fields override the driver defaults for
apps whose splash logo sits elsewhere or whose home screen is named
differently. Adding an app is one entry, never a code change.

The file takes either shape:

    [ {app}, {app} ]                       # apps only
    { "sheet": "<url>", "apps": [ {app} ] }  # apps plus the sheet they live in

The second exists because the registry held each app's `gid` but not the URL
those gids point into, so the other half of "which checklist" had to be typed
on every run and kept in step by hand wherever the audit was scheduled.

The file is a cache, not a guest list. Every tab in the sheet declares its own
`Package name`, so an app missing from here is still auditable -- `resolve_packages`
asks the sheet. Being absent from `apps.json` means "nobody wrote it down yet",
never "not allowed".
"""
import json
from pathlib import Path

DEFAULT_REGISTRY = Path(__file__).parent / "apps.json"
REQUIRED_FIELDS = ("package", "gid")


def sheet_url_for(base_sheet_url: str, gid: str) -> str:
    """Point a sheet URL at one app's tab."""
    base = base_sheet_url.split("#")[0].split("?")[0]
    return f"{base}?gid={gid}#gid={gid}"


def _read(path: Path | str) -> tuple[str | None, list[dict]]:
    """Parse either registry shape into (sheet, apps). SystemExit on bad input."""
    path = Path(path)
    if not path.exists():
        raise SystemExit(f"Không thấy registry: {path} (xem apps.example.json)")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"Registry không phải JSON hợp lệ: {path} -- {e}")

    if isinstance(data, dict):
        sheet, apps = data.get("sheet"), data.get("apps")
        if not isinstance(apps, list):
            raise SystemExit(f'Registry dạng object phải có "apps" là một list: {path}')
    else:
        sheet, apps = None, data
    if not isinstance(apps, list):
        raise SystemExit(f"Registry phải là một list các app, hoặc object có \"apps\": {path}")

    for i, app in enumerate(apps):
        missing = [f for f in REQUIRED_FIELDS if not app.get(f)]
        if missing:
            raise SystemExit(f"App #{i} trong {path} thiếu field: {', '.join(missing)}")
    return sheet, apps


def load_apps(path: Path | str = DEFAULT_REGISTRY) -> list[dict]:
    """Read and validate the registry. Raises SystemExit with a usable message."""
    return _read(path)[1]


def registry_sheet(path: Path | str = DEFAULT_REGISTRY) -> str | None:
    """The base checklist URL the registry declares, if it declares one."""
    return _read(path)[0]


def resolve_packages(wanted: list[str], apps: list[dict], sheet: str | None) -> list[dict]:
    """The entries to audit for the packages asked for, registry or not.

    The registry answers instantly when it knows the package. When it does not,
    the sheet is asked directly -- a package typed by hand is not required to
    have been written down first. Refusal is kept for the two cases where there
    is genuinely nothing to audit against: no tab declares the package, or two
    tabs do and picking one silently would diff against the wrong checklist.
    """
    from package_verifier import is_package_name
    from sheet_tabs import gids_by_package  # network + heavier deps, only if needed

    known = {app["package"]: app for app in apps}
    chosen = [known[pkg] for pkg in wanted if pkg in known]
    missing = [pkg for pkg in wanted if pkg not in known]
    if not missing:
        return chosen

    # An app name typed where a package belongs would otherwise be reported as
    # "the sheet has no tab for it", which sends the reader to the sheet to look
    # for something that was never a package.
    shapeless = [pkg for pkg in missing if not is_package_name(pkg)]
    if shapeless:
        raise SystemExit(
            f"Không phải package id: {', '.join(shapeless)}. "
            "Cần dạng com.abc.xyz, không phải tên app."
        )

    if not sheet:
        raise SystemExit(
            f"Không tra được tab cho: {', '.join(missing)} -- registry chưa khai \"sheet\". "
            "Truyền --sheet hoặc thêm app vào registry."
        )

    gids = gids_by_package(sheet)
    # A package added to the sheet after the tab list was cached looks identical
    # to one the sheet never had, so re-read before calling it missing.
    if any(pkg not in gids for pkg in missing):
        gids = gids_by_package(sheet, refresh=True)

    for pkg in missing:
        found = gids.get(pkg, [])
        if len(found) == 1:
            chosen.append({"package": pkg, "gid": found[0]})
        elif found:
            raise SystemExit(
                f"Sheet có {len(found)} tab cùng khai {pkg} (gid {', '.join(found)}). "
                "Chọn bừa là đối chiếu nhầm checklist -- thêm entry vào registry với gid muốn dùng."
            )
        else:
            raise SystemExit(
                f"Sheet không có tab nào khai {pkg}: chưa có checklist để đối chiếu. "
                "Kiểm tra lại package, hoặc nhờ ads-team thêm tab."
            )
    return chosen

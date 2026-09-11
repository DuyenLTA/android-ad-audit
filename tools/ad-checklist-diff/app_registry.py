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

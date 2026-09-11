"""Resolve a typed app name to a package.

    python find_app.py Nexus
    python find_app.py --device "AI Video"   # mọi app đang cài, không cần registry

Prints one line per match. Exit 0 on a single match, 1 on none, 2 on several --
so the caller can tell "pick one" apart from "no such app" instead of guessing
either way.

`--device` sweeps the phone instead of the registry, matching the name each app
shows on its icon. That is the name people know; the registry's label is an
internal nickname and the package id is not something anyone should have to
type.
"""
import argparse
import json
import sys
from pathlib import Path

from app_label import match_apps, names_for, screen_name
from app_registry import DEFAULT_REGISTRY, load_apps, registry_sheet
from device_apps import installed_packages, labels
from sheet_tabs import gids_by_package


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="tên app trên màn hình, label, hoặc package")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    parser.add_argument(
        "--device", action="store_true",
        help="tìm trong mọi app đang cài trên máy, bỏ qua registry",
    )
    parser.add_argument(
        "--refresh-tabs", action="store_true",
        help="đọc lại danh sách tab trong sheet (khi vừa thêm app mới)",
    )
    parser.add_argument(
        "--add", action="store_true",
        help="ghi app tìm được vào registry (chỉ khi gid đã xác định)",
    )
    args = parser.parse_args()

    if args.device:
        found = labels(installed_packages())
        apps = [{"package": pkg, "label": label} for pkg, label in sorted(found.items())]
        matches = match_apps(args.query, apps, screen_name_fn=lambda p: None)
        if args.add and len(matches) == 1:
            _add_to_registry(matches[0], args.registry, args.refresh_tabs)
        _report_device(args.query, apps, matches, args.registry, args.refresh_tabs)
        return

    apps = load_apps(args.registry)
    matches = match_apps(args.query, apps)

    if not matches:
        print(f"Không app nào khớp {args.query!r}. Registry đang có:", file=sys.stderr)
        for app in apps:
            print(f"  {app['package']}  ({' · '.join(names_for(app))})", file=sys.stderr)
        sys.exit(1)

    for app in matches:
        shown = screen_name(app["package"]) or app.get("label") or app["package"]
        print(f"{app['package']}  ({shown})")
    sys.exit(0 if len(matches) == 1 else 2)


def _tab_for(package: str, registry: str, refresh: bool) -> str:
    """The checklist tab this app declares itself in, if the sheet says so."""
    sheet = registry_sheet(registry)
    if not sheet:
        return ""
    try:
        gids = gids_by_package(sheet, refresh=refresh).get(package, [])
    except Exception:  # sheet không đọc được thì vẫn trả package, đừng chết cả lệnh
        return ""
    if len(gids) == 1:
        return f"  gid={gids[0]}"
    if gids:
        # Hai tab cùng khai một app: chọn bừa là đối chiếu nhầm checklist.
        return f"  gid=? ({', '.join(gids)} — nhiều tab cùng khai app này)"
    return "  gid=? (sheet không có tab nào khai package này)"


def _add_to_registry(app: dict, registry: str, refresh: bool) -> None:
    """Write the entry the audit needs, using only what the sheet itself declared.

    Nothing here is invented: the package comes from the device, the gid from the
    tab that names that package, the label from the app's own icon. An app the
    sheet does not cover is left out rather than registered against a guess.
    """
    sheet = registry_sheet(registry)
    gids = gids_by_package(sheet, refresh=refresh).get(app["package"], []) if sheet else []
    if len(gids) != 1:
        return

    path = Path(registry)
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data["apps"] if isinstance(data, dict) else data
    if any(e["package"] == app["package"] for e in entries):
        return

    entries.append({"label": app["label"], "package": app["package"], "gid": gids[0]})
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Đã thêm vào registry: {app['label']} (gid={gids[0]})", file=sys.stderr)


def _report_device(
    query: str, apps: list[dict], matches: list[dict], registry: str, refresh: bool
) -> None:
    """Same contract as the registry path, so callers branch on exit code only."""
    if not matches:
        print(f"Không app nào đang cài khớp {query!r}.", file=sys.stderr)
        print(f"Máy đang có {len(apps)} app bên thứ ba.", file=sys.stderr)
        sys.exit(1)
    for app in matches:
        print(f"{app['package']}  ({app['label']}){_tab_for(app['package'], registry, refresh)}")
    sys.exit(0 if len(matches) == 1 else 2)


if __name__ == "__main__":
    main()

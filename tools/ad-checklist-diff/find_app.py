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
import sys

from app_label import match_apps, names_for, screen_name
from app_registry import DEFAULT_REGISTRY, load_apps
from device_apps import installed_packages, labels


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="tên app trên màn hình, label, hoặc package")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    parser.add_argument(
        "--device", action="store_true",
        help="tìm trong mọi app đang cài trên máy, bỏ qua registry",
    )
    args = parser.parse_args()

    if args.device:
        found = labels(installed_packages())
        apps = [{"package": pkg, "label": label} for pkg, label in sorted(found.items())]
        matches = match_apps(args.query, apps, screen_name_fn=lambda p: None)
        _report_device(args.query, apps, matches)
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


def _report_device(query: str, apps: list[dict], matches: list[dict]) -> None:
    """Same contract as the registry path, so callers branch on exit code only."""
    if not matches:
        print(f"Không app nào đang cài khớp {query!r}.", file=sys.stderr)
        print(f"Máy đang có {len(apps)} app bên thứ ba.", file=sys.stderr)
        sys.exit(1)
    for app in matches:
        print(f"{app['package']}  ({app['label']})")
    sys.exit(0 if len(matches) == 1 else 2)


if __name__ == "__main__":
    main()

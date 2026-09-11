"""Resolve a typed app name to packages in the registry.

    python find_app.py Nexus
    python find_app.py "AI Video"

Prints one line per match: package, then the names it answered to. Exit 0 on a
single match, 1 on none, 2 on several -- so the caller can tell "pick one" apart
from "no such app" instead of guessing either way.
"""
import argparse
import sys

from app_label import match_apps, names_for, screen_name
from app_registry import DEFAULT_REGISTRY, load_apps


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="tên app trên màn hình, label, hoặc package")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    args = parser.parse_args()

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


if __name__ == "__main__":
    main()

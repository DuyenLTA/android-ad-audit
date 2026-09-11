"""Ask the installed build whether it contains given strings.

Exists because every judge agent was writing its own zipfile sweep, spending
minutes on it, and reaching for UTF-8 only -- which reports a placement as
missing from a build that ships it, since dex stores strings UTF-16LE too.

    python apk_strings.py <package> show_inter_feature 4070123043
    python apk_strings.py --apk build.apk ca-app-pub-1/2

Prints one line per needle: CÓ with the entries holding it, or KHÔNG. Exit code
1 when at least one needle is absent, so a script can branch on it.
"""
import argparse
import os
import sys

from apk_source import apk_contains, base_apk, cache_path, device_version_code


def resolve_apk(package: str) -> str:
    """The cached APK for the installed build, pulling it only if need be."""
    version_code = device_version_code(package)
    if version_code:
        cached = cache_path(package, version_code)
        if os.path.exists(cached):
            return cached
    path, _ephemeral = base_apk(package)
    if not path:
        raise SystemExit(f"Không lấy được APK cho {package} (máy chưa cắm / app chưa cài)")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", help="package name, hoặc bỏ qua nếu dùng --apk")
    parser.add_argument("needles", nargs="+", help="các chuỗi cần tìm")
    parser.add_argument("--apk", help="đọc file APK này thay vì lấy từ máy")
    args = parser.parse_args()

    apk_path = args.apk or resolve_apk(args.package)
    print(f"APK: {apk_path}")
    hits = apk_contains(apk_path, args.needles)
    for needle, entries in hits.items():
        if entries:
            shown = ", ".join(entries[:4]) + (" …" if len(entries) > 4 else "")
            print(f"  CÓ    {needle}  ({shown})")
        else:
            print(f"  KHÔNG {needle}")
    sys.exit(0 if all(hits.values()) else 1)


if __name__ == "__main__":
    main()

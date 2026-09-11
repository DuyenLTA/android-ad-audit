"""Every app installed on the phone, by the name it shows on screen.

Typing a package name to identify an app you can see on the device is backwards,
and keeping a hand-written list of them in sync is worse. The device already
knows what is installed; the only missing piece is the launcher label, and that
lives in the APK.

Pulling a whole APK to read one string costs 50MB per app. The device has
`unzip`, so only the two entries that carry the label are fetched -- the binary
manifest and the resource table, about 3.5MB, under half a second per app -- and
stitched back into a stub APK that `aapt2 dump badging` reads happily.

Labels are cached per build, so the sweep is paid once and a reinstall of the
same versionCode costs nothing.
"""
import json
import os
import re
import subprocess
import zipfile
from concurrent.futures import ThreadPoolExecutor

from apk_source import CACHE_DIR, device_apk_path, find_aapt2
from app_label import LABEL_RE

LABEL_CACHE = os.path.join(CACHE_DIR, "app-labels.json")
VERSION_RE = re.compile(r"^package:(\S+)\s+versionCode:(\S+)$")
ENTRIES = ("AndroidManifest.xml", "resources.arsc")


def installed_packages(serial: str | None = None) -> list[str]:
    """Third-party packages on the device -- the apps someone chose to install."""
    cmd = ["adb"] + (["-s", serial] if serial else []) + [
        "shell", "cmd", "package", "list", "packages", "-3",
    ]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=30).stdout
    except (subprocess.SubprocessError, OSError):
        return []
    return sorted(
        line.strip()[len("package:"):]
        for line in out.splitlines()
        if line.strip().startswith("package:")
    )


def installed_versions(serial: str | None = None) -> dict[str, str]:
    """versionCode of every third-party package, in one call.

    Asking per package cost an adb round trip each -- 2 seconds across a phone
    holding 85 apps, spent entirely on deciding whether a cached label was still
    good. The package manager will list them all at once.
    """
    cmd = ["adb"] + (["-s", serial] if serial else []) + [
        "shell", "cmd", "package", "list", "packages", "-3", "--show-versioncode",
    ]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=30).stdout
    except (subprocess.SubprocessError, OSError):
        return {}
    versions = {}
    for line in out.splitlines():
        found = VERSION_RE.match(line.strip())
        if found:
            versions[found.group(1)] = found.group(2)
    return versions


def _entry_bytes(apk_path: str, entry: str, serial: str | None) -> bytes:
    """One file out of an APK, extracted on the device and streamed back."""
    cmd = ["adb"] + (["-s", serial] if serial else []) + [
        "exec-out", f"unzip -p {apk_path} {entry}",
    ]
    try:
        return subprocess.run(cmd, capture_output=True, timeout=180).stdout
    except (subprocess.SubprocessError, OSError):
        return b""


def stub_apk(package: str, out_path: str, serial: str | None = None) -> str | None:
    """A stub holding just enough of the app for aapt2 to resolve its label."""
    apk_path = device_apk_path(package)
    if not apk_path:
        return None
    blobs = {entry: _entry_bytes(apk_path, entry, serial) for entry in ENTRIES}
    if not blobs["AndroidManifest.xml"]:
        return None
    with zipfile.ZipFile(out_path, "w") as zf:
        for entry, blob in blobs.items():
            if blob:
                zf.writestr(entry, blob)
    return out_path


def read_label(package: str, serial: str | None = None, aapt2: str | None = None) -> str | None:
    aapt2 = aapt2 or find_aapt2()
    if not aapt2:
        return None
    os.makedirs(CACHE_DIR, exist_ok=True)
    stub = os.path.join(CACHE_DIR, f"{package}-stub.apk")
    try:
        if not stub_apk(package, stub, serial):
            return None
        dump = subprocess.run(
            [aapt2, "dump", "badging", stub], capture_output=True, text=True, timeout=60
        ).stdout
    except (subprocess.SubprocessError, OSError):
        return None
    finally:
        if os.path.exists(stub):
            os.unlink(stub)
    found = LABEL_RE.search(dump)
    return found.group(1) if found else None


def _load_cache() -> dict:
    try:
        with open(LABEL_CACHE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _save_cache(cache: dict) -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(LABEL_CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2, sort_keys=True)


def labels(
    packages: list[str],
    serial: str | None = None,
    workers: int = 4,
    read_label_fn=read_label,
    versions: dict[str, str] | None = None,
) -> dict[str, str]:
    """Launcher label per package, reading only what the cache is missing."""
    cache = _load_cache()
    if versions is None:
        versions = installed_versions(serial)
    known, wanted = {}, []
    for package in packages:
        version = versions.get(package)
        entry = cache.get(package)
        if entry and entry.get("version_code") == version and entry.get("label"):
            known[package] = entry["label"]
        else:
            wanted.append((package, version))

    if wanted:
        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            fetched = list(pool.map(lambda pv: read_label_fn(pv[0], serial), wanted))
        for (package, version), label in zip(wanted, fetched):
            if label:
                known[package] = label
                cache[package] = {"version_code": version, "label": label}
        _save_cache(cache)
    return known

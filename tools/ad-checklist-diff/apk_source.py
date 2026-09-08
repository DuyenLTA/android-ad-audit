"""Fetch the installed APK off the device and read compiled-in values from it.

Pure device/file access -- no checklist knowledge. `apk_verifier.py` decides
what the values mean for a checklist row.

A pulled APK is cached under its package + versionCode: pulling ~45MB on every
run is waste when the build has not changed, and versionCode (not versionName)
is the identity that actually increments per build.
"""
import glob
import os
import re
import subprocess
import tempfile
import zipfile
from shutil import which

APK_ID_BYTES_RE = re.compile(rb"ca-app-pub-\d+[/~]\d+")
AAPT2_VALUE_RE = re.compile(r'android:value\S*="([^"]+)"')
VERSION_CODE_RE = re.compile(r"versionCode=(\d+)")

MANIFEST_APP_ID_NAME = "com.google.android.gms.ads.APPLICATION_ID"
# Where compiled-in strings live. Images and other media are skipped -- scanning
# a 45MB APK entry by entry is otherwise dominated by assets that cannot hold
# an ad unit ID.
SCANNED_SUFFIXES = (".dex", ".arsc", ".json", ".xml", ".txt", ".properties")

CACHE_DIR = os.path.join(
    os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"),
    "ad-checklist-diff",
)


def find_aapt2() -> str | None:
    """aapt2 from the SDK's build-tools (highest version), else PATH."""
    roots = [
        os.environ.get("ANDROID_HOME"),
        os.environ.get("ANDROID_SDK_ROOT"),
        os.path.expanduser("~/Android/Sdk"),
        os.path.expanduser("~/Library/Android/sdk"),
    ]
    for root in roots:
        if not root:
            continue
        found = sorted(glob.glob(os.path.join(root, "build-tools", "*", "aapt2*")))
        if found:
            return found[-1]
    return which("aapt2")


def device_apk_path(package: str) -> str | None:
    """Path of the installed base APK on the device, per `pm path`."""
    out = subprocess.run(
        ["adb", "shell", "pm", "path", package], capture_output=True, text=True, timeout=20
    ).stdout
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("package:") and line.endswith("base.apk"):
            return line[len("package:"):]
    return None


def device_version_code(package: str) -> str | None:
    """The installed build's versionCode, per `dumpsys package`."""
    out = subprocess.run(
        ["adb", "shell", "dumpsys", "package", package],
        capture_output=True,
        text=True,
        timeout=60,
    ).stdout
    m = VERSION_CODE_RE.search(out)
    return m.group(1) if m else None


def cache_path(package: str, version_code: str) -> str:
    return os.path.join(CACHE_DIR, f"{package}-{version_code}.apk")


def _prune_older_cached_builds(package: str, keep: str) -> None:
    """Drop cached APKs of superseded builds -- only the installed one is useful."""
    for stale in glob.glob(os.path.join(CACHE_DIR, f"{package}-*.apk")):
        if stale != cache_path(package, keep):
            try:
                os.unlink(stale)
            except OSError:
                pass


def base_apk(package: str) -> tuple[str | None, bool]:
    """Local copy of the installed base APK, cached per build.

    Returns (path, ephemeral): ephemeral means the caller must delete the file,
    which happens only when the build's versionCode could not be read and the
    copy therefore cannot be keyed for reuse.
    """
    version_code = device_version_code(package)
    if version_code:
        cached = cache_path(package, version_code)
        if os.path.exists(cached) and zipfile.is_zipfile(cached):
            return cached, False

    apk_path = device_apk_path(package)
    if not apk_path:
        return None, False

    # Pull into a temp file *inside* the cache dir when the result is
    # cacheable: os.replace cannot rename across filesystems, and the system
    # temp dir is frequently a different one (tmpfs vs the home partition).
    if version_code:
        os.makedirs(CACHE_DIR, exist_ok=True)
        fd, local_apk = tempfile.mkstemp(suffix=".apk", prefix="adcheck_apk_", dir=CACHE_DIR)
    else:
        fd, local_apk = tempfile.mkstemp(suffix=".apk", prefix="adcheck_apk_")
    os.close(fd)
    pull = subprocess.run(
        ["adb", "pull", apk_path, local_apk], capture_output=True, text=True, timeout=600
    )
    if pull.returncode != 0:
        os.unlink(local_apk)
        return None, False
    if not version_code:
        return local_apk, True

    # Move into place only once the pull finished, so an interrupted pull can
    # never leave a truncated APK behind as a valid-looking cache entry.
    cached = cache_path(package, version_code)
    os.replace(local_apk, cached)
    _prune_older_cached_builds(package, version_code)
    return cached, False


def manifest_app_id(apk_path: str, aapt2: str) -> str | None:
    """The APPLICATION_ID meta-data value declared in the APK's manifest."""
    dump = subprocess.run(
        [aapt2, "dump", "xmltree", "--file", "AndroidManifest.xml", apk_path],
        capture_output=True,
        text=True,
        timeout=180,
    )
    if dump.returncode != 0:
        return None
    return app_id_from_xmltree(dump.stdout)


def app_id_from_xmltree(xmltree: str) -> str | None:
    """Pull APPLICATION_ID's sibling `android:value` out of aapt2's dump.

    aapt2 prints a meta-data element's attributes on consecutive lines, so the
    value belonging to a given name is the next `android:value` after it.
    """
    lines = xmltree.splitlines()
    for i, line in enumerate(lines):
        if MANIFEST_APP_ID_NAME not in line:
            continue
        for following in lines[i + 1 : i + 4]:
            m = AAPT2_VALUE_RE.search(following)
            if m:
                return m.group(1)
    return None


def apk_ad_ids(apk_path: str) -> set[str]:
    """Every AdMob ID string compiled into the APK (dex, resources, assets)."""
    ids: set[str] = set()
    with zipfile.ZipFile(apk_path) as zf:
        for info in zf.infolist():
            if not info.filename.endswith(SCANNED_SUFFIXES):
                continue
            with zf.open(info) as entry:
                blob = entry.read()
            ids.update(m.decode("ascii") for m in APK_ID_BYTES_RE.findall(blob))
    return ids

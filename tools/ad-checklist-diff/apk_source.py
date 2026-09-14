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
        # Where Android Studio installs the SDK on Windows by default.
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Android", "Sdk")
        if os.environ.get("LOCALAPPDATA")
        else None,
    ]
    for root in roots:
        if not root:
            continue
        found = sorted(glob.glob(os.path.join(root, "build-tools", "*", "aapt2*")))
        if found:
            return found[-1]
    return which("aapt2")


def device_apk_paths(package: str) -> list[str]:
    """Every APK of the installed build: base first, then its splits.

    An app delivered as an app bundle keeps most of its code in split APKs, and
    a string compiled into one of those is absent from base.apk. Scanning only
    base therefore reports "không có trong build" for placements the build
    really ships. Plenty of apps on a normal phone are split this way.
    """
    out = subprocess.run(
        ["adb", "shell", "pm", "path", package], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20
    ).stdout
    paths = [
        line.strip()[len("package:"):]
        for line in out.splitlines()
        if line.strip().startswith("package:")
    ]
    # Base first: it is the one the manifest is read from.
    return sorted(paths, key=lambda p: not p.endswith("base.apk"))


def device_apk_path(package: str) -> str | None:
    """Path of the installed base APK on the device, per `pm path`."""
    for path in device_apk_paths(package):
        if path.endswith("base.apk"):
            return path
    return None


def device_version_code(package: str) -> str | None:
    """The installed build's versionCode, per `dumpsys package`."""
    out = subprocess.run(
        ["adb", "shell", "dumpsys", "package", package],
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        timeout=60,
    ).stdout
    m = VERSION_CODE_RE.search(out)
    return m.group(1) if m else None


def cache_path(package: str, version_code: str, split: str | None = None) -> str:
    """Where a pulled APK lives. `split` names a non-base APK of the same build.

    Base keeps the historic name, so caches pulled before splits were handled
    are still found instead of being silently re-pulled.
    """
    stem = f"{package}-{version_code}"
    if split:
        stem += f"-{split}"
    return os.path.join(CACHE_DIR, f"{stem}.apk")


def _prune_older_cached_builds(package: str, keep: str) -> None:
    """Drop cached APKs of superseded builds -- only the installed one is useful."""
    keep_prefix = os.path.join(CACHE_DIR, f"{package}-{keep}")
    for stale in glob.glob(os.path.join(CACHE_DIR, f"{package}-*.apk")):
        # Every APK of the installed build shares this prefix: base is
        # "<pkg>-<vc>.apk" and its splits "<pkg>-<vc>-<split>.apk".
        if not stale.startswith(keep_prefix):
            try:
                os.unlink(stale)
            except OSError:
                pass


def _pull_apk(
    package: str, remote_path: str, version_code: str | None, split: str | None = None
) -> tuple[str | None, bool]:
    """Fetch one APK off the device, cached per build when that is possible."""
    if version_code:
        cached = cache_path(package, version_code, split)
        if os.path.exists(cached) and zipfile.is_zipfile(cached):
            return cached, False

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
        ["adb", "pull", remote_path, local_apk], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600
    )
    if pull.returncode != 0:
        os.unlink(local_apk)
        return None, False
    if not version_code:
        return local_apk, True

    # Move into place only once the pull finished, so an interrupted pull can
    # never leave a truncated APK behind as a valid-looking cache entry.
    cached = cache_path(package, version_code, split)
    os.replace(local_apk, cached)
    _prune_older_cached_builds(package, version_code)
    return cached, False


def base_apk(package: str) -> tuple[str | None, bool]:
    """Local copy of the installed base APK, cached per build.

    Returns (path, ephemeral): ephemeral means the caller must delete the file,
    which happens only when the build's versionCode could not be read and the
    copy therefore cannot be keyed for reuse.
    """
    version_code = device_version_code(package)
    apk_path = device_apk_path(package)
    if not apk_path:
        # No path means no device or no install -- but a cache entry from an
        # earlier run is still a usable copy of that build.
        if version_code:
            cached = cache_path(package, version_code)
            if os.path.exists(cached) and zipfile.is_zipfile(cached):
                return cached, False
        return None, False
    return _pull_apk(package, apk_path, version_code)


def build_apks(package: str) -> tuple[list[str], bool]:
    """Local copies of every APK of the installed build, base first.

    Same contract as `base_apk`, for the whole build rather than one file:
    (paths, ephemeral), ephemeral meaning the caller deletes them because the
    versionCode could not be read and the copies cannot be keyed for reuse.

    A split build keeps most of its code outside base.apk, so a scan of base
    alone reports strings as absent from a build that ships them.
    """
    remote = device_apk_paths(package)
    if not remote:
        return [], False
    if len(remote) == 1:
        path, ephemeral = base_apk(package)
        return ([path], ephemeral) if path else ([], False)

    version_code = device_version_code(package)
    paths, ephemeral = [], False
    for index, remote_path in enumerate(remote):
        # Index rather than the on-device filename: split names are stable
        # enough to read but not guaranteed unique across the list.
        split = None if index == 0 else f"split{index}"
        local, one_ephemeral = _pull_apk(package, remote_path, version_code, split)
        if not local:
            continue
        paths.append(local)
        ephemeral = ephemeral or one_ephemeral
    return paths, ephemeral


def manifest_app_id(apk_path: str, aapt2: str) -> str | None:
    """The APPLICATION_ID meta-data value declared in the APK's manifest."""
    dump = subprocess.run(
        [aapt2, "dump", "xmltree", "--file", "AndroidManifest.xml", apk_path],
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
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


def _as_paths(apk_path) -> list[str]:
    """One APK or several -- callers hold whichever the build turned out to be."""
    return [apk_path] if isinstance(apk_path, (str, os.PathLike)) else list(apk_path)


def apk_contains(apk_path, needles: list[str]) -> dict[str, list[str]]:
    """Which APK entries hold each literal string. Empty list means absent.

    The agent layer kept re-implementing this by hand and kept getting it half
    right: dex stores some strings UTF-16LE, so a UTF-8-only sweep reports a
    placement as missing from a build that ships it. Both encodings are checked
    here once, so "not in the build" means it.
    """
    wanted = [
        (needle, needle.encode("utf-8"), needle.encode("utf-16-le"))
        for needle in needles
    ]
    hits: dict[str, list[str]] = {needle: [] for needle in needles}
    paths = _as_paths(apk_path)
    for path in paths:
        # Name the split a hit came from, but only when there is more than one
        # APK -- otherwise every line grows a "base.apk/" nobody needs.
        prefix = "" if len(paths) == 1 else f"{os.path.basename(path)}/"
        with zipfile.ZipFile(path) as zf:
            for info in zf.infolist():
                with zf.open(info) as entry:
                    blob = entry.read()
                for needle, utf8, utf16 in wanted:
                    if utf8 in blob or utf16 in blob:
                        hits[needle].append(f"{prefix}{info.filename}")
    return hits


def apk_ad_ids(apk_path) -> set[str]:
    """Every AdMob ID string compiled into the build (dex, resources, assets).

    Takes one APK or the whole set: a split build keeps most of its code outside
    base.apk, so reading base alone under-reports what the build contains.
    """
    ids: set[str] = set()
    for path in _as_paths(apk_path):
        with zipfile.ZipFile(path) as zf:
            for info in zf.infolist():
                if not info.filename.endswith(SCANNED_SUFFIXES):
                    continue
                with zf.open(info) as entry:
                    blob = entry.read()
                ids.update(m.decode("ascii") for m in APK_ID_BYTES_RE.findall(blob))
    return ids

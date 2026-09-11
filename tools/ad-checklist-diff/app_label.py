"""Find an app by the name it shows on the phone.

The registry's `label` is an internal nickname -- "AI Art" -- while the icon on
the device reads "Nexus AI - AI Video Generator". People type what they see, so
a lookup that only knows the nickname turns a correct name into "không tìm
thấy". The launcher label is declared in the APK, and the APK is already cached
per build, so it can be read without touching the device.

Matching is substring and case-insensitive across all the names an app answers
to. Several matches is not an error to resolve by guessing -- the caller is
expected to show them and let a person pick.
"""
import glob
import os
import re
import subprocess

from apk_source import CACHE_DIR, find_aapt2

LABEL_RE = re.compile(r"^application-label:'(.*)'$", re.M)


def cached_apk_for(package: str) -> str | None:
    """Any cached build of this app -- the launcher label rarely changes."""
    builds = sorted(glob.glob(os.path.join(CACHE_DIR, f"{package}-*.apk")))
    return builds[-1] if builds else None


def apk_app_label(apk_path: str, aapt2: str | None = None) -> str | None:
    """The app's launcher label, as declared in the APK."""
    aapt2 = aapt2 or find_aapt2()
    if not aapt2:
        return None
    try:
        dump = subprocess.run(
            [aapt2, "dump", "badging", apk_path],
            capture_output=True, text=True, timeout=60,
        ).stdout
    except (subprocess.SubprocessError, OSError):
        return None
    found = LABEL_RE.search(dump)
    return found.group(1) if found else None


def screen_name(package: str) -> str | None:
    """The on-screen name, read from whatever build of this app is cached."""
    apk = cached_apk_for(package)
    return apk_app_label(apk) if apk else None


def names_for(app: dict, screen_name_fn=screen_name) -> list[str]:
    """Every name this app answers to, nickname and real name alike."""
    names = [app.get("label"), app["package"], *app.get("aliases", [])]
    names.append(screen_name_fn(app["package"]))
    return [n for n in names if n]


def match_apps(query: str, apps: list[dict], screen_name_fn=screen_name) -> list[dict]:
    """Registry entries answering to `query`, exact matches winning outright.

    Without the exact-match rule a registry holding both "AI Art" and "AI Art
    Pro" would make the shorter name permanently ambiguous with itself.
    """
    wanted = query.strip().lower()
    if not wanted:
        return []

    exact, partial = [], []
    for app in apps:
        names = [n.lower() for n in names_for(app, screen_name_fn)]
        if any(wanted == n for n in names):
            exact.append(app)
        elif any(wanted in n for n in names):
            partial.append(app)
    return exact or partial

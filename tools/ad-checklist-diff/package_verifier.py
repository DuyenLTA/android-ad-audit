"""Verify Android package-name checklist rows against the connected device.

Package names (and the AdMob App ID's *own* line under UserMessagingPlatform/
AdsConsentManager) are handled separately from the FOR_TESTER-family log diff
because the package name itself is never printed in any trusted log line --
there's nothing to grep for. Instead we ask the device directly via
`adb shell pm list packages`. GUI-only (see streamlit_app.py): check_ads.py's
CLI never touches a device, by design.
"""
import re
import subprocess

PACKAGE_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*){2,}$")


def is_package_name(value: str) -> bool:
    """Shape check: 3+ dot-separated segments, no hyphens/tildes -- distinguishes a
    package name from every other checklist value shape (ad unit IDs, tokens, env names)."""
    return bool(PACKAGE_RE.fullmatch(value))


def installed_packages() -> set[str]:
    """Every package name currently installed on the connected device."""
    out = subprocess.run(
        ["adb", "shell", "pm", "list", "packages"], capture_output=True, text=True, timeout=15
    ).stdout
    return {line.strip()[len("package:"):] for line in out.splitlines() if line.strip()}


def verify_package_rows(result: dict, installed_packages_fn=installed_packages) -> None:
    """Override found-status for package-name-shaped checklist rows in place.

    If the adb query itself fails (device unplugged between Start and Stop),
    leave those rows at whatever the log diff already decided rather than
    crashing report generation.
    """
    package_rows = [
        r for rows in result["sections"].values() for r in rows if is_package_name(r["value"])
    ]
    if not package_rows:
        return
    try:
        installed = installed_packages_fn()
    except (subprocess.SubprocessError, OSError):
        return
    for r in package_rows:
        r["found"] = r["value"] in installed

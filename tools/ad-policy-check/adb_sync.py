"""The few adb calls the evidence side needs, independent of whichever driver runs the app.

The driver (rc-check's fo_flow) has its own async adb client; the recorder, the
activity sampler and the click prober only need these, so they stay usable with
any driver.
"""
import asyncio
import re
import subprocess

TOP_RESUMED_RE = re.compile(r"topResumedActivity=ActivityRecord\{\S+ \S+ (\S+?)[ }]")
RESUMED_RE = re.compile(r"ResumedActivity: ActivityRecord\{\S+ \S+ (\S+?)[ }]")


def adb(serial: str, *args: str, timeout: int = 30) -> str:
    return subprocess.run(["adb", "-s", serial, *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout).stdout


def top_activity(serial: str) -> str | None:
    out = adb(serial, "shell", "dumpsys", "activity", "activities", timeout=15)
    m = TOP_RESUMED_RE.search(out) or RESUMED_RE.search(out)
    return m.group(1) if m else None


def safe_dump(serial: str, remote: str) -> str:
    """uiautomator dump that never hands back an older file: remove first, check the result,
    retry once (a dump during a window change fails with "null root node"). "" when it failed."""
    for _ in range(2):
        try:
            adb(serial, "shell", "rm", "-f", remote)
            adb(serial, "shell", "uiautomator", "dump", remote, timeout=60)
            xml = adb(serial, "exec-out", "cat", remote, timeout=60)
        except subprocess.TimeoutExpired:
            # uiautomator waits for the UI to go idle; a screen that never stops animating (a looping
            # video in a popup) hangs it. Kill the stuck dumper and try again instead of ending the pass.
            try:
                adb(serial, "shell", "pkill", "-f", "uiautomator", timeout=10)
            except subprocess.TimeoutExpired:
                pass
            continue
        if "<hierarchy" in xml:
            return xml
    return ""


def screencap_png(serial: str) -> bytes:
    png = subprocess.run(["adb", "-s", serial, "exec-out", "screencap", "-p"],
                         capture_output=True, timeout=20).stdout
    return png if png.startswith(b"\x89PNG") else b""


async def a_top_activity(serial: str) -> str | None:
    return await asyncio.to_thread(top_activity, serial)


async def a_tap(serial: str, x: int, y: int) -> None:
    await asyncio.to_thread(adb, serial, "shell", "input", "tap", str(int(x)), str(int(y)))


async def a_key(serial: str, key: str) -> None:
    await asyncio.to_thread(adb, serial, "shell", "input", "keyevent", key)

"""ADB UI primitives: what screen is up, and where to tap on it.

Element-based, not pixel-based: the driver asks for a node by `resource-id`,
`text` or `content-desc` and taps the centre of its reported bounds, so an
onboarding layout that shifts between builds still works. The one exception is
the splash screen -- it lasts ~5s while `uiautomator dump` alone costs ~1s, so
the logo has to be tapped by coordinate there (see device_driver).

Every device call goes through an injectable `run` so the parsing logic is
testable without a phone attached.
"""
import re
import subprocess

FOCUS_RE = re.compile(r"mCurrentFocus=Window\{\S+ \S+ ([^/\s}]+)/?(\S*)\}")
SIZE_RE = re.compile(r"Physical size:\s*(\d+)x(\d+)")
BOUNDS_RE = re.compile(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"')
NODE_RE = re.compile(r"<node\b[^>]*/?>")

DUMP_REMOTE_PATH = "/sdcard/adcheck-ui.xml"


def adb_run(args: list[str], serial: str | None = None, timeout: int = 30) -> str:
    """Run an adb command against one device, returning stdout."""
    cmd = ["adb"]
    if serial:
        cmd += ["-s", serial]
    cmd += args
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout


def screen_size(run=adb_run) -> tuple[int, int] | None:
    m = SIZE_RE.search(run(["shell", "wm", "size"]))
    return (int(m.group(1)), int(m.group(2))) if m else None


def focused_package_activity(run=adb_run) -> tuple[str, str] | None:
    """(package, activity) currently focused, per `dumpsys window`.

    The package half matters as much as the activity: tapping ad content can
    throw the device into a completely different app, and a run once mistook
    YouTube's own `InternalMainActivity` for the app's Home screen.
    """
    out = run(["shell", "dumpsys", "window"])
    for line in out.splitlines():
        if "mCurrentFocus" in line:
            m = FOCUS_RE.search(line)
            if m:
                return m.group(1), m.group(2)
    return None


def focused_activity(run=adb_run) -> str | None:
    """Activity half of the focused window, as `package/activity`."""
    found = focused_package_activity(run=run)
    return f"{found[0]}/{found[1]}" if found else None


def ui_xml(run=adb_run) -> str:
    """Dump the current view hierarchy as XML."""
    run(["shell", "uiautomator", "dump", DUMP_REMOTE_PATH], timeout=60)
    xml = run(["exec-out", "cat", DUMP_REMOTE_PATH], timeout=60)
    run(["shell", "rm", "-f", DUMP_REMOTE_PATH])
    return xml


def find_node_center(
    xml: str,
    resource_id: str | None = None,
    text: str | None = None,
    content_desc: str | None = None,
) -> tuple[int, int] | None:
    """Centre of the first node matching every given attribute.

    `resource_id` matches by suffix so callers can pass `id/btnNextOnboarding`
    without the package prefix, which differs per app.
    """
    for node in NODE_RE.findall(xml):
        if resource_id and not _attr(node, "resource-id").endswith(resource_id):
            continue
        if text is not None and _attr(node, "text") != text:
            continue
        if content_desc is not None and _attr(node, "content-desc") != content_desc:
            continue
        b = BOUNDS_RE.search(node)
        if not b:
            continue
        x1, y1, x2, y2 = (int(g) for g in b.groups())
        # Recycler views report off-screen/recycled rows as [0,0][0,0]; tapping
        # a zero-area node's "centre" would hit the screen corner.
        if x2 <= x1 or y2 <= y1:
            continue
        return (x1 + x2) // 2, (y1 + y2) // 2
    return None


# An interstitial's close control is whatever the ad creative's own locale
# calls it -- a real run showed a Portuguese "Fechar" inside an app whose
# language had just been set to something else entirely -- so matching one
# English label is not enough. Countdown-then-close means the control is also
# absent for the first few seconds.
CLOSE_LABELS = {
    "close", "fechar", "cerrar", "fermer", "schliessen", "schließen", "chiudi",
    "закрыть", "đóng", "tutup", "关闭", "關閉", "닫기", "閉じる", "बंद करें",
    "skip", "bỏ qua", "saltar", "pular",
}


def _looks_like_close(value: str) -> bool:
    """Whether a label reads as close/skip, in any of the locales seen.

    Substring, not equality: real controls say "Skip ad", "Bỏ qua quảng cáo",
    "Close ad" rather than the bare word. Long strings are ignored so ad body
    copy that merely mentions the word cannot be mistaken for the control.
    """
    value = value.strip().lower()
    if not value or len(value) > 24:
        return False
    return any(label in value for label in CLOSE_LABELS)


def find_close_center(xml: str) -> tuple[int, int] | None:
    """Centre of a close/skip control, matched across locales."""
    for node in NODE_RE.findall(xml):
        text = _attr(node, "text")
        desc = _attr(node, "content-desc")
        if _looks_like_close(text) or _looks_like_close(desc):
            b = BOUNDS_RE.search(node)
            if not b:
                continue
            x1, y1, x2, y2 = (int(g) for g in b.groups())
            if x2 <= x1 or y2 <= y1:
                continue
            return (x1 + x2) // 2, (y1 + y2) // 2
    return None


def _attr(node: str, name: str) -> str:
    m = re.search(rf'{name}="([^"]*)"', node)
    return m.group(1) if m else ""


def tap(x: int, y: int, run=adb_run) -> None:
    run(["shell", "input", "tap", str(x), str(y)])


def spam_tap(x: int, y: int, times: int, run=adb_run) -> None:
    """Tap one spot many times in a single shell round-trip.

    Looping inside the device shell matters: each `adb shell` costs ~100ms of
    round-trip, which is most of the splash screen's lifetime. The tester log
    dump this triggers does not appear at all otherwise -- a launch with no taps
    produces zero FOR_TESTER lines.
    """
    run(
        ["shell", f"for i in $(seq 1 {times}); do input tap {x} {y}; done"],
        timeout=120,
    )


def swipe_left(run=adb_run, duration_ms: int = 300) -> None:
    """Page a horizontal pager forward (finger moves right-to-left).

    Onboarding page 3 has no Next button -- it only advances by swipe.
    """
    size = screen_size(run=run) or (1080, 2280)
    w, h = size
    run(
        [
            "shell",
            "input",
            "swipe",
            str(int(w * 0.8)),
            str(h // 2),
            str(int(w * 0.2)),
            str(h // 2),
            str(duration_ms),
        ]
    )


def key_event(keycode: str, run=adb_run) -> None:
    run(["shell", "input", "keyevent", keycode])

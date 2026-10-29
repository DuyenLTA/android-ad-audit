"""Popup windows an app draws over its own screen, read from `dumpsys input`.

On a test device every native ad comes with the "AdMob native ad validator"
popup, and a new one is stacked on each ad refresh. On the question screen it
covers the middle of the continue button, so a tap at the button's centre opens
the validator page instead of advancing. Tapping its Dismiss button does not
help: on the OPPO CPH2375 injected taps never close it (AIP882 4.3.0,
29/10/2026, five taps, still four popups stacked). What does work is tapping the
part of the continue button the popup leaves uncovered.

The popup is not in the `uiautomator dump` tree, but it is a window of its own
-- an activity-owned window smaller than the screen -- so its frame is listed
by the input dispatcher.
"""
import re

Rect = tuple[int, int, int, int]

WINDOW_RE = re.compile(
    r"name='Window\{\S+ \S+ [^/}\s]+/[^}]*\}'.*?visible=(true|false).*?"
    r"frame=\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]"
)


def popup_frames(dumpsys_input: str, width: int, height: int) -> list[Rect]:
    """Frames of visible activity-owned windows that do not fill the screen."""
    frames = set()
    for m in WINDOW_RE.finditer(dumpsys_input):
        if m.group(1) != "true":
            continue
        x1, y1, x2, y2 = (int(v) for v in m.groups()[1:])
        if x2 - x1 >= width and y2 - y1 >= height * 0.9:
            continue  # the activity's own full-screen window
        if x2 > x1 and y2 > y1:
            frames.add((x1, y1, x2, y2))
    return sorted(frames)


def uncovered_point(bounds: Rect, covers: list[Rect], step: int = 8) -> tuple[int, int] | None:
    """A point inside `bounds` that no cover hides: the centre if free, else the
    free spot nearest to it along the button's middle row. None if all hidden."""
    x1, y1, x2, y2 = bounds
    cy = (y1 + y2) // 2
    cx = (x1 + x2) // 2

    def free(x: int) -> bool:
        return not any(a <= x < c and b <= cy < d for a, b, c, d in covers)

    margin = min(16, (x2 - x1) // 4)
    xs = range(x1 + margin, x2 - margin + 1, step)
    for x in sorted(xs, key=lambda v: abs(v - cx)):
        if free(x):
            return x, cy
    return None

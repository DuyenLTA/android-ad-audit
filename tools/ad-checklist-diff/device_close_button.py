"""Find an interstitial's close control -- or decide there isn't one.

Two independent things have to hold before tapping, because getting this wrong
is expensive: a tap that misses the control lands on the ad creative, the
WebView turns it into a VIEW intent, and the run is suddenly inside YouTube
with its capture abandoned. That happened three times in one session; the log
showed `input tap 309 814` on a 1080x2148 screen and a youtube.com intent 0.7s
later.

  Label -- whatever the creative's own locale calls it. A real run showed a
  Portuguese "Fechar" inside an app set to another language entirely, so one
  English word is not enough. Substring, since controls say "Skip ad" rather
  than "skip"; long strings are excluded so ad body copy mentioning the word
  cannot pass for the control. Plenty of close buttons carry no word at all --
  just a glyph, or a resource id -- so those are matched too, by exact glyph
  (never as a substring: "x" appears inside ordinary words).

  Geometry -- close controls sit against an edge and are small. (309, 814) is
  mid-screen, which is where the creative is, not its close button.

Finding nothing is a useful answer: the caller falls back to BACK, which
dismisses the ad without any chance of clicking it.
"""
from device_ui import BOUNDS_RE, NODE_RE, _attr

CLOSE_LABELS = {
    "close", "fechar", "cerrar", "fermer", "schliessen", "schließen", "chiudi",
    "закрыть", "đóng", "tutup", "关闭", "關閉", "닫기", "閉じる", "बंद करें",
    "skip", "bỏ qua", "saltar", "pular",
}

# Close buttons that carry no label at all. Matched whole, after stripping:
# as a substring "x" would hit every word containing the letter.
CLOSE_GLYPHS = {"×", "✕", "✖", "✗", "⨯", "╳", "x", "✘", "⊗", "ⓧ", "[x]"}

# Ids the ad frames use for their own dismiss control, matched by suffix. These
# are the frame's button rather than anything the creative drew, so they are
# trusted ahead of a label match.
CLOSE_IDS = ("interstitial_close_button", "closeButton", "btnClose", "ad_close_button", "iv_close")

# Fractions of the screen. An edge band wide enough for a control with padding
# around it, and an area cap far above any real button but far below a creative.
TOP_BAND = 0.22
BOTTOM_BAND = 0.82
SIDE_BAND = 0.15
MAX_AREA = 0.06


def _looks_like_close(value: str) -> bool:
    value = value.strip()
    if not value:
        return False
    if value.lower() in CLOSE_GLYPHS or value in CLOSE_GLYPHS:
        return True
    lowered = value.lower()
    if len(lowered) > 24:
        return False
    return any(label in lowered for label in CLOSE_LABELS)


def _is_close_id(node: str) -> bool:
    resource_id = _attr(node, "resource-id")
    return any(resource_id.endswith(name) for name in CLOSE_IDS)


def _screen(xml: str) -> tuple[int, int]:
    """Screen extent, taken as the furthest corner any node reaches."""
    width = height = 0
    for node in NODE_RE.findall(xml):
        m = BOUNDS_RE.search(node)
        if m:
            _x1, _y1, x2, y2 = (int(g) for g in m.groups())
            width, height = max(width, x2), max(height, y2)
    return width, height


def _against_an_edge(cx: int, cy: int, width: int, height: int) -> bool:
    return (
        cy <= height * TOP_BAND
        or cy >= height * BOTTOM_BAND
        or cx <= width * SIDE_BAND
        or cx >= width * (1 - SIDE_BAND)
    )


def _corner_distance(cx: int, cy: int, width: int, height: int) -> int:
    """How far the centre sits from the nearest corner, squared."""
    return min(
        (cx - x) ** 2 + (cy - y) ** 2
        for x in (0, width)
        for y in (0, height)
    )


def find_close_center(xml: str) -> tuple[int, int] | None:
    """Centre of a credible close/skip control, or None to let BACK handle it."""
    width, height = _screen(xml)
    if not width or not height:
        return None

    best = None
    for node in NODE_RE.findall(xml):
        by_id = _is_close_id(node)
        if not (
            by_id
            or _looks_like_close(_attr(node, "text"))
            or _looks_like_close(_attr(node, "content-desc"))
        ):
            continue
        m = BOUNDS_RE.search(node)
        if not m:
            continue
        x1, y1, x2, y2 = (int(g) for g in m.groups())
        if x2 <= x1 or y2 <= y1:
            continue
        if (x2 - x1) * (y2 - y1) > MAX_AREA * width * height:
            continue
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        if not _against_an_edge(cx, cy, width, height):
            continue
        # Several may qualify (a creative's own "skip" plus the real control);
        # the one nearest a corner is the one the ad frame owns.
        # An id match is the ad frame's own control; a label match might be
        # something the creative drew to look like one. Rank ids first, then by
        # nearness to a corner.
        rank = (0 if by_id else 1, _corner_distance(cx, cy, width, height))
        if best is None or rank < best[0]:
            best = (rank, (cx, cy))
    return best[1] if best else None

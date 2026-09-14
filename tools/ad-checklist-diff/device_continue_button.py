"""Find the screen's primary continue button by what it is, not what it says.

The question screen's continue control is labelled by remote config: builds have
shipped "Go to Home", "Next" and "Get Started" for the same button. A label list
only ever covers the wordings someone has already met -- and only in the exact
casing they met them in, which is how a run met "Get Started" while the step
list said "Get started" and advanced nothing. The screen then never moves, and
the capture spends its whole timeout one tap from done.

What is stable is the node itself: the layout declares an id for it, and failing
that it is the labelled button below the content.

The hazard here is not missing the button, it is hitting the wrong one. This
screen carries a native ad *below* the continue button, and that ad's own call
to action is wider, lower and also a labelled Button -- "take the bottom-most
button" taps INSTALL, leaves for the Play Store, and bills the run as a click on
the very ad unit being audited. So ad subtrees are carved out by geometry before
anything is ranked: any node sitting inside the bounds of an ad-owned view is
not a candidate, whatever it looks like.
"""
from device_ui import BOUNDS_RE, NODE_RE, _attr, screen_extent

# Ids a continue button carries, matched by suffix. `btnNextQuestion` is this
# screen's; the others are the same control on neighbouring screens. An id match
# is the layout naming the button, so it outranks any inference from shape.
CONTINUE_IDS = (
    "btnNextQuestion",
    "btnNextOnboardingImage",
    "btnNextOnboarding",
    "btnContinue",
    "btnGetStarted",
    "btnStart",
    "btnNext",
)

# Id fragments that mean "this view belongs to an ad". Checked against the id's
# own name, segment-wise, so `btnAdd` is not read as an ad view.
AD_ID_MARKERS = ("ad_", "_ad", "nativead", "admob", "adview", "adcontainer", "banner")

# Fractions of the screen. The band starts below the answer grid; the width
# floor separates a call to action from an inline link; the area cap keeps a
# full-screen clickable container out.
BOTTOM_BAND = 0.45
MIN_WIDTH = 0.2
MAX_AREA = 0.25


def _bounds(node: str) -> tuple[int, int, int, int] | None:
    m = BOUNDS_RE.search(node)
    if not m:
        return None
    x1, y1, x2, y2 = (int(g) for g in m.groups())
    return (x1, y1, x2, y2) if x2 > x1 and y2 > y1 else None


def _id_name(node: str) -> str:
    """The id's own name, without the package prefix, lowercased."""
    return _attr(node, "resource-id").rsplit("/", 1)[-1].lower()


def _is_ad_view(node: str) -> bool:
    name = _id_name(node)
    if not name:
        return False
    return (
        name.startswith("ad_")
        or name.endswith("_ad")
        or "_ad_" in name
        or any(marker in name for marker in AD_ID_MARKERS if not marker.startswith(("ad_", "_ad")))
    )


def _ad_regions(xml: str) -> list[tuple[int, int, int, int]]:
    """Bounds of every ad-owned view on screen.

    An ad's own children are mostly unnamed -- the creative's media frame and
    its install button are found by sitting inside one of these, not by their
    own ids.
    """
    return [b for node in NODE_RE.findall(xml) if _is_ad_view(node) and (b := _bounds(node))]


def _inside_an_ad(cx: int, cy: int, regions: list[tuple[int, int, int, int]]) -> bool:
    return any(x1 <= cx <= x2 and y1 <= cy <= y2 for x1, y1, x2, y2 in regions)


def _has_label(node: str) -> bool:
    return bool(_attr(node, "text").strip() or _attr(node, "content-desc").strip())


def find_continue_center(xml: str) -> tuple[int, int] | None:
    """Centre of the screen's primary continue button, or None if none fits."""
    width, height = screen_extent(xml)
    if not width or not height:
        return None
    ad_regions = _ad_regions(xml)

    best = None
    for node in NODE_RE.findall(xml):
        if _attr(node, "clickable") != "true" or _attr(node, "enabled") == "false":
            continue
        by_id = _id_name(node).endswith(tuple(name.lower() for name in CONTINUE_IDS))
        if not by_id and not _has_label(node):
            continue
        b = _bounds(node)
        if not b:
            continue
        x1, y1, x2, y2 = b
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        # Before any ranking: never a node the ad drew, however button-shaped.
        if _is_ad_view(node) or _inside_an_ad(cx, cy, ad_regions):
            continue
        if not by_id:
            # Shape only has to hold for an inferred button; a declared one is
            # allowed to be as small or as high as the layout made it.
            if (x2 - x1) < MIN_WIDTH * width or cy < BOTTOM_BAND * height:
                continue
        if (x2 - x1) * (y2 - y1) > MAX_AREA * width * height:
            continue
        # Declared button first; otherwise the lowest candidate, since a screen
        # that stacks a link over a button puts the button underneath.
        rank = (0 if by_id else 1, -cy)
        if best is None or rank < best[0]:
            best = (rank, (cx, cy))
    return best[1] if best else None

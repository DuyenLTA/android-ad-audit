"""Pick a language on the VSL language screen.

The screen is not a flat list of choices. Some rows carry
`checkboxLanguageItem` and are selectable outright; others carry
`iconExpandLanguageItem` and only unfold into regional variants when tapped --
tapping one of those selects nothing and leaves the confirm button disabled.

English is an unfolding row, and the first row that does carry a checkbox is
whatever remote config happens to list first -- हिन्दी (India) on the build this
was written against. So "tap the first checkbox" quietly ran the whole capture
in a language nobody asked for.

So: unfold English, then take the first variant inside it. Matching the variant
by name would be a second thing to keep in step with the build ("English (US)"
vs "English (United States)"); position inside the group needs no such list.

The group can also arrive already unfolded: the flow crosses two language
activities, and the second one inherits the first one's open group. Tapping the
expander there *folds* it, and "first checkbox below the English row" then means
the next language down -- हिन्दी (India) -- selected while the label still
claimed English. So the open state is read off the rows themselves before
touching the expander: a variant sits indented relative to its parent row, which
holds whatever the variants are called.

Rows are matched by vertical overlap rather than tree structure -- a row's title
and its control share a y-range, which survives the flat node list that
`uiautomator dump` produces.
"""
from device_ui import BOUNDS_RE, NODE_RE, _attr, tap

DEFAULT_LANGUAGE = "English"
TITLE_ID = "titleLanguageItem"
CHECKBOX_ID = "checkboxLanguageItem"
EXPAND_ID = "iconExpandLanguageItem"


def _bounds(node: str) -> tuple[int, int, int, int] | None:
    m = BOUNDS_RE.search(node)
    if not m:
        return None
    x1, y1, x2, y2 = (int(g) for g in m.groups())
    # Recycled rows report a zero-area box; its "centre" is the screen corner.
    return (x1, y1, x2, y2) if x2 > x1 and y2 > y1 else None


def _nodes_with_id(xml: str, suffix: str):
    for node in NODE_RE.findall(xml):
        if not _attr(node, "resource-id").endswith(suffix):
            continue
        b = _bounds(node)
        if b:
            yield node, b


def row_box(xml: str, title: str) -> tuple[int, int, int] | None:
    """Left edge and vertical extent of the row titled exactly `title`."""
    for node, (x1, y1, _x2, y2) in _nodes_with_id(xml, TITLE_ID):
        if _attr(node, "text") == title:
            return x1, y1, y2
    return None


def row_span(xml: str, title: str) -> tuple[int, int] | None:
    """Vertical extent of the row titled exactly `title`."""
    box = row_box(xml, title)
    return (box[1], box[2]) if box else None


def variants_unfolded(xml: str, x_left: int, y_bottom: int) -> bool:
    """Whether the row below the one at `y_bottom` is one of its variants.

    Variants are indented under their parent; the next row at the parent's own
    left edge is the next language, not a variant.
    """
    below = [
        (y1, x1)
        for _node, (x1, y1, _x2, _y2) in _nodes_with_id(xml, TITLE_ID)
        if y1 >= y_bottom
    ]
    if not below:
        return False
    _y, x1 = min(below)
    return x1 > x_left


def control_between(xml: str, control_id: str, y_top: int, y_bottom: int | None = None):
    """Centre of the first `control_id` whose own centre sits in the y window."""
    for _node, (x1, y1, x2, y2) in _nodes_with_id(xml, control_id):
        centre_y = (y1 + y2) // 2
        if centre_y < y_top:
            continue
        if y_bottom is not None and centre_y > y_bottom:
            continue
        return (x1 + x2) // 2, centre_y
    return None


def pick(language: str, xml_fn, run, sleep=None) -> str | None:
    """Select `language`, unfolding it first when its variants are hidden.

    One step rather than several: the driver consumes a step whether or not its
    node was on screen, so a "fall back to any language" step queued behind this
    one would also fire on the happy path and move the selection off English.
    """
    xml = xml_fn()
    box = row_box(xml, language)

    if box:
        x_left, y_top, y_bottom = box
        # Some builds make the language selectable without unfolding at all.
        centre = control_between(xml, CHECKBOX_ID, y_top, y_bottom)
        if centre:
            tap(*centre, run=run)
            return language

        already_open = variants_unfolded(xml, x_left, y_bottom)
        expander = control_between(xml, EXPAND_ID, y_top, y_bottom)
        if expander and not already_open:
            tap(*expander, run=run)
            if sleep:
                sleep(1)
            xml = xml_fn()
            box = row_box(xml, language) or box
            y_bottom = box[2]
        if expander or already_open:
            # The variants unfold directly beneath their own row, so the first
            # checkbox below it is the first variant of this language and not
            # some unrelated row further down.
            variant = control_between(xml, CHECKBOX_ID, y_bottom)
            if variant:
                tap(*variant, run=run)
                return f"{language} (biến thể đầu)"
            return f"mở {language}"

    # This build does not offer it at all. Any language reaches Home, which is
    # what the capture needs -- better than stalling on this screen.
    centre = control_between(xml_fn(), CHECKBOX_ID, 0)
    if centre:
        tap(*centre, run=run)
        return f"không có {language} -- chọn ngôn ngữ đầu danh sách"
    return None

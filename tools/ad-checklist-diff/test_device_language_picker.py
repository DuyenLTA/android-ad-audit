from device_language_picker import pick

# Shape taken from a real `uiautomator dump` of the language screen: English is
# an unfolding row, and the first row carrying a checkbox is हिन्दी (India).
COLLAPSED = (
    '<node resource-id="x:id/titleLanguageItem" text="Français" bounds="[202,372][982,467]" />'
    '<node resource-id="x:id/iconExpandLanguageItem" text="" bounds="[982,391][1040,449]" />'
    '<node resource-id="x:id/titleLanguageItem" text="English" bounds="[202,563][982,658]" />'
    '<node resource-id="x:id/iconExpandLanguageItem" text="" bounds="[982,582][1040,640]" />'
    '<node resource-id="x:id/titleLanguageItem" text="हिन्दी (India)" bounds="[202,754][982,849]" />'
    '<node resource-id="x:id/checkboxLanguageItem" text="" bounds="[982,773][1040,831]" />'
)
EXPANDED = (
    '<node resource-id="x:id/titleLanguageItem" text="Français" bounds="[202,372][982,467]" />'
    '<node resource-id="x:id/iconExpandLanguageItem" text="" bounds="[982,391][1040,449]" />'
    '<node resource-id="x:id/titleLanguageItem" text="English" bounds="[202,563][982,658]" />'
    '<node resource-id="x:id/iconExpandLanguageItem" text="" bounds="[982,582][1040,640]" />'
    '<node resource-id="x:id/titleLanguageItem" text="English (US)" bounds="[274,754][982,849]" />'
    '<node resource-id="x:id/checkboxLanguageItem" text="" bounds="[982,773][1040,831]" />'
    '<node resource-id="x:id/titleLanguageItem" text="English (UK)" bounds="[274,945][982,1040]" />'
    '<node resource-id="x:id/checkboxLanguageItem" text="" bounds="[982,964][1040,1022]" />'
)


class _Screen:
    """Serves COLLAPSED until the expander is tapped, EXPANDED after."""

    def __init__(self, first=COLLAPSED, then=EXPANDED, expander_y=611):
        self.first, self.then, self.expander_y = first, then, expander_y
        self.taps = []
        self.expanded = False

    def xml(self):
        return self.then if self.expanded else self.first

    def run(self, args, **kwargs):
        if "input" in args and "tap" in args:
            x, y = int(args[-2]), int(args[-1])
            self.taps.append((x, y))
            if y == self.expander_y:
                self.expanded = True
        return ""


def test_unfolds_english_and_takes_its_first_variant():
    # The whole point: never the first checkbox on screen, which is another
    # language entirely.
    screen = _Screen()
    label = pick("English", screen.xml, screen.run, sleep=lambda s: None)
    assert screen.taps == [(1011, 611), (1011, 802)]  # expander, then English (US)
    assert "English" in label


def test_never_touches_a_checkbox_above_the_language_row():
    screen = _Screen()
    pick("English", screen.xml, screen.run, sleep=lambda s: None)
    english_bottom = 658
    assert all(y > 500 for _x, y in screen.taps)
    assert screen.taps[-1][1] > english_bottom


def test_selects_directly_when_the_row_needs_no_unfolding():
    flat = (
        '<node resource-id="x:id/titleLanguageItem" text="English" bounds="[202,563][982,658]" />'
        '<node resource-id="x:id/checkboxLanguageItem" text="" bounds="[982,582][1040,640]" />'
    )
    screen = _Screen(first=flat, then=flat)
    assert pick("English", screen.xml, screen.run, sleep=lambda s: None) == "English"
    assert screen.taps == [(1011, 611)]


def test_falls_back_to_any_language_when_english_is_not_offered():
    # Reaching Home matters more than the language; stalling here loses the run.
    only_other = (
        '<node resource-id="x:id/titleLanguageItem" text="हिन्दी (India)" bounds="[202,754][982,849]" />'
        '<node resource-id="x:id/checkboxLanguageItem" text="" bounds="[982,773][1040,831]" />'
    )
    screen = _Screen(first=only_other, then=only_other)
    label = pick("English", screen.xml, screen.run, sleep=lambda s: None)
    assert screen.taps == [(1011, 802)]
    assert "không có" in label


def test_recycled_zero_area_rows_are_ignored():
    # A recycler reports off-screen rows as [0,0][0,0]; its "centre" is the corner.
    xml = (
        '<node resource-id="x:id/titleLanguageItem" text="English" bounds="[0,0][0,0]" />'
        '<node resource-id="x:id/checkboxLanguageItem" text="" bounds="[0,0][0,0]" />'
    )
    screen = _Screen(first=xml, then=xml)
    assert pick("English", screen.xml, screen.run, sleep=lambda s: None) is None
    assert screen.taps == []

from device_close_button import find_close_center

ROOT = '<node class="android.widget.FrameLayout" text="" bounds="[0,0][1080,2148]" />'


def test_does_not_tap_the_creative_in_the_middle_of_the_screen():
    # The regression this module exists for: a run tapped (309,814) on a
    # 1080x2148 screen and the ad's WebView turned it into a YouTube intent.
    # Nothing mid-screen is a close control; BACK handles the ad instead.
    xml = ROOT + '<node text="Close" content-desc="" bounds="[200,750][418,878]" />'
    assert find_close_center(xml) is None


def test_close_control_matched_in_the_ad_creatives_own_language():
    # A real interstitial rendered its close control as Portuguese "Fechar"
    # inside an app set to another language entirely.
    xml = ROOT + '<node text="Fechar" content-desc="" bounds="[144,1968][300,2067]" />'
    assert find_close_center(xml) == (222, 2017)


def test_close_control_matched_by_content_desc():
    xml = ROOT + '<node text="" content-desc="Close Billing Screen" bounds="[940,120][1040,220]" />'
    assert find_close_center(xml) == (990, 170)


def test_a_creative_sized_node_is_never_the_close_control():
    # An ad frame whose description happens to carry the word would otherwise
    # be the biggest possible mis-tap.
    xml = ROOT + '<node text="" content-desc="Close" bounds="[0,200][1080,1900]" />'
    assert find_close_center(xml) is None


def test_prefers_the_corner_control_over_one_the_creative_drew():
    # "Skip" painted inside the creative sits lower and further in than the ad
    # frame's own button; the corner one is the real control.
    xml = (
        ROOT
        + '<node text="Skip ad" content-desc="" bounds="[120,1700][320,1790]" />'
        + '<node text="Close" content-desc="" bounds="[980,60][1060,140]" />'
    )
    assert find_close_center(xml) == (1020, 100)


def test_no_close_control_returns_none():
    assert find_close_center(ROOT + '<node text="More" content-desc="" bounds="[0,0][10,10]" />') is None


def test_long_body_copy_mentioning_close_is_ignored():
    xml = ROOT + '<node text="Tap here to close this offer now" content-desc="" bounds="[40,80][900,180]" />'
    assert find_close_center(xml) is None


def test_glyph_only_close_button_is_found():
    # Most interstitials label their dismiss control with nothing but a glyph.
    xml = ROOT + '<node text="✕" content-desc="" bounds="[980,60][1060,140]" />'
    assert find_close_center(xml) == (1020, 100)


def test_the_letter_x_inside_a_word_is_not_a_close_button():
    # Matching glyphs as substrings would make "Next", "Explore" and every
    # other word carrying an x into a dismiss control.
    xml = ROOT + '<node text="Next" content-desc="" bounds="[980,60][1060,140]" />'
    assert find_close_center(xml) is None


def test_frames_own_close_id_wins_over_a_label_the_creative_drew():
    # A creative can paint its own "Close" anywhere; the frame's button is the
    # one that actually dismisses the ad.
    xml = (
        ROOT
        + '<node resource-id="com.x:id/interstitial_close_button" text="" content-desc="" bounds="[960,40][1060,140]" />'
        + '<node text="Close" content-desc="" bounds="[40,1990][240,2090]" />'
    )
    assert find_close_center(xml) == (1010, 90)


def test_close_id_still_has_to_sit_where_a_button_could():
    # An id match is trusted, not blindly obeyed -- a full-screen node carrying
    # that id is still the creative.
    xml = ROOT + '<node resource-id="com.x:id/btnClose" text="" bounds="[0,200][1080,1900]" />'
    assert find_close_center(xml) is None

"""The continue button has to be found without knowing its label -- and the ad
sitting under it must never be mistaken for it."""
from device_continue_button import find_continue_center

# 720x1600, the shape the question screen actually has on device: a 2x2 grid of
# unlabelled answer cards, the continue button under them, and a native ad
# filling everything below that.
SCREEN = '<node bounds="[0,0][720,1600]" />'
CARDS = (
    '<node resource-id="" text="" clickable="true" bounds="[27,123][345,478]" />'
    '<node resource-id="" text="" clickable="true" bounds="[375,123][693,478]" />'
    '<node resource-id="" text="" clickable="true" bounds="[27,508][345,863]" />'
    '<node resource-id="" text="" clickable="true" bounds="[375,508][693,863]" />'
)
# Taken from a real dump: the creative's install button is wider and lower than
# the app's own button, and is a labelled Button too.
NATIVE_AD = (
    '<node resource-id="com.x:id/ad_headline" text="Test Ad : Google Ads" clickable="true" bounds="[82,1002][697,1036]" />'
    '<node resource-id="com.x:id/ad_media" text="" clickable="true" bounds="[23,1075][697,1478]" />'
    '<node resource-id="com.x:id/ad_call_to_action" text="INSTALL" clickable="true" bounds="[23,1487][697,1577]" />'
)
BUTTON = '<node resource-id="com.x:id/btnNextQuestion" text="Get Started" clickable="true" bounds="[505,942][693,978]" />'
LIVE = SCREEN + CARDS + BUTTON + NATIVE_AD


def test_picks_the_button_not_the_ad_on_a_real_screen():
    # The whole hazard in one assertion: INSTALL is lower, wider and also a
    # labelled button. Tapping it leaves the app and bills a click on the very
    # ad unit under audit.
    assert find_continue_center(LIVE) == (599, 960)


def test_label_is_never_what_identifies_it():
    for label in ("Get Started", "Get started", "Go to Home", "Next", "Bắt đầu"):
        xml = SCREEN + CARDS + BUTTON.replace("Get Started", label) + NATIVE_AD
        assert find_continue_center(xml) == (599, 960), label


def test_unnamed_button_is_found_by_shape():
    # Builds that ship no id for it still have to advance.
    unnamed = '<node resource-id="" text="Get Started" clickable="true" bounds="[60,1200][660,1300]" />'
    assert find_continue_center(SCREEN + CARDS + unnamed) == (360, 1250)


def test_ad_alone_is_not_a_continue_button():
    # No app button on screen -> report nothing rather than tap the creative.
    assert find_continue_center(SCREEN + CARDS + NATIVE_AD) is None


def test_answer_cards_are_not_the_button():
    # Tapping a card picks an answer and the screen still does not advance.
    assert find_continue_center(SCREEN + CARDS) is None


def test_ignores_a_full_screen_clickable_container():
    xml = SCREEN + '<node text="root" clickable="true" bounds="[0,0][720,1600]" />'
    assert find_continue_center(xml) is None


def test_ignores_unclickable_text_and_disabled_buttons():
    prompt = '<node text="Choose one to continue" bounds="[60,900][660,940]" />'
    disabled = '<node resource-id="com.x:id/btnNextQuestion" text="Get Started" clickable="true" enabled="false" bounds="[505,942][693,978]" />'
    assert find_continue_center(SCREEN + CARDS + prompt + disabled) is None


def test_an_id_called_btnadd_is_not_read_as_an_ad_view():
    add = '<node resource-id="com.x:id/btnAdd" text="Add" clickable="true" bounds="[60,1200][660,1300]" />'
    assert find_continue_center(SCREEN + add) == (360, 1250)


def test_no_nodes_at_all():
    assert find_continue_center("") is None

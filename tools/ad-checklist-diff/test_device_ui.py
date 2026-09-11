from device_ui import find_close_center, find_node_center, focused_activity, screen_size

LANGUAGE_XML = """<hierarchy>
<node resource-id="com.x:id/buttonLanguageNext" text="" enabled="false" bounds="[922,139][1066,283]" />
<node resource-id="com.x:id/titleLanguageItem" text="English" bounds="[202,563][982,658]" />
<node resource-id="com.x:id/checkboxLanguageItem" text="" bounds="[982,773][1040,831]" />
<node resource-id="com.x:id/rootLanguageItem" text="" bounds="[0,0][0,0]" />
</hierarchy>"""


def test_find_node_by_resource_id_suffix_ignores_package_prefix():
    assert find_node_center(LANGUAGE_XML, resource_id="id/checkboxLanguageItem") == (1011, 802)


def test_find_node_matches_on_text_too():
    assert find_node_center(LANGUAGE_XML, resource_id="id/titleLanguageItem", text="English") == (592, 610)


def test_recycled_zero_area_nodes_are_skipped():
    # A recycler reports off-screen rows as [0,0][0,0]; tapping that "centre"
    # would hit the screen corner instead of the row.
    assert find_node_center(LANGUAGE_XML, resource_id="id/rootLanguageItem") is None


def test_missing_node_returns_none():
    assert find_node_center(LANGUAGE_XML, resource_id="id/nope") is None


AD_XML = """<hierarchy>
<node class="android.widget.TextView" text="Fechar" content-desc="" bounds="[144,1968][300,2067]" />
<node class="android.view.View" text="" content-desc="More" bounds="[567,1953][1023,2082]" />
</hierarchy>"""


def test_close_control_matched_in_the_ad_creatives_own_language():
    # A real interstitial rendered its close control as Portuguese "Fechar"
    # inside an app set to another language entirely.
    assert find_close_center(AD_XML) == (222, 2017)


def test_close_control_matched_by_content_desc():
    xml = '<node text="" content-desc="Close Billing Screen" bounds="[40,100][140,200]" />'
    assert find_close_center(xml) == (90, 150)


def test_no_close_control_returns_none():
    assert find_close_center('<node text="More" content-desc="" bounds="[0,0][10,10]" />') is None


def test_focused_activity_parsed_from_dumpsys():
    out = "  mCurrentFocus=Window{29d4be5 u0 com.x/com.x.ui.MainActivity}\n"
    assert focused_activity(run=lambda *a, **k: out) == "com.x/com.x.ui.MainActivity"


def test_focused_activity_none_when_nothing_focused():
    assert focused_activity(run=lambda *a, **k: "mCurrentFocus=null\n") is None


def test_screen_size_parsed():
    assert screen_size(run=lambda *a, **k: "Physical size: 1080x2280\n") == (1080, 2280)

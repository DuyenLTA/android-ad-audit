"""Checkers on hand-built runs, one test per trap met on a real device (04/11/2026)."""
import json
from pathlib import Path

from checkers_fullscreen_resume import inter_changes_screen, inter_click_handled, resume_not_after_utility
from checkers_native_banner import _app_webviews, _mid_swipe, native_content_overlap, no_ad_on_webview
from checkers_reward_app_sub import sub_billing_popup_dates, sub_privacy_tos_in_app
from policy_evidence import Frame, Run

PKG = "com.example.app"
AD = f"{PKG}/com.google.android.libraries.ads.mobile.sdk.common.AdActivity"


def node(rid="", text="", desc="", cls="android.widget.FrameLayout", bounds=(0, 0, 10, 10), clickable=False, pkg=PKG):
    return {"rid": rid, "text": text, "desc": desc, "cls": cls, "pkg": pkg, "clickable": clickable, "bounds": bounds}


def run(tmp_path: Path, activities=(), probes=(), frames=(), files=None) -> Run:
    for name, data in (files or {}).items():
        (tmp_path / name).write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
    r = Run(root=tmp_path, meta={"package": PKG, "screen_px": [1080, 2400], "density_dpi": 480},
            activities=list(activities), probes=list(probes))
    r.frames = list(frames)
    return r


def frame(t, activity, nodes):
    return Frame(t=t, xml=Path(f"{t}.xml"), png=None, activity=activity, nodes=nodes)


NATIVE = [node("nativeAdView", bounds=(0, 1400, 1080, 2400)), node("ad_media", bounds=(30, 1600, 1050, 2100)),
          node("ad_call_to_action", bounds=(30, 2200, 1050, 2350)), node(text="Ad", bounds=(30, 1420, 105, 1477)),
          node(desc="Ad Choices Icon", bounds=(1035, 1400, 1080, 1445))]


def test_trip_to_chrome_after_ad_tap_stays_inside_the_ad_episode(tmp_path):
    r = run(tmp_path, activities=[{"t": 0, "activity": f"{PKG}/.Question"}, {"t": 1000, "activity": AD},
                                  {"t": 5000, "activity": "com.android.chrome/.Tab"}, {"t": 6000, "activity": AD},
                                  {"t": 9000, "activity": f"{PKG}/.Billing"}])
    eps = r.episodes()
    assert len(eps) == 1 and eps[0].after == f"{PKG}/.Billing"
    assert inter_changes_screen(r, {})["status"] == "PASS"


def test_inter_click_without_any_tap_is_blocked_not_passed(tmp_path):
    assert inter_click_handled(run(tmp_path), {})["status"] == "BLOCKED"


def test_mid_swipe_native_is_not_measured():
    assert _mid_swipe((0, 0, 674, 2400), 1080)          # seen on Onboarding while the pager moved
    assert not _mid_swipe((0, 1400, 1080, 2400), 1080)   # full-width native at rest


def test_id_less_container_around_the_native_is_not_content_over_it(tmp_path):
    nodes = NATIVE[1:] + [node(bounds=(0, 1380, 1080, 2360), clickable=True)]   # container without id
    r = run(tmp_path, frames=[frame(1, f"{PKG}/.Question", nodes)])
    assert native_content_overlap(r, {})["status"] == "PASS"
    # An app button straddling the ad's edge. (One drawn entirely inside the ad box cannot be told apart
    # from the ad's own views in a flat dump; that case is left to the screenshot.)
    nodes.append(node("btnNext", bounds=(800, 2300, 1080, 2400), clickable=True))
    assert native_content_overlap(r, {})["status"] == "FAIL"


def test_webview_inside_native_or_interstitial_is_not_an_app_page(tmp_path):
    media_web = node(cls="android.webkit.WebView", bounds=(30, 1600, 1050, 2100))
    assert _app_webviews(frame(1, f"{PKG}/.Onboarding", NATIVE + [media_web]), PKG) == []
    full_web = node(cls="android.webkit.WebView", bounds=(0, 0, 1080, 2400))
    assert _app_webviews(frame(2, AD, [full_web]), PKG) == []
    r = run(tmp_path, frames=[frame(1, f"{PKG}/.Onboarding", NATIVE + [media_web])])
    assert no_ad_on_webview(r, {})["status"] == "NA"


def test_ad_after_returning_from_a_utility_screen_fails(tmp_path):
    ok = {"label": "Privacy Policy", "way": "sang web rồi BACK", "ad_after": None}
    bad = {"label": "Rate us", "way": "sang Play rồi BACK", "ad_after": AD}
    r = run(tmp_path, files={"utility-visits.jsonl": json.dumps(ok) + "\n" + json.dumps(bad) + "\n"})
    assert resume_not_after_utility(r, {})["status"] == "FAIL"


PAYWALL = [node(text="Weekly"), node(text="₫130,000"), node(text="/week"), node(text="Privacy policy", clickable=True),
           node(text="Terms of service", clickable=True)]


def test_privacy_link_may_open_outside_the_app_but_must_open(tmp_path):
    pw = [frame(1, f"{PKG}/com.visionlab.billing.ui.VslBillingActivity", PAYWALL)]
    tap = {"t": 2, "kind": "paywall_privacy", "after": "com.android.chrome/.Tab", "left_app": True,
           "handled": True, "activity": "x"}
    assert sub_privacy_tos_in_app(run(tmp_path, frames=pw, probes=[tap]), {})["status"] == "PASS"
    dead = dict(tap, handled=False, after="x", left_app=False)
    assert sub_privacy_tos_in_app(run(tmp_path, frames=pw, probes=[dead]), {})["status"] == "FAIL"


def test_activity_spellings_compare_equal():
    from ui_nodes import norm_activity
    assert norm_activity("com.x.app/.ui.Main") == norm_activity("com.x.app/com.x.app.ui.Main")
    assert norm_activity("com.x.app/com.other.Main") == "com.x.app/com.other.Main"


def test_inferred_native_is_the_real_container_not_built_from_adchoices():
    from ui_nodes import native_parts
    kids = [node("ad_media", bounds=(30, 1600, 1050, 2100)), node("ad_call_to_action", bounds=(30, 2200, 1050, 2350)),
            node(text="Ad", bounds=(30, 1520, 105, 1577))]
    holder = node(bounds=(0, 1464, 1080, 2400), clickable=True)          # id-less container, as on Question
    screen = node(bounds=(0, 0, 1080, 2400))
    stray = node(desc="Ad Choices Icon", bounds=(1035, 200, 1080, 245))   # far above the ad
    parts = native_parts([screen, holder, *kids, stray])
    assert parts["native"]["inferred"] and parts["native"]["bounds"] == (0, 1464, 1080, 2400)


def test_tap_that_only_changed_app_screen_is_unclear(tmp_path):
    from checkers_native_banner import native_cta_click_handled
    probe = {"t": 1, "kind": "native_cta", "activity": f"{PKG}/.A", "after": f"{PKG}/.B",
             "handled": "unclear", "left_app": False}
    assert native_cta_click_handled(run(tmp_path, probes=[probe]), {})["status"] == "CAN_XEM"


def test_plan_named_trial_on_play_sheet_fails(tmp_path):
    buy = {"billing_sheet_texts": ["Weekly Free Trial", "Starting today"], "billing_sheet_t": 10, "paywall_texts": []}
    assert sub_billing_popup_dates(run(tmp_path, files={"purchase.json": buy}), {})["status"] == "FAIL"
    buy["billing_sheet_texts"] = ["Weekly", "Starting today", "₫130,000/5 min"]
    assert sub_billing_popup_dates(run(tmp_path, files={"purchase.json": buy}), {})["status"] == "PASS"


def test_ai_result_screen_with_report_button_passes(tmp_path):
    from checkers_reward_app_sub import ai_result_has_report_button
    from ui_nodes import parse_nodes
    xml = (Path(__file__).resolve().parent / "fixtures" / "ai-result-hair-generate.xml").read_text(encoding="utf-8")
    nodes = [dict(n, pkg=PKG) for n in parse_nodes(xml)]
    r = run(tmp_path, frames=[frame(1, f"{PKG}/.ui.generate.GenerateActivity", nodes)])
    assert ai_result_has_report_button(r, {})["status"] == "PASS"
    no_report = [n for n in nodes if n["desc"] != "Report"]
    r = run(tmp_path, frames=[frame(1, f"{PKG}/.ui.generate.GenerateActivity", no_report)])
    assert ai_result_has_report_button(r, {})["status"] == "FAIL"


def test_no_trial_is_not_applicable_but_missing_sale_fails(tmp_path):
    from checkers_reward_app_sub import (sub_sale_shows_both_prices, sub_trial_not_separate_button,
                                         sub_trial_then_price)
    r = run(tmp_path, frames=[frame(1, f"{PKG}/com.visionlab.billing.ui.VslBillingActivity", PAYWALL)])
    for checker in (sub_trial_then_price, sub_trial_not_separate_button):
        assert checker(r, {})["status"] == "NA"      # free trial is optional per app
    assert sub_sale_shows_both_prices(r, {})["status"] == "FAIL"
    assert sub_trial_then_price(run(tmp_path), {})["status"] == "BLOCKED"   # no paywall reached


def test_picker_tiles_are_photos_not_tabs_or_cancel():
    from evidence_home_explorer import photo_tiles
    from ui_nodes import parse_nodes
    xml = (Path(__file__).resolve().parent / "fixtures" / "system-photo-picker-pixel4.xml").read_text(encoding="utf-8")
    tiles = photo_tiles(parse_nodes(xml))
    assert tiles and all(t["desc"].startswith("Photo taken") for t in tiles)


def _fixture_nodes(name):
    from ui_nodes import parse_nodes
    return parse_nodes((Path(__file__).resolve().parent / "fixtures" / name).read_text(encoding="utf-8"))


def test_rate_dialog_closes_by_icon_id():
    # AIP872 05/11/2026: the rate dialog's close icon has no text, only id btnDismiss; the run stuck on it.
    from evidence_home_explorer import popup_closes
    closes = popup_closes(_fixture_nodes("rate-dialog-icon-close-aip872.xml"),
                          "com.aiphotogenearator.aivideogenerator.photogallery")
    assert [c["rid"] for c in closes] == ["btnDismiss"]


def test_upload_box_opens_picker_without_choose_n_label():
    # AIP872 Image to Image: "Tap to Upload" box, no sample row, no "Choose N photo".
    from evidence_home_explorer import HomeExplorer
    nodes = _fixture_nodes("image-to-image-upload-aip872.xml")
    box = HomeExplorer.gallery_box(HomeExplorer.__new__(HomeExplorer), nodes, None)
    assert box and box["clickable"]


def test_off_sub_turns_blocked_sub_rules_into_na():
    from policy_check_runner import mark_off_sub
    res = [{"checker": "sub_plan_info_complete", "status": "BLOCKED", "reason": "lượt này không tới được paywall"},
           {"checker": "sub_sale_shows_both_prices", "status": "FAIL", "reason": "x"},
           {"checker": "inter_click_handled", "status": "BLOCKED", "reason": "y"}]
    mark_off_sub(res, "plan tuần ghi Off subs")
    assert [r["status"] for r in res] == ["NA", "FAIL", "BLOCKED"]


def test_inter_judged_on_cta_tap_after_pausing_tap(tmp_path):
    # AIP872 05/11/2026: the first tap paused the video and showed "More"; the follow-up tap opens the landing.
    probes = [{"t": 100, "kind": "fullscreen", "activity": AD, "tap": [540, 1320], "after": AD, "handled": False,
               "left_app": False},
              {"t": 4200, "kind": "fullscreen", "activity": AD, "tap": [900, 2200],
               "after": "com.android.chrome/x.Chrome", "handled": True, "left_app": True, "follow_up_of": 100}]
    assert inter_click_handled(run(tmp_path, probes=probes), {})["status"] == "PASS"
    probes[1]["handled"], probes[1]["after"] = False, AD
    assert inter_click_handled(run(tmp_path, probes=probes), {})["status"] == "FAIL"


def test_report_gate_lists_open_items():
    from policy_check_runner import unresolved
    out = {"results": [{"checker": "a", "status": "PASS"}, {"checker": "b", "status": "CAN_XEM"},
                       {"checker": "c", "status": "BLOCKED"}, {"checker": "d", "status": "NA"}]}
    assert unresolved(out) == ["b", "c"]


def test_screen_under_ad_flashing_back_before_the_next_one_is_not_same_screen(tmp_path):
    q, bill = f"{PKG}/.Question", f"{PKG}/.Billing"
    flash = [{"t": 0, "activity": q}, {"t": 1000, "activity": AD}, {"t": 30000, "activity": q}, {"t": 30600, "activity": bill}]
    assert inter_changes_screen(run(tmp_path, activities=flash), {})["status"] == "PASS"
    stays = [{"t": 0, "activity": q}, {"t": 1000, "activity": AD}, {"t": 30000, "activity": q}, {"t": 45000, "activity": bill}]
    assert inter_changes_screen(run(tmp_path, activities=stays), {})["status"] == "FAIL"


def test_app_name_on_billing_sheet_with_or_without_tagline():
    from evidence_sub_purchase import _app_name_on_sheet
    assert _app_name_on_sheet(["Weekly 6.99", "Lingix: AI Tutor Vocab Builder", "Starting today"]) == "Lingix: AI Tutor Vocab Builder"
    assert _app_name_on_sheet(["Weekly", "Starting today", "Emberly - AI Photo"]) == "Emberly - AI Photo"
    assert _app_name_on_sheet([]) == ""


def test_ai_chat_report_sits_under_the_answer(tmp_path):
    from checkers_reward_app_sub import ai_result_has_report_button
    chat = [node(text="Hi there! What are we diving into today?"), node(text="Report answer", clickable=True),
            node(desc="Send", clickable=True)]
    r = run(tmp_path, frames=[frame(1, f"{PKG}/.MainActivity", chat)])
    assert ai_result_has_report_button(r, {})["status"] == "PASS"
    r = run(tmp_path, frames=[frame(1, f"{PKG}/.MainActivity", [chat[0], chat[2]])])
    assert ai_result_has_report_button(r, {})["status"] == "FAIL"


def test_fullscreen_cta_in_any_language_skips_close_and_ad_badge():
    from evidence_click_probe import fullscreen_cta
    node = lambda text, y, cls="android.widget.Button", click=True: {
        "rid": "", "text": text, "desc": "", "cls": cls, "pkg": "x", "clickable": click, "bounds": (0, y, 100, y + 50)}
    paused = [node("Ad", 10, "android.widget.TextView", False), node("了解详情", 800), node("Close", 1700),
              node("了解详情", 1700)]
    assert fullscreen_cta(paused)["bounds"][1] == 1700 and fullscreen_cta(paused)["text"] == "了解详情"
    assert fullscreen_cta([node("Close", 1700), node("Skip", 1800)]) is None
    assert fullscreen_cta([node("Xem Thêm", 900)])["text"] == "Xem Thêm"


def _q_node(text="", desc="", cls="android.view.View", click=False, b=(0, 0, 10, 10)):
    return {"rid": "", "text": text, "desc": desc, "cls": cls, "pkg": "x", "clickable": click, "bounds": b}


def test_questionnaire_types_a_name_then_presses_continue():
    from evidence_in_app_questionnaire import next_action
    go_box = _q_node(click=True, b=(84, 2100, 996, 2268))
    nodes = [_q_node("What should we call you?", b=(84, 440, 900, 660)),
             _q_node("Enter your name", cls="android.widget.EditText", click=True, b=(84, 884, 996, 1050)),
             go_box, _q_node("Continue →", b=(380, 2150, 700, 2210))]
    kind, button, fill = next_action(nodes)
    assert kind == "go" and button is go_box and fill[0]["cls"].endswith("EditText")


def test_questionnaire_picks_first_answer_card_above_the_button():
    from evidence_in_app_questionnaire import next_action
    card1, card2 = _q_node(click=True, b=(60, 600, 1020, 760)), _q_node(click=True, b=(60, 780, 1020, 940))
    nodes = [_q_node("How old are you?", b=(60, 400, 900, 500)), card1, _q_node("13–17", b=(100, 650, 300, 700)),
             card2, _q_node("Start", click=True, b=(60, 2100, 1020, 2260))]
    kind, button, fill = next_action(nodes)
    assert kind == "go" and button["text"] == "Start" and fill == [card1]


def test_questionnaire_never_presses_continue_on_a_paywall():
    from evidence_in_app_questionnaire import next_action
    nodes = [_q_node("Weekly", b=(60, 1400, 400, 1450)), _q_node("₫182,000 /week", b=(700, 1400, 1000, 1450)),
             _q_node("Continue", click=True, b=(60, 2000, 1020, 2100))]
    assert next_action(nodes)[0] == "stop"


def test_questionnaire_stops_on_real_home():
    from evidence_in_app_questionnaire import next_action
    nodes = [_q_node("AI Tutor", b=(60, 150, 600, 260)), _q_node("Vocabulary", click=True, b=(388, 1969, 692, 2151))]
    assert next_action(nodes)[0] == "stop"


def test_questionnaire_uses_disabled_continue_label_when_name_is_empty():
    from evidence_in_app_questionnaire import next_action
    nodes = [_q_node("What should we call you?", b=(84, 430, 996, 674)),
             _q_node("", cls="android.widget.EditText", click=True, b=(84, 882, 996, 1051)),
             _q_node("Enter your name", b=(144, 936, 541, 997)), _q_node("Continue", b=(391, 2156, 606, 2214))]
    kind, button, fill = next_action(nodes)
    assert kind == "go" and button["text"] == "Continue" and fill[0]["cls"].endswith("EditText")


def test_chat_cards_skip_tab_bar_and_native_ad_cards():
    from evidence_chat_reward import chat_cards, watch_ad_gate
    tutor = _q_node(click=True, b=(60, 463, 1020, 907))
    ad_card = _q_node(click=True, b=(60, 949, 1020, 1393))
    tab_bar = _q_node(click=True, b=(60, 1921, 1020, 2229))
    nodes = [tutor, _q_node("Olivia", b=(468, 609, 638, 685)), ad_card, _q_node("Ad", b=(80, 960, 130, 1000)), tab_bar]
    assert chat_cards(nodes, 1080, 2400) == [tutor]
    gate = [_q_node("Watch Ad (0/3)", b=(374, 1505, 706, 1560)), _q_node("Maybe later", click=True)]
    assert watch_ad_gate(gate)["text"] == "Watch Ad (0/3)"

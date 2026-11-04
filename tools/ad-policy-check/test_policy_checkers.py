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

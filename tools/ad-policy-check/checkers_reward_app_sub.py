"""Checkers for reward ads, app-level rules (external links, AI report button) and the paywall.

Paywall rules read the texts of the paywall screen's UI dump; wording that needs
judgement (benefits, "then <price>") goes to Claude with the screenshot.
"""
import re

from checkers_fullscreen_resume import BLOCKED, CAN_XEM, FAIL, NA, PASS, _click
from policy_evidence import Run

PAYWALL_MARKERS = ("Billing", "Paywall", "Premium", "Subscription", "Iap", "Purchase")
PRICE_RE = re.compile(r"(₫|\$|€|£|¥|₹|VND|USD|đ)\s?[\d.,]+|[\d.,]+\s?(₫|đ|VND|USD)")
PERIOD_RE = re.compile(r"week|month|year|tuần|tháng|năm|lifetime|trọn đời", re.I)
TRIAL_RE = re.compile(r"trial|dùng thử|free for", re.I)
REWARD_RE = re.compile(r"watch (an )?ad|xem (quảng cáo|qc)|free with ad|unlock with ad", re.I)
CANCEL_RE = re.compile(r"cancel any ?time|hủy bất kỳ lúc nào|huỷ bất kỳ lúc nào|cancel at any time", re.I)


def _paywall_frames(run: Run) -> list:
    out, seen = [], set()
    for f in run.frames:
        if any(m in f.activity for m in PAYWALL_MARKERS) and f.texts():
            key = tuple(f.texts()[:6])
            if key not in seen:
                seen.add(key)
                out.append(f)
    return out


def _no_paywall():
    # Not reaching the paywall says nothing about it: the run is incomplete, not the app compliant.
    return {"status": BLOCKED, "reason": "lượt này không tới được paywall", "evidence": []}


# The checklist is the standard (user, 04/11/2026): a paywall without a sale showing both prices
# violates the sale rule. A free trial is optional per app (user, same day): no trial -> the trial
# rules do not apply (N/A).
NO_TRIAL = "app không có gói free trial — rule trial không áp dụng"
NO_SALE = "paywall không có gói sale hiện giá trước và sau khi giảm — checklist yêu cầu"


def _texts(frames) -> list[str]:
    return [t for f in frames for t in f.texts()]


def sub_plan_info_complete(run: Run, params: dict) -> dict:
    pw = _paywall_frames(run)
    if not pw:
        return _no_paywall()
    texts = _texts(pw)
    prices = [t for t in texts if PRICE_RE.search(t)]
    periods = [t for t in texts if PERIOD_RE.search(t)]
    ev = [run.rel(f.png) for f in pw if f.png]
    missing = [name for name, got in (("giá", prices), ("thời hạn", periods)) if not got]
    if missing:
        return {"status": FAIL, "reason": f"paywall thiếu {', '.join(missing)}", "evidence": ev}
    return {"status": CAN_XEM, "reason": f"có giá ({', '.join(prices[:3])}) và thời hạn; quyền lợi/trial cần nhìn",
            "evidence": ev, "visual": {"images": ev, "question": "Paywall có hiện rõ quyền lợi khi mua không? Nếu có trial thì có ghi số ngày cụ thể không?"}}


def _trial(run: Run, question: str, need: str) -> dict:
    pw = _paywall_frames(run)
    if not pw:
        return _no_paywall()
    if not any(TRIAL_RE.search(t) for t in _texts(pw)):
        return {"status": NA, "reason": NO_TRIAL, "evidence": [run.rel(f.png) for f in pw if f.png][:2]}
    ev = [run.rel(f.png) for f in pw if f.png]
    return {"status": CAN_XEM, "reason": "có trial, cần nhìn", "evidence": ev, "visual": {"images": ev, "question": question}}


def sub_trial_then_price(run, params):
    return _trial(run, "Câu trial có dạng 'start with X days trial then <giá>' (hoặc tương đương) không?",
                  "câu 'start with X days trial then <giá>'")


def sub_trial_text_smaller(run, params):
    return _trial(run, "Chữ trial trong nút có nhỏ hơn giá và thời hạn gói không?",
                  "chữ trial nằm trong nút có giá + thời hạn, cỡ nhỏ hơn")


def sub_trial_not_separate_button(run: Run, params: dict) -> dict:
    pw = _paywall_frames(run)
    if not pw:
        return _no_paywall()
    lone = [n for f in pw for n in f.nodes if n["clickable"] and TRIAL_RE.search(n["text"] or n["desc"])
            and not PRICE_RE.search(n["text"] or n["desc"])]
    if not any(TRIAL_RE.search(t) for t in _texts(pw)):
        return {"status": NA, "reason": NO_TRIAL, "evidence": [run.rel(f.png) for f in pw if f.png][:2]}
    return {"status": FAIL if lone else PASS,
            "reason": f"nút trial riêng: '{lone[0]['text']}'" if lone else "chữ trial không nằm trong nút riêng",
            "evidence": [run.rel(f.png) for f in pw if f.png][:2]}


def sub_sale_shows_both_prices(run: Run, params: dict) -> dict:
    pw = _paywall_frames(run)
    if not pw:
        return _no_paywall()
    sale = [t for t in _texts(pw) if re.search(r"sale|off|giảm|-\d+%|\d+% ?off", t, re.I)]
    if not sale:
        return {"status": FAIL, "reason": NO_SALE, "evidence": [run.rel(f.png) for f in pw if f.png][:2]}
    ev = [run.rel(f.png) for f in pw if f.png]
    return {"status": CAN_XEM, "reason": f"có sale: {sale[0]}", "evidence": ev,
            "visual": {"images": ev, "question": "Gói sale có hiện cả giá trước và sau khi giảm không?"}}


def sub_cancel_anytime_text(run: Run, params: dict) -> dict:
    pw = _paywall_frames(run)
    if not pw:
        return _no_paywall()
    hit = [t for t in _texts(pw) if CANCEL_RE.search(t)]
    return {"status": PASS if hit else FAIL, "reason": f"có: '{hit[0][:60]}'" if hit else "không thấy 'Cancel anytime'",
            "evidence": [run.rel(f.png) for f in pw if f.png][:2]}


def sub_privacy_tos_in_app(run: Run, params: dict) -> dict:
    """Both links on the paywall, and they open. Opening outside the app (browser) is fine (user, 04/11/2026)."""
    pw = _paywall_frames(run)
    if not pw:
        return _no_paywall()
    texts = " | ".join(_texts(pw)).lower()
    has_p = "privacy" in texts or "quyền riêng tư" in texts or "chính sách" in texts
    has_t = "term" in texts or "điều khoản" in texts
    ev = [run.rel(f.png) for f in pw if f.png][:2]
    if not (has_p and has_t):
        return {"status": FAIL, "reason": f"paywall thiếu link {'Privacy' if not has_p else 'Terms'}", "evidence": ev}
    tap = next((p for p in run.probes if p["kind"] == "paywall_privacy"), None)
    if not tap:
        return {"status": BLOCKED, "reason": "có link Privacy và Terms; chưa bấm thử được", "evidence": ev}
    if not tap["handled"]:
        return {"status": FAIL, "reason": "có link Privacy và Terms, nhưng bấm Privacy không mở ra gì",
                "evidence": ev + ["click-probes.jsonl"]}
    where = "ngoài app (" + tap["after"].split("/")[0] + ")" if tap["left_app"] else "trong app"
    return {"status": PASS, "reason": f"có link Privacy và Terms; bấm Privacy mở trang {where}", "evidence": ev}


def sub_billing_popup_dates(run: Run, params: dict) -> dict:
    buy = run.json("purchase.json")
    sheet = buy.get("billing_sheet_texts")
    if not sheet:
        return {"status": BLOCKED, "reason": "chưa mở được sheet thanh toán của Play ("
                                             + buy.get("result", "chưa chạy lượt mua") + ")", "evidence": []}
    f = run.frame_near(buy["billing_sheet_t"] - 3000)
    ev = [run.rel(f.png)] if f and f.png else []
    plan = sheet[0]
    has_trial = any(TRIAL_RE.search(t) for t in buy.get("paywall_texts", []) + sheet)
    when = [t for t in sheet if re.search(r"today|starting|từ hôm nay|bắt đầu|\d{1,2}/\d{1,2}", t, re.I)]
    if TRIAL_RE.search(plan):
        return {"status": FAIL, "reason": f"tên gói trên Play chứa chữ trial: '{plan}'", "evidence": ev}
    if has_trial:
        return {"status": CAN_XEM, "reason": "gói có trial; sheet Play: " + " · ".join(sheet[:6]), "evidence": ev,
                "visual": {"images": ev, "question": "Sheet thanh toán có ghi ngày bắt đầu dùng thử và ngày bắt đầu tính "
                                                     "tiền (ngày tính tiền không được là hôm nay) không?"}}
    return {"status": PASS, "reason": f"gói '{plan}' không có trial, tên không chứa 'trial'; sheet ghi: "
                                      + " · ".join(when[:2] or sheet[1:4]), "evidence": ev}


def sub_cancel_option_after_purchase(run: Run, params: dict) -> dict:
    buy = run.json("purchase.json")
    if not buy.get("purchased"):
        return {"status": BLOCKED, "reason": "chưa mua được sub (" + buy.get("result", "chưa chạy lượt mua") + ")",
                "evidence": []}
    opt, opens = buy.get("cancel_option"), buy.get("cancel_option_opens", "")
    if not opt:
        return {"status": FAIL, "reason": "đã mua sub nhưng không thấy lựa chọn huỷ sub trong app (trang chủ và Cài đặt)",
                "evidence": ["purchase.json"]}
    ok = opens.startswith("com.android.vending")
    note = "" if buy.get("cancelled") else "; sub test chưa huỷ được: " + "; ".join(buy.get("steps", [])[-1:])
    return {"status": PASS if ok else FAIL,
            "reason": f"có '{opt}' trong app, bấm mở " + ("Google Play > Subscriptions" if ok else opens) + note,
            "evidence": ["purchase.json"]}


def sub_ios_restore(run, params):
    return {"status": NA, "reason": "rule chỉ cho iOS", "evidence": []}


def reward_has_watch_ad_label(run: Run, params: dict) -> dict:
    marks = [f for f in run.frames if any(REWARD_RE.search(t) for t in f.texts())]
    if not marks:
        return {"status": NA, "reason": "các màn đã đi không có vị trí reward ad (không thấy 'Watch ad' / "
                                        "'Xem quảng cáo')", "evidence": []}
    ev = [run.rel(f.png) for f in marks if f.png][:4]
    return {"status": CAN_XEM, "reason": "có chữ gợi ý reward, cần nhìn vị trí", "evidence": ev,
            "visual": {"images": ev, "question": "Nút mở reward ad có icon hoặc chữ 'Watch an ad' (hay tương đương) không?"}}


def reward_click_handled(run: Run, params: dict) -> dict:
    if any(REWARD_RE.search(t) for f in run.frames for t in f.texts()):
        return {"status": BLOCKED, "reason": "có vị trí reward ad nhưng tool chưa bấm thử reward", "evidence": []}
    return {"status": NA, "reason": "lượt này không gặp reward ad", "evidence": []}


def external_link_has_ad_label(run: Run, params: dict) -> dict:
    shots = [run.rel(f.png) for f in run.frames if f.png and run.meta["package"] in f.activity][::3][:10]
    return {"status": CAN_XEM, "reason": "tìm nút dẫn sang app/web khác (cross-promo) trên các màn đã đi", "evidence": shots,
            "visual": {"images": shots, "question": "Có nút/khối nào dẫn sang app hoặc web khác (quảng bá chéo) không? "
                                                     "Nếu có, nó có chữ 'AD' hoặc cảnh báo sang nội dung khác không?"}}


def ai_result_has_report_button(run: Run, params: dict) -> dict:
    """Result screen = an app screen offering Download/Save/Share of what was generated."""
    results = [f for f in run.frames if run.meta["package"] in f.activity and sum(
        1 for n in f.nodes if re.search(r"download|tải xuống|save|lưu", n["text"] or n["desc"], re.I)) >= 1
        and any(re.search(r"share|chia sẻ", n["text"] or n["desc"], re.I) for n in f.nodes)]
    if not results:
        return {"status": BLOCKED, "reason": "lượt này chưa tới được màn kết quả AI", "evidence": []}
    with_report = [f for f in results if any(re.search(r"^(report|báo cáo|report content)$|report",
                                                       (n["text"] or n["desc"]).strip(), re.I) for n in f.nodes)]
    f = (with_report or results)[0]
    ev = [run.rel(f.png or f.xml)]
    if with_report:
        return {"status": PASS, "reason": f"màn kết quả ({f.activity.rsplit('.', 1)[-1]}) có nút Report", "evidence": ev}
    return {"status": FAIL, "reason": f"màn kết quả ({f.activity.rsplit('.', 1)[-1]}) không có nút báo cáo nội dung",
            "evidence": ev}


CHECKERS = {f.__name__: f for f in (
    sub_plan_info_complete, sub_trial_then_price, sub_trial_text_smaller, sub_trial_not_separate_button,
    sub_sale_shows_both_prices, sub_cancel_anytime_text, sub_privacy_tos_in_app, sub_billing_popup_dates,
    sub_cancel_option_after_purchase, sub_ios_restore, reward_has_watch_ad_label, reward_click_handled,
    external_link_has_ad_label, ai_result_has_report_button)}

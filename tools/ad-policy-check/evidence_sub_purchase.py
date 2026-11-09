"""Buy a subscription from the paywall, look for the in-app cancel option, then cancel it on Play.

Sub rule #5 needs the Play payment sheet (trial start / first charge date, plan name
without "trial"); rule #9 needs the app after a purchase (a "cancel sub" option that
opens Play > Subscriptions). Every account the team uses is a Play license tester,
so the purchase is a test purchase. The subscription is cancelled at the end so the
next run still meets the paywall; if cancelling fails the record says so.

Writes purchase.json and adds screenshots to frames/ via the evidence hook.
"""
import asyncio
import json
import re
import time
from pathlib import Path

from adb_sync import a_key, a_tap, a_top_activity
from ui_nodes import center

PLAY = "com.android.vending"
BUY_RE = re.compile(r"^(continue|subscribe|start|start free trial|try (it )?free|tiếp tục|đăng ký|mua|buy|get premium|"
                    r"upgrade|nâng cấp)", re.I)
NOT_BUY_RE = re.compile(r"with ads|kèm quảng cáo|later|restore", re.I)
PLAY_BUY_RE = re.compile(r"^(subscribe|đăng ký|buy|mua|1-tap buy|mua bằng 1 lần nhấn)$", re.I)
CANCEL_IN_APP_RE = re.compile(r"cancel (sub|subscription|plan)|manage (sub|subscription)|hủy (gói|đăng ký)|"
                              r"huỷ (gói|đăng ký)|quản lý (gói|đăng ký)", re.I)
SETTINGS_RE = re.compile(r"setting|cài đặt", re.I)
TEST_CARD_RE = re.compile(r"test card|thẻ thử nghiệm|test subscription|gói thuê bao thử nghiệm", re.I)
PLAY_ERROR_RE = re.compile(r"error|lỗi|declined|bị từ chối|already own|đã sở hữu|try again|thử lại", re.I)
PLAY_CANCEL_RE = re.compile(r"^(cancel subscription|hủy gói thuê bao|huỷ gói thuê bao|cancel)$", re.I)
PLAY_NEXT_RE = re.compile(r"^(continue|tiếp tục|no thanks|không, cảm ơn|decline offer)$", re.I)


async def _wait_for(serial: str, pred, seconds: float) -> str:
    end = time.monotonic() + seconds
    act = ""
    while time.monotonic() < end:
        act = await a_top_activity(serial) or ""
        if pred(act):
            return act
        await asyncio.sleep(0.7)
    return act


async def _tap_label(ex, nodes: list[dict], pattern: re.Pattern, skip: re.Pattern | None = None) -> str | None:
    for n in nodes:
        lab = (n["text"] or n["desc"]).strip()
        if lab and pattern.search(lab) and not (skip and skip.search(lab)):
            target = n if n["clickable"] else ex._clickable_parent(nodes, n)
            if target:
                await a_tap(ex.serial, *center(target["bounds"]))
                return lab
    return None


async def _look_any(ex) -> tuple[str, list[dict]]:
    """Dump + screenshot even outside the app (the Play sheet is the evidence here)."""
    xml = await asyncio.to_thread(ex._dump)
    await asyncio.to_thread(ex.ev.save, xml)
    from ui_nodes import parse_nodes
    return await a_top_activity(ex.serial) or "", parse_nodes(xml)


async def purchase_pass(ex, out_dir: Path) -> dict:
    """`ex` is the HomeExplorer that just opened the paywall."""
    rec: dict = {"steps": []}

    def step(msg: str) -> None:
        rec["steps"].append(msg)

    act, nodes = await _look_any(ex)
    if not any(m in act for m in ("Billing", "Paywall", "Premium", "Iap", "Subscription", "Purchase")):
        rec["result"] = f"không ở paywall (đang ở {act})"
        return _save(out_dir, rec)
    rec["paywall_texts"] = [n["text"] for n in nodes if n["text"].strip()]
    buy = await _tap_label(ex, nodes, BUY_RE, NOT_BUY_RE)
    step(f"bấm nút mua: {buy}")
    if not buy:
        rec["result"] = "không thấy nút mua trên paywall"
        return _save(out_dir, rec)
    act = await _wait_for(ex.serial, lambda a: a.startswith(PLAY), 12)
    if not act.startswith(PLAY):
        rec["result"] = f"không mở sheet thanh toán của Play (đang ở {act})"
        return _save(out_dir, rec)
    # The sheet first shows "Loading…" (seen on Pixel 4); read it once it has real content.
    sheet: list[dict] = []
    for _ in range(6):
        await asyncio.sleep(2.5)
        _act, sheet = await _look_any(ex)
        texts = [n["text"] for n in sheet if n["text"].strip()]
        if texts and not all(re.fullmatch(r"loading…?|loading\.\.\.|đang tải…?", t.strip(), re.I) for t in texts):
            break
    rec["billing_sheet_texts"] = [n["text"] for n in sheet if n["text"].strip()]
    rec["billing_sheet_t"] = ex._ms()
    # Only ever pay with Play's license-test card. Another account on the phone would be charged for real.
    if not TEST_CARD_RE.search(" ".join(rec["billing_sheet_texts"])):
        rec["result"] = "sheet Play không ghi 'Test card' — tài khoản không phải license tester, KHÔNG mua"
        await a_key(ex.serial, "KEYCODE_BACK")
        await ex.back_to_app()
        return _save(out_dir, rec)
    paid = await _tap_label(ex, sheet, PLAY_BUY_RE)
    step(f"bấm trên Play: {paid}")
    if not paid:
        rec["result"] = "mở được sheet Play nhưng không thấy nút Subscribe — đã BACK, chưa mua"
        await ex.back_to_app()
        return _save(out_dir, rec)
    await asyncio.sleep(8)
    _act, done = await _look_any(ex)
    rec["after_buy_texts"] = [n["text"] for n in done if n["text"].strip()][:20]
    after = " ".join(rec["after_buy_texts"])
    await ex.back_to_app()
    await asyncio.sleep(2)
    await ex.close_popups()
    if PLAY_ERROR_RE.search(after):
        rec["result"] = f"Play không mua được: {after[:120]}"
        return _save(out_dir, rec)
    rec["purchased"] = True
    rec["purchased_at"] = time.time()

    # Rule #9: a "cancel sub" option in the app that opens Play > Subscriptions.
    _home, nodes = await ex.look()
    where = await _tap_label(ex, nodes, CANCEL_IN_APP_RE)
    if not where:
        settings = await _tap_label(ex, nodes, SETTINGS_RE)
        step(f"vào cài đặt: {settings}")
        await asyncio.sleep(2.5)
        _s, nodes = await ex.look()
        where = await _tap_label(ex, nodes, CANCEL_IN_APP_RE)
    rec["cancel_option"] = where
    if where:
        act = await _wait_for(ex.serial, lambda a: a.startswith(PLAY), 10)
        rec["cancel_option_opens"] = act
        page = await _wait_play_page(ex, step)
        rec["cancel_page_texts"] = [n["text"] for n in page if n["text"].strip()][:30]
        sheet_name = next((t for t in rec.get("billing_sheet_texts", [])[1:3] if " - " in t), "")
        rec["cancelled"] = await _cancel_on_play(ex, page, step, sheet_name)
    else:
        rec["cancelled"] = False
        step("không thấy lựa chọn huỷ sub trong app; sub test vẫn còn hiệu lực")
    await ex.back_to_app()
    rec["result"] = "đã mua" + (", đã huỷ trên Play" if rec.get("cancelled") else ", CHƯA huỷ được sub")
    return _save(out_dir, rec)


def _bottom(nodes: list[dict], pattern: re.Pattern) -> dict | None:
    """The lowest node matching: Play repeats its button label ("Cancel subscription") as the page title."""
    hits = [n for n in nodes if pattern.search((n["text"] or n["desc"]).strip()) and n["bounds"][3] > 0]
    return max(hits, key=lambda n: n["bounds"][1]) if hits else None


async def _wait_play_page(ex, step) -> list[dict]:
    """Play's Subscriptions page loads for several seconds and sometimes answers 'Server error'."""
    retried = False
    nodes: list[dict] = []
    for _ in range(6):
        await asyncio.sleep(2.5)
        _a, nodes = await _look_any(ex)
        texts = " ".join(n["text"] for n in nodes)
        if "Active" in texts or "Đang hoạt động" in texts or PLAY_CANCEL_RE.search(texts):
            return nodes
        if "Server error" in texts or "Something went wrong" in texts or "Đã xảy ra lỗi" in texts:
            if retried:
                step("Play báo 'Server error' ở trang Subscriptions (đã thử lại); sub test tự hết sau ~6 lần gia hạn")
                return nodes
            retried = True
            await _tap_label(ex, nodes, re.compile(r"^(try again|thử lại)$", re.I))
    return nodes


async def _cancel_on_play(ex, page: list[dict], step, app_name: str = "") -> bool:
    """Play > Subscriptions (list) > this app's sub > Cancel subscription > (reason page) Cancel subscription.

    Measured on Pixel 4 (04/11/2026): the list shows "Test: <app>" under Active; its page has the
    cancel button at the bottom, the reason page again; success reads "Canceled".
    """
    name = re.escape(app_name.split(" - ")[0]) if app_name else ""
    if name:
        entry = next((n for n in page if re.search(rf"^(test: )?{name}", n["text"] or "", re.I)), None)
        if entry:
            await a_tap(ex.serial, *center(entry["bounds"]))
            step(f"Play: mở gói {entry['text']}")
            await asyncio.sleep(4)
    for _ in range(4):
        _a, nodes = await _look_any(ex)
        texts = " ".join(n["text"] for n in nodes)
        if re.search(r"\bCanceled\b|Đã hủy|Đã huỷ|will end on|sẽ kết thúc", texts):
            step("Play: đã huỷ")
            await a_key(ex.serial, "KEYCODE_BACK")
            return True
        btn = _bottom(nodes, PLAY_CANCEL_RE) or _bottom(nodes, PLAY_NEXT_RE)
        if not btn:
            break
        await a_tap(ex.serial, *center(btn["bounds"]))
        await asyncio.sleep(4)
    step("Play: không xác nhận được đã huỷ")
    await a_key(ex.serial, "KEYCODE_BACK")
    return False


def _save(out_dir: Path, rec: dict) -> dict:
    (out_dir / "purchase.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    return rec

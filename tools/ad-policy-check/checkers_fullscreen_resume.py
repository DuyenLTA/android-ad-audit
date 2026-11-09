"""Checkers for interstitial and resume (app open) ads.

Each checker: (run, params) -> {"status", "reason", "evidence": [rel paths], "visual": {...}?}
status: PASS / FAIL / CAN_XEM (Claude must look; `visual` says at what) / BLOCKED / NA.
"""
from policy_evidence import Run, is_fullscreen_ad_activity

PASS, FAIL, CAN_XEM, BLOCKED, NA = "PASS", "FAIL", "CAN_XEM", "BLOCKED", "NA"


def _short(activity: str) -> str:
    return activity.rsplit(".", 1)[-1] if activity else "?"


def _no_inter(run: Run):
    return {"status": NA, "reason": "lượt này không gặp quảng cáo toàn màn hình nào", "evidence": []}


def inter_not_before_splash(run: Run, params: dict) -> dict:
    eps = run.episodes()
    if not eps:
        return _no_inter(run)
    app = run.app_activities()
    first_app = app[0] if app else None
    ok = first_app is not None and first_app["t"] < eps[0].start
    return {"status": PASS if ok else FAIL,
            "reason": (f"app mở {_short(first_app['activity'])} ở {first_app['t']/1000:.1f}s, inter đầu tiên hiện ở "
                       f"{eps[0].start/1000:.1f}s (sau màn chờ)") if ok else
                      "inter hiện trước khi app có màn nào", "evidence": ["activities.jsonl"]}


def _app_open_like(run: Run, e) -> bool:
    """Episodes that come back to the same screen by design: resume ads and ads after a utility trip."""
    window = run.resume_window()
    if window and window[0]["t"] <= e.start <= window[-1]["t"]:
        return True
    return any(v["t"] <= e.start <= v["t"] + 20000 for v in run.jsonl("utility-visits.jsonl"))


# The screen under the ad resumes for a moment before the app starts the next one (seen on AIP920:
# Question back for 0.6s, then Billing). Only a screen that stays this long counts as "where the ad left you".
SETTLE_MS = 2000


def _settled_after(run: Run, e) -> str:
    pkg = run.meta["package"] + "/"
    nxt = next((a for a in run.activities if a["t"] > e.end and a["activity"].startswith(pkg)), None)
    if e.after == e.before and nxt and nxt["t"] - e.end < SETTLE_MS and not is_fullscreen_ad_activity(nxt["activity"]):
        return nxt["activity"]
    return e.after


def inter_changes_screen(run: Run, params: dict) -> dict:
    eps = [e for e in run.episodes() if e.end is not None and not _app_open_like(run, e)]
    if not eps:
        return _no_inter(run)
    after = {e.index: _settled_after(run, e) for e in eps}
    rows = [f"#{e.index}: {_short(e.before)} → ad → {_short(after[e.index])}" for e in eps]
    same = [e for e in eps if e.before == after[e.index]]
    return {"status": FAIL if same else PASS,
            "reason": "; ".join(rows) + ("" if not same else " — tắt ad mà vẫn ở màn cũ"),
            "evidence": ["activities.jsonl"]}


def _sheet(run: Run, e, name: str, before_s: float, after_s: float):
    end = e.end if e.end is not None else e.start + 30000
    return run.video_sheet(int(e.start - before_s * 1000), int(end + after_s * 1000), name)


def inter_loading_before(run: Run, params: dict) -> dict:
    eps = run.episodes()
    if not eps:
        return _no_inter(run)
    sheets = [s for e in eps if (s := _sheet(run, e, f"inter{e.index}-before", 4, -0.0)) is not None]
    rel = [run.rel(s) for s in sheets]
    return {"status": CAN_XEM, "reason": "xem video 4s trước mỗi inter", "evidence": rel,
            "visual": {"images": rel, "question": "Ngay trước khi inter hiện (ô cuối trước màn ad) có màn/hộp loading "
                                                    "ad không? Inter ngay sau splash: màn splash có thanh/loading là đạt."}}


def inter_latency(run: Run, params: dict) -> dict:
    # The FO journey reaches each inter by a tap the driver makes; the video around it is the evidence.
    return inter_loading_before(run, params) | {"reason": "xem video: từ lúc bấm/hết loading tới khi inter hiện có trễ không"}


def inter_close_within_15s(run: Run, params: dict) -> dict:
    eps = [e for e in run.episodes() if e.end is not None]
    if not eps:
        return _no_inter(run)
    # Tapped episodes are paused by the tap; only untouched ones say when X appears.
    tapped = {p["t"] for p in run.probes if p["kind"] == "fullscreen"}
    clean = [e for e in eps if not any(e.start <= t <= e.end for t in tapped)]
    if not clean:
        return {"status": BLOCKED, "reason": "mọi inter đều đã bị bấm thử nên không đo được nút X", "evidence": []}
    rel = []
    for e in clean:
        s = run.video_sheet(e.start, e.end + 1000, f"inter{e.index}-close")
        if s:
            rel.append(run.rel(s))
    lasted = ", ".join(f"#{e.index} {(e.end - e.start)/1000:.0f}s" for e in clean)
    return {"status": CAN_XEM, "reason": f"inter hiện: {lasted}; xem video nút X/đếm ngược",
            "evidence": rel,
            "visual": {"images": rel, "question": f"Mỗi ô là 1 giây kể từ khi inter hiện. Nút tắt (X/Skip/Close) xuất hiện "
                                                  f"ở ô thứ mấy? Phải ≤ {params.get('max_seconds', 15)}s."}}


def _click(run: Run, kind: str) -> dict:
    tries = [p for p in run.probes if p["kind"] == kind]
    # A tap that only paused a video creative was followed by a tap on the CTA it revealed: the ad is
    # judged on that last tap of the chain.
    followed = {p["follow_up_of"] for p in tries if "follow_up_of" in p}
    tries = [p for p in tries if p["t"] not in followed]
    if not tries:
        return {"status": BLOCKED, "reason": "lượt này chưa bấm thử được loại ad này", "evidence": []}
    bad = [p for p in tries if p["handled"] is False]
    unclear = [p for p in tries if p["handled"] == "unclear"]
    rows = "; ".join(f"{_short(p['activity'])} → {_short(p['after']) if p['handled'] == 'unclear' else p['after'].split('/')[0]}"
                     for p in tries)
    if bad:
        status = FAIL
    elif unclear:
        # Moved to another app screen: the app's own navigation, or the ad? Claude decides from the
        # frames around the tap (visual queue), never left open.
        status = CAN_XEM
    else:
        status = PASS
    out = {"status": status, "reason": f"bấm {len(tries)} lần: {rows}", "evidence": ["click-probes.jsonl"]}
    if unclear and not bad:
        shots = [run.rel(s) for p in unclear
                 if (s := run.video_sheet(p["t"] - 1000, p["t"] + 4000, f"click-{kind}-{p['t']}", fps=2)) is not None]
        out["evidence"] += shots
        out["visual"] = {"images": shots, "question": "Mỗi ô 0,5s quanh lần bấm vào ad. Sau khi bấm, màn mới là trang "
                                                      "của ad (landing/store/ad mở rộng) hay chỉ là app tự chuyển màn? "
                                                      "Trang của ad → PASS, app tự chuyển/không gì → FAIL."}
    return out


def inter_click_handled(run: Run, params: dict) -> dict:
    return _click(run, "fullscreen")


def resume_window_ads(run: Run) -> list:
    return [a for a in run.resume_window() if "AdActivity" in a["activity"]]


def resume_background_opaque(run: Run, params: dict) -> dict:
    if not run.resume_window():
        return {"status": BLOCKED, "reason": "lượt này chưa chạy bước ẩn app rồi mở lại", "evidence": []}
    if not resume_window_ads(run):
        where = (run.jsonl("resume-trials.jsonl") or [{}])[0].get("screen") or "Home"
        return {"status": NA, "reason": f"ẩn rồi mở lại app ở {_short(where)} không hiện resume ad (app không bật "
                                        "resume) — không có ad resume để xem nền", "evidence": ["activities.jsonl"]}
    w = run.resume_window()
    s = run.video_sheet(w[0]["t"], w[-1]["t"] + 6000, "resume")
    rel = [run.rel(s)] if s else []
    return {"status": CAN_XEM, "reason": "xem nền dưới resume ad", "evidence": rel,
            "visual": {"images": rel, "question": "Lúc resume ad hiện, có nhìn xuyên thấy nội dung app phía dưới không?"}}


def resume_not_after_utility(run: Run, params: dict) -> dict:
    visits = run.jsonl("utility-visits.jsonl")
    if not visits:
        return {"status": BLOCKED, "reason": "chưa vào được màn Privacy/Terms/Rate/Feedback/Share nào để thử quay lại",
                "evidence": []}
    rows = [f"{v['label']} ({v['way']}): {'CÓ ad ' + _short(v['ad_after']) if v['ad_after'] else 'không có ad'}"
            for v in visits]
    bad = [v for v in visits if v["ad_after"]]
    return {"status": FAIL if bad else PASS, "reason": "; ".join(rows), "evidence": ["utility-visits.jsonl"]}


def resume_click_handled(run: Run, params: dict) -> dict:
    if run.resume_window() and not resume_window_ads(run):
        return {"status": NA, "reason": "không có resume ad hiện ra trong lượt", "evidence": []}
    return _click(run, "resume")


CHECKERS = {f.__name__: f for f in (
    inter_not_before_splash, inter_changes_screen, inter_loading_before, inter_latency,
    inter_close_within_15s, inter_click_handled,
    resume_background_opaque, resume_not_after_utility, resume_click_handled)}

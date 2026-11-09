"""Checkers for native and banner ads, measured on UI dumps of every screen the driver read.

Bounds come straight from uiautomator (physical px); dp = px * 160 / density.
A native is measured only once settled (AdChoices bound, shimmer gone), the same
condition the click prober uses.
"""
from checkers_fullscreen_resume import BLOCKED, CAN_XEM, FAIL, NA, PASS, _click, _short
from policy_evidence import Run
from ui_nodes import area, banner_node, intersection, is_fullscreen_ad_activity


def _mid_swipe(box: tuple, screen_w: int) -> bool:
    """A native cut by a screen edge while a pager moves (seen: 674 of 1080px wide mid-swipe):
    parts may be off screen, so it is not measured."""
    width = box[2] - box[0]
    return (box[0] <= 0 or box[2] >= screen_w) and width < 0.9 * screen_w and width > 0.5 * screen_w


def _settled(run: Run) -> list:
    """(frame, parts) for each screen showing a settled native; one per activity+page text."""
    out, seen = [], set()
    for f in run.frames:
        p = f.native
        if not (p["native"] and p["adchoices"] and p["shimmer"] is None):
            continue
        if _mid_swipe(p["native"]["bounds"], run.meta["screen_px"][0]):
            continue
        key = (f.activity, tuple(f.texts()[:3]))
        if key in seen:
            continue
        seen.add(key)
        out.append((f, p))
    return out


def _none(kind="native"):
    return {"status": NA, "reason": f"lượt này không gặp {kind} nào đã hiện xong", "evidence": []}


def _measure(run: Run, fn, label: str) -> dict:
    rows, bad, ev = [], [], []
    for f, p in _settled(run):
        ok, note = fn(f, p)
        rows.append(f"{_short(f.activity)}: {note}")
        ev.append(run.rel(f.png or f.xml))
        if not ok:
            bad.append(rows[-1])
    if not rows:
        return _none()
    return {"status": FAIL if bad else PASS, "reason": f"{label} — " + "; ".join(bad or rows[:4]), "evidence": ev[:6]}


def native_mediaview_min_size(run: Run, params: dict) -> dict:
    min_dp, dpi = params.get("min_dp", 120), run.meta["density_dpi"]

    def fn(f, p):
        if not p["media"]:
            return False, "không thấy MediaView"
        b = p["media"]["bounds"]
        w, h = (b[2] - b[0]) * 160 / dpi, (b[3] - b[1]) * 160 / dpi
        return w >= min_dp and h >= min_dp, f"{w:.0f}x{h:.0f}dp"
    return _measure(run, fn, f"MediaView ≥{min_dp}x{min_dp}dp")


def native_attribution_min_size(run: Run, params: dict) -> dict:
    min_px = params.get("min_px", 15)

    def fn(f, p):
        b = p["attribution"]["bounds"] if p["attribution"] else None
        if not b:
            return False, "không thấy nhãn Ad"
        w, h = b[2] - b[0], b[3] - b[1]
        return w >= min_px and h >= min_px, f"{w}x{h}px"
    return _measure(run, fn, f"nhãn Ad ≥{min_px}px")


def native_adchoices_inside(run: Run, params: dict) -> dict:
    need = params.get("min_inside_ratio", 0.5)

    def fn(f, p):
        c, n = p["adchoices"]["bounds"], p["native"]["bounds"]
        r = intersection(c, n) / max(1, area(c))
        return r >= need, f"trong khung {r:.0%}"
    return _measure(run, fn, "AdChoices nằm trong khung native")


def _contains(outer: tuple, inner: tuple, slack: int = 40) -> bool:
    """outer wraps inner (within a few px): a container of the ad, not content lying over it."""
    return (outer[0] <= inner[0] + slack and outer[1] <= inner[1] + slack
            and outer[2] >= inner[2] - slack and outer[3] >= inner[3] - slack)


def _app_webviews(f, package: str) -> list:
    """WebViews of the app that are not part of an ad (a native's media is often a WebView)."""
    if is_fullscreen_ad_activity(f.activity):
        return []                     # an interstitial is itself a WebView; it is not the app's page
    ad = f.native["native"]["bounds"] if f.native["native"] else None
    ban = banner_node(f.nodes)
    return [n for n in f.nodes if "WebView" in n["cls"] and n["pkg"] == package
            and not (ad and _contains(ad, n["bounds"])) and not (ban and _contains(ban["bounds"], n["bounds"]))]


def _overlap(run: Run, region_of) -> dict:
    rows, bad, ev = [], [], []
    for f in run.frames:
        box = region_of(f)
        if not box:
            continue
        hit = [n for n in f.nodes if n["clickable"] and n["pkg"] == run.meta["package"]
               and intersection(n["bounds"], box) > 0
               and not (n["bounds"][0] >= box[0] and n["bounds"][1] >= box[1]
                        and n["bounds"][2] <= box[2] and n["bounds"][3] <= box[3])
               and not _contains(n["bounds"], box)]   # the ad's own container (often id-less) is not content
        rows.append(_short(f.activity))
        if hit:
            bad.append(f"{_short(f.activity)}: {hit[0]['rid'] or hit[0]['text'] or hit[0]['cls']} lấn vào ad")
            ev.append(run.rel(f.png or f.xml))
    if not rows:
        return None
    return {"status": FAIL if bad else PASS,
            "reason": "; ".join(bad[:4]) if bad else f"không nút nào của app lấn vào khung ad ({len(rows)} khung hình)",
            "evidence": ev[:6]}


def native_content_overlap(run: Run, params: dict) -> dict:
    r = _overlap(run, lambda f: f.native["native"]["bounds"] if f.native["native"] and f.native["adchoices"] else None)
    return r or _none()


def banner_content_overlap(run: Run, params: dict) -> dict:
    r = _overlap(run, lambda f: (b := banner_node(f.nodes)) and b["bounds"])
    return r or _none("banner")


def _entry_times(run: Run) -> dict[str, int]:
    """First time each app activity came to the front."""
    out: dict[str, int] = {}
    for a in run.activities:
        out.setdefault(a["activity"], a["t"])
    return out


def _native_slot(f) -> dict:
    n = f.native
    return {"box": n["native"], "shimmer": n["shimmer"], "loaded": n["native"] and n["adchoices"]}


def _banner_slot(f) -> dict:
    box = banner_node(f.nodes)
    if not box:
        return {"box": None, "shimmer": None, "loaded": None}
    b = box["bounds"]
    inside = [n for n in f.nodes if b[0] <= n["bounds"][0] and b[1] <= n["bounds"][1]
              and n["bounds"][2] <= b[2] and n["bounds"][3] <= b[3]]
    shimmer = next((n for n in inside if "shimmer" in n["rid"].lower() or "loading" in n["rid"].lower()), None)
    return {"box": box, "shimmer": shimmer, "loaded": None if shimmer else box}


def _placeholder(run: Run, kind: str, params: dict, size: bool) -> dict:
    """Per screen showing this ad: size of the placeholder vs the ad, or what showed in the first 0.5s.

    The first UI dump of a screen comes 1-3s after entering it, too late for "loading from the very
    start" (0.5s). That half is judged on the video around each screen entry instead.
    """
    parts = _native_slot if kind == "native" else _banner_slot
    by_act: dict[str, list] = {}
    for f in run.frames:
        by_act.setdefault(f.activity, []).append(f)
    entries = _entry_times(run)
    rows, bad, ev, sheets = [], [], [], []
    for act, frames in by_act.items():
        with_ad = [(f, p) for f in frames if (p := parts(f))["box"]]
        if not with_ad:
            continue
        if size:
            sh = next(((f, p) for f, p in with_ad if p["shimmer"]), None)
            ad = next(((f, p) for f, p in with_ad if p["loaded"]), None)
            if not (sh and ad):
                continue
            r = area(sh[1]["shimmer"]["bounds"]) / max(1, area(ad[1]["box"]["bounds"]))
            sh = sh[0]
            rows.append(f"{_short(act)}: loading = {r:.0%} khung ad")
            ev.append(run.rel(sh.png or sh.xml))
            if r < params.get("min_ratio", 0.75):
                bad.append(rows[-1])
        elif act in entries:
            t = entries[act]
            s = run.video_sheet(t - 500, t + 2500, f"entry-{_short(act)}", fps=4, cols=6)
            if s:
                sheets.append(run.rel(s))
                rows.append(_short(act))
    if not rows:
        if size and any(True for f in run.frames if parts(f)["box"]):
            # The ad was always already loaded when a dump came: no loading frame was ever caught, so the
            # size is judged on the entry video instead.
            out = _placeholder(run, kind, params, size=False)
            if out.get("visual"):
                out["reason"] = f"không chụp được lúc {kind} còn loading; xem video lúc vào màn"
                out["visual"]["question"] = (f"Mỗi ô 0,25s quanh lúc vào màn có {kind}. Khung loading (trước khi ad "
                                             f"hiện) có chiếm ít nhất {params.get('min_ratio', 0.75):.0%} kích thước ad "
                                             "sau khi hiện không? Không có khung loading nào → FAIL.")
            return out
        return _none(kind)
    if not size:
        return {"status": CAN_XEM, "reason": f"xem video lúc vào từng màn có {kind}: " + ", ".join(rows),
                "evidence": sheets,
                "visual": {"images": sheets, "question": f"Mỗi ô 0,25s, ô thứ 3 là lúc vào màn. Trong "
                                                         f"{params.get('max_seconds', 0.5)}s đầu (2 ô sau lúc vào) vị trí "
                                                         "đặt native đã có khung loading hoặc ad chưa, hay ad/loading bật "
                                                         "ra đột ngột sau đó?"}}
    return {"status": FAIL if bad else PASS, "reason": "; ".join(bad or rows), "evidence": ev[:6]}


def native_placeholder_first(run, params): return _placeholder(run, "native", params, size=False)
def native_placeholder_size(run, params): return _placeholder(run, "native", params, size=True)
def banner_placeholder_first(run, params): return _placeholder(run, "banner", params, size=False)
def banner_placeholder_size(run, params): return _placeholder(run, "banner", params, size=True)
def native_cta_click_handled(run, params): return _click(run, "native_cta")


def banner_click_handled(run, params):
    if not any(banner_node(f.nodes) for f in run.frames):
        return _none("banner")
    return _click(run, "banner")


def no_ad_on_webview(run: Run, params: dict) -> dict:
    pkg = run.meta["package"]
    bad = [f for f in run.frames if (f.native["native"] or banner_node(f.nodes)) and _app_webviews(f, pkg)]
    if bad:
        return {"status": FAIL, "reason": f"ad cùng màn với WebView của app: {_short(bad[0].activity)}",
                "evidence": [run.rel(bad[0].png or bad[0].xml)]}
    has_web = any(_app_webviews(f, pkg) for f in run.frames)
    return {"status": PASS if has_web else NA,
            "reason": "màn webview của app không có ad" if has_web else "lượt này không đi qua màn webview nào của app",
            "evidence": []}


def _visual_frames(run: Run, question: str, reason: str) -> dict:
    shots = [run.rel(f.png) for f, _ in _settled(run) if f.png]
    if not shots:
        return _none()
    return {"status": CAN_XEM, "reason": reason, "evidence": shots[:8], "visual": {"images": shots[:8], "question": question}}


def native_layout_not_clipped(run, params):
    return _visual_frames(run, "Native ad trong từng ảnh: nội dung (tiêu đề, media, CTA, nhãn Ad) có bị cắt hoặc đè nhau không?",
                          "xem ảnh từng native")


def native_background_differs(run, params):
    return _visual_frames(run, "Nền của khung native có khác nền app xung quanh (phân biệt được ad với nội dung) không?",
                          "xem ảnh từng native")


def no_ad_on_empty_screen(run, params):
    return _visual_frames(run, "Màn có native/banner có nội dung thật của app (không phải màn trống chỉ có ad) không?",
                          "xem ảnh từng màn có ad")


CHECKERS = {f.__name__: f for f in (
    native_mediaview_min_size, native_attribution_min_size, native_adchoices_inside, native_content_overlap,
    banner_content_overlap, native_placeholder_first, native_placeholder_size, banner_placeholder_first,
    banner_placeholder_size, native_cta_click_handled, banner_click_handled, no_ad_on_webview,
    native_layout_not_clipped, native_background_differs, no_ad_on_empty_screen)}

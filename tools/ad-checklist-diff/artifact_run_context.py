"""Turn one run's triage into the lines the report puts under its title.

These used to be typed into the template by hand each run, which is how a page
ended up claiming "delta: không đổi" next to a different run's id. Anything the
triage already knows is read from it instead; only the run id, the mode and the
report path have to be passed in, because nothing on disk records them.

The capture warning matters most: a journey that stopped at onboarding makes
every "chưa thấy trong log" row meaningless, and a reader who cannot see that
warning has no way to know the page is built on a half-finished capture.

Every condition warned about here is one the triage already records. A tool that
detects a condition and stays quiet about it pushes the work onto whoever reads
the number afterwards -- and that reader is looking at the page, not at the
handbook where it used to be written down.
"""
import html

MODE_LABELS = {
    "capture": "capture — lái máy rồi audit",
    "apk": "apk — đọc APK, không lái UI",
    "skip": "skip — phán lại trên triage sẵn có",
}

DELTA_PARTS = (
    ("broke", "dòng mới lệch"),
    ("fixed", "dòng đã fix"),
    ("new_leftover_ids", "ID lạ mới"),
)


def delta_note(triage: dict | None) -> str:
    """What changed since the previous run, in the words the summary uses."""
    if not triage:
        return "không rõ"
    delta = triage.get("delta") or {}
    if not delta.get("changed"):
        return "không đổi"
    parts = [
        f"{len(delta.get(key) or [])} {label}"
        for key, label in DELTA_PARTS
        if delta.get(key)
    ]
    return ", ".join(parts) or "có đổi"


def mode_label(mode: str | None) -> str:
    return MODE_LABELS.get(mode or "", mode or "không rõ")


def capture_warning(triage: dict | None) -> str:
    """An HTML banner when the capture behind this page came up short.

    Three states have to stay distinct: no capture at all (missed_home is None),
    a capture where some journey never reached Home (a non-empty list), and a
    triage written before any of this was recorded (the key is simply absent).
    """
    if not triage:
        return ""

    warnings = []

    signals = triage.get("dev_build_signals") or []
    if signals:
        warnings.append(
            "<b>Nghi đang audit build dev</b> — " + "; ".join(
                html.escape(str(s)) for s in signals
            ) + ". Checklist ghi giá trị production, nên phần lớn dòng lệch ở đây "
            "có thể chỉ là sai build chứ không phải sheet ghi sai."
        )

    if "missed_home" in triage:
        missed = triage["missed_home"]
        if missed is None:
            warnings.append(
                "Lượt này <b>không capture</b> — mọi kết luận dựa trên "
                "&ldquo;log không có&rdquo; đều không đứng được."
            )
        elif missed:
            names = ", ".join(html.escape(str(m)) for m in missed)
            warnings.append(
                f"Luồng <b>{names}</b> chưa tới được Home, nên các dòng cần màn "
                "phía sau Home có thể chỉ là chưa capture tới, không phải lỗi thật."
            )
    else:
        warnings.append(
            "Triage sinh từ bản tool cũ, không ghi lại lượt capture đã đi tới đâu."
        )

    empty = triage.get("empty_filters") or []
    if empty:
        names = ", ".join(html.escape(str(f)) for f in empty)
        warnings.append(
            f"Filter <b>{names}</b> không khớp dòng log nào — cả vùng đó chưa được capture."
        )

    # False means the APK embeds no real ad unit id, so a checklist id missing
    # from it is the normal state and says nothing. Silence here is what let 44
    # rows be filed against the sheet on a build that never held those ids.
    if triage.get("apk_scan_applicable") is False:
        warnings.append(
            "Build này nạp ad unit ID lúc chạy, nên <b>không tra được ID trong APK</b> — "
            "các dòng ads phải đối chiếu bằng log, và việc ID vắng mặt trong APK "
            "không nói lên điều gì."
        )

    if not warnings:
        return ""

    items = "".join(f"<p>{w}</p>" for w in warnings)
    return (
        '<div class="callout"><div class="eyebrow">Cảnh báo về lượt capture</div>'
        f"{items}</div>"
    )

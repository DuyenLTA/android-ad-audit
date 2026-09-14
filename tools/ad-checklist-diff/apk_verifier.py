"""Verify checklist rows against the installed APK, for values logcat never shows.

Two independent gaps the log diff cannot close, both app-agnostic:

1. **AdMob App ID.** Declared as an `android:name="com.google.android.gms.ads.
   APPLICATION_ID"` meta-data entry in AndroidManifest.xml. Some apps never
   print it: a real capture had zero `ca-app-pub-...~...` strings in 3MB of log
   across every trusted filter, so a perfectly correct App ID read as "Lệch".

2. **Ad unit IDs of placements the capture never exercised.** An ad unit ID
   reaches logcat only when the app actually requests that placement, so
   verifying every row meant walking every screen (and some, like an uninstall
   survey flow, are impractical to trigger on demand). The IDs are compiled
   into the APK's dex, so their *presence in the build* can be confirmed
   without touching the app at all.

An APK match is weaker evidence than a log match and is labelled as such: it
proves the build contains the ID, not that the screen in question is enabled or
wired to it. A row already confirmed in the log is never re-judged here.

Gap 2 rests on an assumption that is not always true: that the build compiles in
its real ad unit IDs. Apps that fetch IDs from remote config at runtime ship an
APK containing only the AdMob SDK's own sample IDs, and there "absent from the
APK" is the normal state of every real ID -- it says nothing about the checklist.
A run against such a build put all 44 of its ad-ID rows into "không có trong
build" with a note suspecting the checklist, while the log showed the app loading
production IDs the APK had never heard of. So the sweep now checks whether it is
in a position to answer at all before it answers.

Reading the manifest needs `aapt2` (Android SDK build-tools); ad unit IDs need
no extra tooling. When something is unavailable the affected rows are marked
explicitly unverified rather than silently passed or failed.

GUI-only (see streamlit_app.py): check_ads.py's CLI never touches a device.
"""
import os
import re
import subprocess
import zipfile

from apk_source import apk_ad_ids, apk_contains, build_apks, find_aapt2, manifest_app_id

APP_ID_RE = re.compile(r"ca-app-pub-\d+~\d+")
AD_UNIT_ID_RE = re.compile(r"ca-app-pub-\d+/\d+")

APP_ID_UNVERIFIED_NOTE = (
    "App này không in App ID ra logcat -- không verify được từ log. "
    "Cần aapt2 (Android SDK build-tools) + máy đang cắm để đọc manifest APK."
)
AD_ID_IN_APK_NOTE = (
    "Xác nhận từ APK: ID có trong build. Log chưa thấy load ID này -- "
    "chưa chứng minh placement đó đang bật hay màn đó dùng đúng ID."
)
VALUE_IN_APK_NOTE = (
    "Xác nhận từ APK: giá trị này có trong build. Log không in nó ra -- "
    "chưa chứng minh SDK đang dùng đúng giá trị đó lúc chạy."
)
VALUE_NOT_IN_APK_NOTE = (
    "Không tìm thấy giá trị này trong APK của build đang cài -- nghi checklist "
    "ghi giá trị không tồn tại trong build."
)
AD_ID_NOT_IN_APK_NOTE = (
    "Không tìm thấy ID này trong APK của build đang cài -- nghi checklist ghi ID "
    "không tồn tại trong build (không phải chỉ do chưa capture đúng màn)."
)
AD_ID_APK_CANNOT_ANSWER_NOTE = (
    "APK của build này không nhúng ID ads thật nào (chỉ có ID mẫu của SDK), nên "
    "việc không thấy ID trong APK KHÔNG nói lên điều gì -- app nạp ad unit ID "
    "lúc chạy. Dòng này phải đối chiếu bằng log, cần capture đúng màn."
)

# Publisher ids that are nobody's real inventory: Google's own sample ads, which
# ship inside the AdMob SDK, and the placeholder a project starts life with.
SAMPLE_PUBLISHERS = ("3940256099942544", "0000000000000000")


def is_sample_ad_id(value: str) -> bool:
    """An SDK sample or placeholder id rather than anyone's real placement."""
    return any(f"ca-app-pub-{pub}" in value for pub in SAMPLE_PUBLISHERS)


def scan_can_answer(in_apk: set[str]) -> bool:
    """Whether absence from this APK is evidence about an ad unit id.

    Only when the build embeds at least one real ad unit id. A build carrying
    nothing but sample ids keeps its real ones somewhere else -- remote config --
    so every real id is "absent" and absence distinguishes nothing.
    """
    return any(
        AD_UNIT_ID_RE.fullmatch(value) and not is_sample_ad_id(value) for value in in_apk
    )


def is_app_id(value: str) -> bool:
    """Shape check: AdMob *App* ID uses `~`, ad *unit* IDs use `/`."""
    return bool(APP_ID_RE.fullmatch(value))


def has_ad_id_candidate(row: dict) -> bool:
    """Whether the APK sweep could speak to this row at all.

    A placement row keeps its real ad unit ID in `alt_values`, not in `value`.
    """
    return bool(_row_ad_ids(row))


def _row_ad_ids(row: dict) -> list[str]:
    """The row's ad-unit-ID candidates: its own value plus sheet column C alts."""
    return [
        v for v in [row["value"], *row.get("alt_values", [])] if AD_UNIT_ID_RE.fullmatch(v)
    ]


def is_token_like(value: str) -> bool:
    """Opaque enough that finding it in the APK means something.

    Adjust tokens, Facebook ids and client tokens are unique strings: seeing one
    inside the build is real evidence. A plain word is not -- "production" would
    turn up in any APK ever built, and calling that a match would quietly pass a
    row nobody checked. Requiring both letters and digits, or a long run of
    digits, keeps the words out and the tokens in.
    """
    if len(value) < 6:
        return False
    has_alpha = any(c.isalpha() for c in value)
    has_digit = any(c.isdigit() for c in value)
    return (has_alpha and has_digit) or (value.isdigit() and len(value) >= 12)


def verify_apk_rows(result: dict, package: str | None, apk_fn=build_apks) -> None:
    """Second-opinion unmatched App ID / ad unit ID rows against the APK, in place.

    Rows the log already confirmed keep their log verdict -- observing an ad
    actually load is stronger evidence than finding its ID in the build.
    """
    app_id_rows = []
    ad_id_rows = []
    plain_rows = []
    for section_rows in result["sections"].values():
        for row in section_rows:
            if row["found"]:
                continue
            if is_app_id(row["value"]):
                app_id_rows.append(row)
            elif _row_ad_ids(row):
                ad_id_rows.append(row)
            elif is_token_like(row["value"]):
                # Tokens the log never prints -- an Adjust app token, a Facebook
                # client token. They sat unverifiable while being compiled right
                # into the build the whole time.
                plain_rows.append(row)
    if not (app_id_rows or ad_id_rows or plain_rows) or not package:
        return

    try:
        apk_paths, ephemeral = apk_fn(package)
    except (subprocess.SubprocessError, OSError):
        apk_paths, ephemeral = [], False
    if not apk_paths:
        for row in app_id_rows:
            row["note"] = APP_ID_UNVERIFIED_NOTE
        return

    try:
        # The manifest lives in base.apk, which build_apks puts first; the
        # string sweeps want the whole build, splits included.
        _apply_app_id_rows(app_id_rows, apk_paths[0])
        _apply_ad_id_rows(ad_id_rows, apk_paths)
        _apply_plain_rows(plain_rows, apk_paths)
    finally:
        if ephemeral:
            for path in apk_paths:
                os.unlink(path)


def _apply_app_id_rows(rows: list[dict], apk_path: str) -> None:
    if not rows:
        return
    aapt2 = find_aapt2()
    declared = None
    if aapt2:
        try:
            declared = manifest_app_id(apk_path, aapt2)
        except (subprocess.SubprocessError, OSError):
            declared = None
    for row in rows:
        if declared is None:
            row["note"] = APP_ID_UNVERIFIED_NOTE
        elif declared == row["value"]:
            row["found"] = True
            row["note"] = None
        else:
            row["note"] = f"Đã kiểm tra manifest APK -- app đang dùng: {declared}"


def _apply_ad_id_rows(rows: list[dict], apk_path) -> None:
    if not rows:
        return
    try:
        in_apk = apk_ad_ids(apk_path)
    except (zipfile.BadZipFile, OSError):
        return
    # Decided once for the build, not per row: it is a fact about the APK.
    can_answer = scan_can_answer(in_apk)
    for row in rows:
        if any(ad_id in in_apk for ad_id in _row_ad_ids(row)):
            row["found"] = True
            row["note"] = AD_ID_IN_APK_NOTE
        elif not can_answer:
            row["note"] = AD_ID_APK_CANNOT_ANSWER_NOTE
        else:
            row["note"] = AD_ID_NOT_IN_APK_NOTE


def _apply_plain_rows(rows: list[dict], apk_path) -> None:
    """Second-opinion plain-token rows against the APK, one sweep for all."""
    if not rows:
        return
    try:
        hits = apk_contains(apk_path, [row["value"] for row in rows])
    except (zipfile.BadZipFile, OSError):
        return
    for row in rows:
        if hits.get(row["value"]):
            row["found"] = True
            row["note"] = VALUE_IN_APK_NOTE
        else:
            row["note"] = VALUE_NOT_IN_APK_NOTE

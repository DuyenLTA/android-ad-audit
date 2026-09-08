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

Reading the manifest needs `aapt2` (Android SDK build-tools); ad unit IDs need
no extra tooling. When something is unavailable the affected rows are marked
explicitly unverified rather than silently passed or failed.

GUI-only (see streamlit_app.py): check_ads.py's CLI never touches a device.
"""
import os
import re
import subprocess
import zipfile

from apk_source import apk_ad_ids, base_apk, find_aapt2, manifest_app_id

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
AD_ID_NOT_IN_APK_NOTE = (
    "Không tìm thấy ID này trong APK của build đang cài -- nghi checklist ghi ID "
    "không tồn tại trong build (không phải chỉ do chưa capture đúng màn)."
)


def is_app_id(value: str) -> bool:
    """Shape check: AdMob *App* ID uses `~`, ad *unit* IDs use `/`."""
    return bool(APP_ID_RE.fullmatch(value))


def _row_ad_ids(row: dict) -> list[str]:
    """The row's ad-unit-ID candidates: its own value plus sheet column C alts."""
    return [
        v for v in [row["value"], *row.get("alt_values", [])] if AD_UNIT_ID_RE.fullmatch(v)
    ]


def verify_apk_rows(result: dict, package: str | None, apk_fn=base_apk) -> None:
    """Second-opinion unmatched App ID / ad unit ID rows against the APK, in place.

    Rows the log already confirmed keep their log verdict -- observing an ad
    actually load is stronger evidence than finding its ID in the build.
    """
    app_id_rows = []
    ad_id_rows = []
    for section_rows in result["sections"].values():
        for row in section_rows:
            if row["found"]:
                continue
            if is_app_id(row["value"]):
                app_id_rows.append(row)
            elif _row_ad_ids(row):
                ad_id_rows.append(row)
    if not (app_id_rows or ad_id_rows) or not package:
        return

    try:
        apk_path, ephemeral = apk_fn(package)
    except (subprocess.SubprocessError, OSError):
        apk_path, ephemeral = None, False
    if not apk_path:
        for row in app_id_rows:
            row["note"] = APP_ID_UNVERIFIED_NOTE
        return

    try:
        _apply_app_id_rows(app_id_rows, apk_path)
        _apply_ad_id_rows(ad_id_rows, apk_path)
    finally:
        if ephemeral:
            os.unlink(apk_path)


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


def _apply_ad_id_rows(rows: list[dict], apk_path: str) -> None:
    if not rows:
        return
    try:
        in_apk = apk_ad_ids(apk_path)
    except (zipfile.BadZipFile, OSError):
        return
    for row in rows:
        if any(ad_id in in_apk for ad_id in _row_ad_ids(row)):
            row["found"] = True
            row["note"] = AD_ID_IN_APK_NOTE
        else:
            row["note"] = AD_ID_NOT_IN_APK_NOTE

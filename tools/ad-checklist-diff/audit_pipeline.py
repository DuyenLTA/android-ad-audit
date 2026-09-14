"""One audit run, composed once and shared by the CLI and the GUI.

The GUI used to wire the steps together itself, which left the CLI unable to
verify anything the log could not show (App ID, placements the capture never
exercised). Both now call `run_audit`, so a headless run and a GUI run reach
the same verdict.

Log and APK are independent sources: with only a log it is the classic diff,
with only an APK it is a device-free check of every ID row, and with both the
log wins where it speaks (an ad seen loading is stronger evidence than an ID
merely present in the build).
"""
from apk_verifier import verify_apk_rows
from check_ads import (
    diff,
    extract_key_cooccurrences,
    extract_key_value_pairs,
    extract_label_value_pairs,
    extract_values,
    fetch_checklist,
    load_trusted_lines,
)
from apk_verifier import has_ad_id_candidate, is_app_id, is_token_like
from package_verifier import is_package_name, verify_package_rows

NO_LOG_NOTE = (
    "Lượt này không capture log nên dòng này chưa kiểm được -- "
    "không phải bằng chứng lệch."
)


def _mark_rows_no_log_can_answer(result: dict) -> None:
    """Say so when a row simply had no source to answer it this run.

    An APK-only run cannot speak to a value that only ever appears in a log --
    the Adjust environment is the plain word `production`, which is in every
    APK ever built and so cannot be swept for. Leaving the log-diff's own note
    there reads as "looked and found a mismatch", which is not what happened.
    """
    for rows in result["sections"].values():
        for row in rows:
            if row["found"] or is_package_name(row["value"]) or is_app_id(row["value"]):
                continue
            # Đã có nguồn trả lời rồi thì giữ nguyên kết luận của nguồn đó. Dòng
            # placement mang ID thật ở alt_values, không ở value -- bỏ sót chỗ này
            # là xoá mất đúng cái ghi chú "không tìm thấy ID trong APK".
            if is_token_like(row["value"]) or has_ad_id_candidate(row):
                continue
            row["note"] = NO_LOG_NOTE


def checklist_package(result: dict) -> str | None:
    """The package the checklist declares -- the APK to read on the device."""
    for rows in result["sections"].values():
        for row in rows:
            if is_package_name(row["value"]):
                return row["value"]
    return None


def run_audit(
    sheet_url: str,
    filters: list[str],
    *,
    log_path: str | None = None,
    package: str | None = None,
    apk_path: str | None = None,
    use_device: bool = True,
) -> tuple[dict, list[str]]:
    """Diff the checklist against a log and/or an APK. Returns (result, empty_filters)."""
    checklist = fetch_checklist(sheet_url)

    empty_filters: list[str] = []
    trusted_values: set[str] = set()
    label_pairs: dict = {}
    key_pairs: dict = {}
    cooccurrences: dict = {}
    if log_path:
        by_filter = load_trusted_lines(log_path, filters)
        empty_filters = [f for f, lines in by_filter.items() if not lines]
        lines = [line for group in by_filter.values() for line in group]
        trusted_values = extract_values(lines)
        label_pairs = extract_label_value_pairs(lines)
        key_pairs = extract_key_value_pairs(lines)
        cooccurrences = extract_key_cooccurrences(lines)

    result = diff(checklist, trusted_values, label_pairs, key_pairs, cooccurrences)

    if use_device:
        verify_package_rows(result)
    package = package or checklist_package(result)

    if apk_path:
        # An APK handed in directly needs no device at all -- this is what lets
        # many apps be audited in parallel, unattended.
        verify_apk_rows(result, package or "(apk)", apk_fn=lambda _pkg: (apk_path, False))
    elif use_device and package:
        verify_apk_rows(result, package)

    if not log_path:
        _mark_rows_no_log_can_answer(result)

    return result, empty_filters

import zipfile

import audit_pipeline
from audit_pipeline import checklist_package, run_audit

CHECKLIST = [
    {"section": "S", "label": "Package name", "value": "com.example.app", "alt_values": []},
    {"section": "S", "label": "Onb", "value": "ca-app-pub-111/222", "alt_values": []},
    {"section": "S", "label": "Other", "value": "ca-app-pub-111/999", "alt_values": []},
]


def _fake_apk(tmp_path):
    apk = tmp_path / "base.apk"
    with zipfile.ZipFile(apk, "w") as zf:
        zf.writestr("classes.dex", b"ca-app-pub-111/222")
    return str(apk)


def test_checklist_package_found_by_shape():
    result = {"sections": {"S": [{"value": "com.example.app"}, {"value": "ca-app-pub-1/2"}]}}
    assert checklist_package(result) == "com.example.app"


def test_apk_only_run_touches_no_device(tmp_path, monkeypatch):
    # The point of --apk: many apps can be audited in parallel with no phone.
    monkeypatch.setattr(audit_pipeline, "fetch_checklist", lambda url: CHECKLIST)
    monkeypatch.setattr(
        audit_pipeline,
        "verify_package_rows",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("không được gọi adb")),
    )
    result, empty = run_audit(
        "sheet", [], apk_path=_fake_apk(tmp_path), use_device=False
    )
    rows = {r["value"]: r for r in result["sections"]["S"]}
    assert rows["ca-app-pub-111/222"]["found"] is True
    assert rows["ca-app-pub-111/999"]["found"] is False
    assert empty == []


def test_log_only_run_reports_empty_filters(tmp_path, monkeypatch):
    monkeypatch.setattr(audit_pipeline, "fetch_checklist", lambda url: CHECKLIST)
    log = tmp_path / "capture.log"
    log.write_text("TAG_A: Ad id ca-app-pub-111/222\n", encoding="utf-8")
    result, empty = run_audit(
        "sheet", ["TAG_A", "TAG_MISSING"], log_path=str(log), use_device=False
    )
    rows = {r["value"]: r for r in result["sections"]["S"]}
    assert rows["ca-app-pub-111/222"]["found"] is True
    assert empty == ["TAG_MISSING"]


def test_a_row_the_apk_already_answered_keeps_that_answer(monkeypatch):
    # A placement row carries its real ad unit ID in alt_values, not in value.
    # Missing that is how the "no log this run" note overwrote the one finding
    # the APK sweep had actually proven.
    from audit_pipeline import NO_LOG_NOTE, _mark_rows_no_log_can_answer

    result = {"sections": {"S": [
        {"label": "Home", "value": "inter_feature_high",
         "alt_values": ["ca-app-pub-1/2"], "found": False,
         "note": "Không tìm thấy ID này trong APK của build đang cài"},
        {"label": "Adjust config environment", "value": "production",
         "alt_values": [], "found": False, "note": "không thấy ID lệch nào tương ứng trong log"},
    ]}}
    _mark_rows_no_log_can_answer(result)

    placement, environment = result["sections"]["S"]
    assert "không tìm thấy id này trong apk" in placement["note"].lower()
    assert environment["note"] == NO_LOG_NOTE


def test_a_token_row_keeps_the_apk_sweeps_verdict():
    from audit_pipeline import NO_LOG_NOTE, _mark_rows_no_log_can_answer

    result = {"sections": {"S": [
        {"label": "Adjust config token", "value": "uz6fb8kyeww0",
         "alt_values": [], "found": False, "note": "Không tìm thấy giá trị này trong APK"},
    ]}}
    _mark_rows_no_log_can_answer(result)
    assert result["sections"]["S"][0]["note"] != NO_LOG_NOTE

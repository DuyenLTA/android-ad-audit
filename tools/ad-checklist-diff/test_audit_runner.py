import json

import audit_runner
from audit_runner import audit_one, run_all

APPS = [{"package": "com.a", "gid": "1", "label": "A"}, {"package": "com.b", "gid": "2"}]
SHEET = "https://docs.google.com/spreadsheets/d/ABC/edit"

RESULT = {
    "sections": {"S": [{"label": "x", "value": "v", "found": False, "note": "n"}]},
    "leftover_ids": [],
}


def _stub(monkeypatch, *, version="33", result=RESULT):
    monkeypatch.setattr(audit_runner, "device_version_code", lambda pkg: version)
    monkeypatch.setattr(audit_runner, "base_apk", lambda pkg: (f"/tmp/{pkg}.apk", False))
    monkeypatch.setattr(audit_runner, "run_audit", lambda *a, **k: (result, []))


def test_unchanged_build_is_skipped_without_reauditing(tmp_path, monkeypatch):
    # The cheap test for "anything new?": same versionCode means the same APK,
    # so re-running the whole audit would burn time for an identical answer.
    _stub(monkeypatch)
    calls = []
    monkeypatch.setattr(
        audit_runner, "run_audit", lambda *a, **k: (calls.append(1), (RESULT, []))[1]
    )
    first = audit_one(APPS[0], SHEET, out_dir=tmp_path, snapshots_dir=tmp_path)
    second = audit_one(APPS[0], SHEET, out_dir=tmp_path, snapshots_dir=tmp_path)
    assert "skipped" in second and "skipped" not in first
    assert len(calls) == 1


def test_force_reaudits_even_on_the_same_build(tmp_path, monkeypatch):
    _stub(monkeypatch)
    audit_one(APPS[0], SHEET, out_dir=tmp_path, snapshots_dir=tmp_path)
    again = audit_one(APPS[0], SHEET, out_dir=tmp_path, force=True, snapshots_dir=tmp_path)
    assert "skipped" not in again


def test_new_build_reaudits_and_reports_the_delta(tmp_path, monkeypatch):
    _stub(monkeypatch, version="33")
    audit_one(APPS[0], SHEET, out_dir=tmp_path, snapshots_dir=tmp_path)

    fixed = {"sections": {"S": [{"label": "x", "value": "v", "found": True, "note": None}]}, "leftover_ids": []}
    _stub(monkeypatch, version="34", result=fixed)
    out = audit_one(APPS[0], SHEET, out_dir=tmp_path, snapshots_dir=tmp_path)
    assert out["score"] == "1/1"
    assert [r["value"] for r in out["delta"]["fixed"]] == ["v"]


def test_triage_file_written_for_the_agent_layer(tmp_path, monkeypatch):
    _stub(monkeypatch)
    out = audit_one(APPS[0], SHEET, out_dir=tmp_path, snapshots_dir=tmp_path)
    payload = json.loads(open(out["triage_path"], encoding="utf-8").read())
    assert "triage" in payload and "delta" in payload


def test_missing_apk_is_reported_per_app_not_fatal(tmp_path, monkeypatch):
    _stub(monkeypatch)
    monkeypatch.setattr(audit_runner, "base_apk", lambda pkg: (None, False))
    out = audit_one(APPS[0], SHEET, out_dir=tmp_path, snapshots_dir=tmp_path)
    assert "error" in out


def test_run_all_covers_every_app(tmp_path, monkeypatch):
    _stub(monkeypatch)
    monkeypatch.setattr(audit_runner, "DEFAULT_DIR", tmp_path, raising=False)
    results = run_all(APPS, SHEET, out_dir=tmp_path, force=True, workers=2)
    assert {r["package"] for r in results} == {"com.a", "com.b"}

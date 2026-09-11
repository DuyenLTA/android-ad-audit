import json

import audit_runner
from audit_runner import audit_one, capture_and_audit, run_all

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
    results = run_all(APPS, SHEET, out_dir=tmp_path, force=True, workers=2, snapshots_dir=tmp_path)
    assert {r["package"] for r in results} == {"com.a", "com.b"}


def _stub_capture(monkeypatch, *, reached=("new", "old"), missed=()):
    captured = []

    def fake_capture(package, out_path, **kwargs):
        captured.append((package, out_path, kwargs))
        open(out_path, "w", encoding="utf-8").write("log\n")
        return [
            {"pass": name, "reached_home": name not in missed}
            for name in (*reached, *missed)
        ]

    monkeypatch.setattr(audit_runner, "capture_session", fake_capture)
    return captured


def test_capture_lane_audits_against_the_log_it_just_recorded(tmp_path, monkeypatch):
    _stub(monkeypatch)
    captured = _stub_capture(monkeypatch)
    seen = {}
    monkeypatch.setattr(
        audit_runner,
        "run_audit",
        lambda *a, **k: (seen.update(k), (RESULT, []))[1],
    )
    out = capture_and_audit(APPS[0], SHEET, out_dir=tmp_path, snapshots_dir=tmp_path)
    assert len(captured) == 1
    assert out["capture_log"] == seen["log_path"] == str(tmp_path / "com.a-capture.log")


def test_unchanged_build_skips_before_touching_the_phone(tmp_path, monkeypatch):
    # A capture costs minutes of the one phone's time; deciding to skip only
    # afterwards would spend all of it for an answer already on disk.
    _stub(monkeypatch)
    captured = _stub_capture(monkeypatch)
    capture_and_audit(APPS[0], SHEET, out_dir=tmp_path, snapshots_dir=tmp_path)
    again = capture_and_audit(APPS[0], SHEET, out_dir=tmp_path, snapshots_dir=tmp_path)
    assert "skipped" in again
    assert len(captured) == 1


def test_journey_that_never_reached_home_is_flagged(tmp_path, monkeypatch):
    # Rows "chưa thấy trong log" mean nothing if the capture stopped early.
    _stub(monkeypatch)
    _stub_capture(monkeypatch, reached=("new",), missed=("old",))
    out = capture_and_audit(APPS[0], SHEET, out_dir=tmp_path, snapshots_dir=tmp_path)
    assert out["missed_home"] == ["old"]


def test_triage_carries_the_journey_that_stopped_short(tmp_path, monkeypatch):
    # Printing it to the terminal loses it: whoever reads the triage later has
    # no other way to learn the capture never got past onboarding.
    _stub(monkeypatch)
    _stub_capture(monkeypatch, reached=("new",), missed=("old",))
    out = capture_and_audit(APPS[0], SHEET, out_dir=tmp_path, snapshots_dir=tmp_path)
    payload = json.loads(open(out["triage_path"], encoding="utf-8").read())
    assert payload["missed_home"] == ["old"]
    assert payload["capture_log"].endswith("-capture.log")


def test_triage_of_a_full_journey_says_nothing_was_missed(tmp_path, monkeypatch):
    _stub(monkeypatch)
    _stub_capture(monkeypatch)
    out = capture_and_audit(APPS[0], SHEET, out_dir=tmp_path, snapshots_dir=tmp_path)
    payload = json.loads(open(out["triage_path"], encoding="utf-8").read())
    assert payload["missed_home"] == []


def test_apk_only_triage_leaves_missed_home_null_not_empty(tmp_path, monkeypatch):
    # [] would read as "every journey reached Home"; there was no journey at all.
    _stub(monkeypatch)
    out = audit_one(APPS[0], SHEET, out_dir=tmp_path, snapshots_dir=tmp_path)
    payload = json.loads(open(out["triage_path"], encoding="utf-8").read())
    assert payload["missed_home"] is None
    assert payload["capture_log"] is None


def test_triage_names_the_build_and_the_moment_it_was_audited(tmp_path, monkeypatch):
    _stub(monkeypatch, version="41")
    out = audit_one(APPS[0], SHEET, out_dir=tmp_path, snapshots_dir=tmp_path)
    payload = json.loads(open(out["triage_path"], encoding="utf-8").read())
    assert payload["package"] == APPS[0]["package"]
    assert payload["version_code"] == "41"
    assert payload["audited_at"].startswith("20")


def test_capture_lane_runs_one_app_at_a_time(tmp_path, monkeypatch):
    # One phone: two captures overlapping would interleave two apps' logs.
    _stub(monkeypatch)
    live = []
    overlapped = []

    def fake_capture(package, out_path, **kwargs):
        overlapped.append(list(live))
        live.append(package)
        open(out_path, "w", encoding="utf-8").write("log\n")
        live.remove(package)
        return [{"pass": "new", "reached_home": True}]

    monkeypatch.setattr(audit_runner, "capture_session", fake_capture)
    run_all(APPS, SHEET, out_dir=tmp_path, force=True, capture=True, snapshots_dir=tmp_path)
    assert overlapped == [[], []]


def test_run_all_writes_snapshots_where_told(tmp_path, monkeypatch):
    # Without this the default snapshot directory is the live one, so a test run
    # would overwrite real baselines.
    _stub(monkeypatch)
    run_all(APPS, SHEET, out_dir=tmp_path, force=True, snapshots_dir=tmp_path)
    assert {p.name for p in tmp_path.glob("com.*.json")} >= {"com.a.json", "com.b.json"}

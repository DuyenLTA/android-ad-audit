import json

import audit_runner
from audit_runner import (
    audit_one,
    capture_and_audit,
    print_summary,
    run_all,
    unsettled_rows,
)

APPS = [{"package": "com.a", "gid": "1", "label": "A"}, {"package": "com.b", "gid": "2"}]
SHEET = "https://docs.google.com/spreadsheets/d/ABC/edit"

# What the sheet says, as parsed. Stubbed because the skip decision reads it
# before deciding whether to audit at all.
CHECKLIST = [{"section": "S", "label": "x", "value": "v", "alt_values": []}]

RESULT = {
    "sections": {"S": [{"label": "x", "value": "v", "found": False, "note": "n"}]},
    "leftover_ids": [],
}


def _stub(monkeypatch, *, version="33", result=RESULT, checklist=CHECKLIST):
    monkeypatch.setattr(audit_runner, "fetch_checklist", lambda url: checklist)
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


def test_unsettled_rows_tells_no_triage_apart_from_an_empty_one(tmp_path):
    # None means "never audited"; 0 means "audited, nothing left to judge".
    assert unsettled_rows(tmp_path / "nope.json") is None
    empty = tmp_path / "empty.json"
    empty.write_text('{"triage": {"a": [], "b": []}}', encoding="utf-8")
    assert unsettled_rows(empty) == 0
    some = tmp_path / "some.json"
    some.write_text('{"triage": {"a": [1, 2], "b": [3]}}', encoding="utf-8")
    assert unsettled_rows(some) == 3


def test_audit_reports_how_many_rows_are_left_for_the_agents(tmp_path, monkeypatch):
    _stub(monkeypatch)
    out = audit_one(APPS[0], SHEET, out_dir=tmp_path, snapshots_dir=tmp_path)
    payload = json.loads(open(out["triage_path"], encoding="utf-8").read())
    assert out["unsettled"] == sum(len(rows) for rows in payload["triage"].values())


def test_skipped_app_still_reports_the_standing_triage(tmp_path, monkeypatch):
    # A skip leaves the previous triage in place, so its rows are still work.
    _stub(monkeypatch)
    audit_one(APPS[0], SHEET, out_dir=tmp_path, snapshots_dir=tmp_path)
    again = audit_one(APPS[0], SHEET, out_dir=tmp_path, snapshots_dir=tmp_path)
    assert again["skipped"]
    assert again["unsettled"] is not None


def test_summary_prints_the_count_the_agent_layer_reads(capsys):
    print_summary([
        {"package": "com.a", "label": "A", "score": "9/9", "unsettled": 0,
         "delta": {"broke": [], "fixed": [], "new_leftover_ids": []}},
        {"package": "com.b", "label": "B", "skipped": "build chưa đổi",
         "version_code": "7", "unsettled": 2},
    ])
    printed = capsys.readouterr().out
    assert "chưa kết luận: 0" in printed
    assert "chưa kết luận: 2" in printed



# --- A dev build stops the run instead of scoring it ------------------------
# A checklist lists production values, so against a dev build nearly every row
# misses and every miss reads as the sheet being wrong. Everything after the
# diff is time spent producing that misreading.

SAMPLE_ID = "ca-app-pub-3940256099942544/2247696110"


def _audit_stubs(monkeypatch, result, saved, tmp_path):
    monkeypatch.setattr(audit_runner, "fetch_checklist", lambda url: CHECKLIST)
    monkeypatch.setattr(audit_runner, "device_version_code", lambda pkg: 12)
    monkeypatch.setattr(audit_runner, "load", lambda pkg, **kw: None)
    monkeypatch.setattr(audit_runner, "base_apk", lambda pkg: (str(tmp_path / "x.apk"), False))
    monkeypatch.setattr(audit_runner, "run_audit", lambda *a, **kw: (result, []))
    monkeypatch.setattr(audit_runner, "apk_ad_ids", lambda path: set())
    monkeypatch.setattr(
        audit_runner, "save", lambda *a, **kw: saved.append(a) or {}
    )


def _app():
    return {"package": "com.x", "gid": "1", "label": "X"}


def test_a_dev_build_stops_before_anything_is_written(monkeypatch, tmp_path):
    saved = []
    result = {"extra": [SAMPLE_ID, "sandbox"], "sections": {}}
    _audit_stubs(monkeypatch, result, saved, tmp_path)

    summary = audit_runner.audit_one(_app(), "http://sheet", out_dir=tmp_path)

    assert summary["wrong_build"]
    assert "score" not in summary
    # The snapshot is the baseline the next run's delta is measured against, and
    # a dev build is not a baseline for anything: saving it would make the
    # following release run report dozens of "fixed" rows that were never broken.
    assert saved == []
    assert not list(tmp_path.glob("*-triage.json"))


def test_allow_dev_build_runs_it_anyway(monkeypatch, tmp_path):
    saved = []
    result = {"extra": [SAMPLE_ID], "sections": {}}
    _audit_stubs(monkeypatch, result, saved, tmp_path)

    summary = audit_runner.audit_one(
        _app(), "http://sheet", out_dir=tmp_path, allow_dev_build=True
    )

    assert "wrong_build" not in summary
    assert saved


def test_a_release_build_is_untouched_by_the_check(monkeypatch, tmp_path):
    saved = []
    result = {"extra": ["ca-app-pub-4973559944609228/2720278708"], "sections": {}}
    _audit_stubs(monkeypatch, result, saved, tmp_path)

    summary = audit_runner.audit_one(_app(), "http://sheet", out_dir=tmp_path)

    assert "wrong_build" not in summary
    assert saved


def test_wrong_build_gets_its_own_exit_code():
    # 1 means the runner broke and 2 means rows are mismatched -- both say the
    # report is wrong. This one says there is no report.
    assert audit_runner.exit_code_for([{"wrong_build": ["x"]}]) == 3
    assert audit_runner.exit_code_for([{"error": "boom"}]) == 1
    assert audit_runner.exit_code_for([{"delta": {"broke": ["r"]}}]) == 2
    assert audit_runner.exit_code_for([{"delta": {"broke": []}}]) == 0


# --- Both halves of the comparison decide whether a re-run is needed ---------

EDITED = [{"section": "S", "label": "x", "value": "v2", "alt_values": []}]


def test_an_edited_checklist_reaudits_a_build_that_did_not_change(tmp_path, monkeypatch):
    # The build is only half the comparison. The ads team edits the sheet without
    # anybody reinstalling the app, and skipping on versionCode alone answers a
    # question nobody asked -- serving the old verdict against a new checklist.
    _stub(monkeypatch)
    audit_one(APPS[0], SHEET, out_dir=tmp_path, snapshots_dir=tmp_path)

    _stub(monkeypatch, checklist=EDITED)
    again = audit_one(APPS[0], SHEET, out_dir=tmp_path, snapshots_dir=tmp_path)
    assert "skipped" not in again


def test_same_build_and_same_checklist_is_the_only_skip(tmp_path, monkeypatch):
    _stub(monkeypatch)
    audit_one(APPS[0], SHEET, out_dir=tmp_path, snapshots_dir=tmp_path)
    again = audit_one(APPS[0], SHEET, out_dir=tmp_path, snapshots_dir=tmp_path)
    assert again["skipped"] == "build và checklist đều chưa đổi"


def test_a_snapshot_from_before_digests_is_audited_once_more(tmp_path, monkeypatch):
    # No digest means unknown, not unchanged: a run that read it as unchanged
    # would skip on a guess, and every old snapshot would skip forever.
    _stub(monkeypatch)
    audit_one(APPS[0], SHEET, out_dir=tmp_path, snapshots_dir=tmp_path)
    snap = tmp_path / "com.a.json"
    payload = json.loads(snap.read_text(encoding="utf-8"))
    del payload["checklist_digest"]
    snap.write_text(json.dumps(payload), encoding="utf-8")

    assert "skipped" not in audit_one(APPS[0], SHEET, out_dir=tmp_path, snapshots_dir=tmp_path)


def test_an_edited_checklist_rediffs_the_stored_capture_instead_of_driving(tmp_path, monkeypatch):
    # Nothing the sheet says can change what the app already did, so re-driving
    # the phone for minutes would produce a log with a known answer.
    _stub(monkeypatch)
    captured = _stub_capture(monkeypatch)
    capture_and_audit(APPS[0], SHEET, out_dir=tmp_path, snapshots_dir=tmp_path)
    assert len(captured) == 1

    _stub(monkeypatch, checklist=EDITED)
    again = capture_and_audit(APPS[0], SHEET, out_dir=tmp_path, snapshots_dir=tmp_path)
    assert again["reused_log"] is True
    assert again["capture_log"] == str(tmp_path / "com.a-capture.log")
    assert len(captured) == 1  # the phone was never touched


def test_a_reused_capture_keeps_the_coverage_it_actually_had(tmp_path, monkeypatch):
    # Which journeys reached Home is a property of the capture, not of the run
    # re-reading it. Dropping it would have the page claim no capture stands
    # behind these rows, and re-flag rows that were already explained.
    _stub(monkeypatch)
    _stub_capture(monkeypatch, reached=("new",), missed=("old",))
    capture_and_audit(APPS[0], SHEET, out_dir=tmp_path, snapshots_dir=tmp_path)

    _stub(monkeypatch, checklist=EDITED)
    capture_and_audit(APPS[0], SHEET, out_dir=tmp_path, snapshots_dir=tmp_path)
    triage = json.loads((tmp_path / "com.a-triage.json").read_text(encoding="utf-8"))
    assert triage["missed_home"] == ["old"]
    assert triage["capture_reused_from"]


def test_a_new_build_still_drives_the_phone(tmp_path, monkeypatch):
    # The reuse path must not swallow the case it looks most like.
    _stub(monkeypatch)
    first = _stub_capture(monkeypatch)
    capture_and_audit(APPS[0], SHEET, out_dir=tmp_path, snapshots_dir=tmp_path)

    _stub(monkeypatch, version="34", checklist=EDITED)
    second = _stub_capture(monkeypatch)
    capture_and_audit(APPS[0], SHEET, out_dir=tmp_path, snapshots_dir=tmp_path)
    assert len(first) == 1 and len(second) == 1


def test_an_apk_only_run_calls_the_variant_unknown_not_clean(tmp_path, monkeypatch):
    # Every dev-build signal lives in what the app printed at runtime, so a run
    # with no log has nothing to read. Recording [] would read as "checked, this
    # is a release build" -- the one claim such a run cannot make.
    _stub(monkeypatch)
    out = audit_one(APPS[0], SHEET, out_dir=tmp_path, snapshots_dir=tmp_path)
    triage = json.loads(open(out["triage_path"], encoding="utf-8").read())
    assert triage["dev_build_signals"] is None

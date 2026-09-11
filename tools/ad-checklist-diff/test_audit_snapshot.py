from audit_snapshot import NOT_IN_BUILD, NO_LOG_EVIDENCE, diff_results, load, save, triage


def _result(rows):
    return {"sections": {"S": rows}, "leftover_ids": []}


def test_save_then_load_round_trips(tmp_path):
    save("com.a", _result([{"label": "x", "value": "v", "found": True, "note": None}]), "33", tmp_path)
    loaded = load("com.a", tmp_path)
    assert loaded["version_code"] == "33"
    assert loaded["result"]["sections"]["S"][0]["value"] == "v"


def test_load_missing_snapshot_returns_none(tmp_path):
    assert load("com.nope", tmp_path) is None


def test_first_run_reports_every_failing_row_as_newly_broken():
    new = _result([{"label": "x", "value": "v", "found": False, "note": "n"}])
    delta = diff_results(None, new)
    assert [b["value"] for b in delta["broke"]] == ["v"]
    assert delta["changed"] is True


def test_unchanged_rerun_reports_nothing():
    rows = [{"label": "x", "value": "v", "found": False, "note": "n"}]
    old = {"result": _result(rows)}
    delta = diff_results(old, _result(rows))
    assert delta["changed"] is False
    assert delta["broke"] == []


def test_regression_and_fix_are_reported_separately():
    old = {"result": _result([
        {"label": "a", "value": "v1", "found": True, "note": None},
        {"label": "b", "value": "v2", "found": False, "note": None},
    ])}
    new = _result([
        {"label": "a", "value": "v1", "found": False, "note": "hỏng"},
        {"label": "b", "value": "v2", "found": True, "note": None},
    ])
    delta = diff_results(old, new)
    assert [r["value"] for r in delta["broke"]] == ["v1"]
    assert [r["value"] for r in delta["fixed"]] == ["v2"]


def test_new_leftover_ids_are_surfaced():
    old = {"result": {"sections": {}, "leftover_ids": ["ca-app-pub-1/1"]}}
    new = {"sections": {}, "leftover_ids": ["ca-app-pub-1/1", "ca-app-pub-1/2"]}
    assert diff_results(old, new)["new_leftover_ids"] == ["ca-app-pub-1/2"]


def test_checklist_edits_show_as_rows_added_and_removed():
    old = {"result": _result([{"label": "old", "value": "gone", "found": True, "note": None}])}
    new = _result([{"label": "new", "value": "fresh", "found": True, "note": None}])
    delta = diff_results(old, new)
    assert [r["value"] for r in delta["rows_added"]] == ["fresh"]
    assert [r["value"] for r in delta["rows_removed"]] == ["gone"]


def test_triage_splits_build_problems_from_capture_gaps():
    result = _result([
        {"label": "a", "value": "v1", "found": False,
         "note": "Không tìm thấy ID này trong APK của build đang cài -- nghi checklist ..."},
        {"label": "b", "value": "v2", "found": False,
         "note": "ID checklist: v2 (lệch) -- không thấy ID lệch nào tương ứng trong log"},
        {"label": "c", "value": "v3", "found": True, "note": None},
    ])
    buckets = triage(result)
    assert [r["value"] for r in buckets[NOT_IN_BUILD]] == ["v1"]
    assert [r["value"] for r in buckets[NO_LOG_EVIDENCE]] == ["v2"]

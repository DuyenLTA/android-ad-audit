import json

import pytest

from app_registry import load_apps, sheet_url_for


def test_sheet_url_points_at_the_apps_tab():
    base = "https://docs.google.com/spreadsheets/d/ABC/edit?gid=1#gid=1"
    assert sheet_url_for(base, "53703266").endswith("?gid=53703266#gid=53703266")


def test_load_apps_reads_entries(tmp_path):
    f = tmp_path / "apps.json"
    f.write_text(json.dumps([{"package": "com.a", "gid": "1"}]), encoding="utf-8")
    assert load_apps(f)[0]["package"] == "com.a"


def test_missing_registry_says_so(tmp_path):
    with pytest.raises(SystemExit):
        load_apps(tmp_path / "nope.json")


def test_entry_missing_required_field_is_rejected(tmp_path):
    f = tmp_path / "apps.json"
    f.write_text(json.dumps([{"package": "com.a"}]), encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        load_apps(f)
    assert "gid" in str(e.value)


def test_malformed_json_is_rejected(tmp_path):
    f = tmp_path / "apps.json"
    f.write_text("{not json", encoding="utf-8")
    with pytest.raises(SystemExit):
        load_apps(f)

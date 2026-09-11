import json

import pytest

from app_registry import load_apps, registry_sheet, sheet_url_for


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


def test_registry_can_carry_the_sheet_it_points_into(tmp_path):
    # The gids alone say which tab but not which spreadsheet, so the URL had to
    # be retyped every run and kept in step by hand wherever the audit ran.
    reg = tmp_path / "apps.json"
    reg.write_text(
        json.dumps({"sheet": "https://x/edit", "apps": [{"package": "com.a", "gid": "1"}]}),
        encoding="utf-8",
    )
    assert registry_sheet(reg) == "https://x/edit"
    assert [a["package"] for a in load_apps(reg)] == ["com.a"]


def test_plain_list_registry_still_works_and_declares_no_sheet(tmp_path):
    reg = tmp_path / "apps.json"
    reg.write_text(json.dumps([{"package": "com.a", "gid": "1"}]), encoding="utf-8")
    assert registry_sheet(reg) is None
    assert [a["package"] for a in load_apps(reg)] == ["com.a"]


def test_object_registry_without_apps_is_rejected(tmp_path):
    reg = tmp_path / "apps.json"
    reg.write_text(json.dumps({"sheet": "https://x/edit"}), encoding="utf-8")
    with pytest.raises(SystemExit):
        load_apps(reg)


def test_missing_field_is_still_caught_inside_the_object_shape(tmp_path):
    reg = tmp_path / "apps.json"
    reg.write_text(json.dumps({"sheet": "https://x", "apps": [{"package": "com.a"}]}), encoding="utf-8")
    with pytest.raises(SystemExit):
        load_apps(reg)

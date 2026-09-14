import json

import pytest

from app_registry import load_apps, registry_sheet, resolve_packages, sheet_url_for


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


APPS = [{"package": "com.a", "gid": "1"}, {"package": "com.b", "gid": "2"}]
SHEET = "https://docs.google.com/spreadsheets/d/ABC/edit"


def _sheet_says(mapping, monkeypatch):
    """Stand in for the sheet's own package -> gids map."""
    import sheet_tabs

    monkeypatch.setattr(sheet_tabs, "gids_by_package", lambda url, refresh=False: mapping)


def test_registry_answers_without_asking_the_sheet(monkeypatch):
    # A capture pm-clears every app it visits, so auditing one app must not walk
    # the rest of the registry and wipe apps nobody asked about.
    def boom(*a, **k):
        raise AssertionError("không được hỏi sheet khi registry đã biết")

    import sheet_tabs

    monkeypatch.setattr(sheet_tabs, "gids_by_package", boom)
    assert resolve_packages(["com.b"], APPS, SHEET) == [APPS[1]]


def test_package_outside_the_registry_is_resolved_from_the_sheet(monkeypatch):
    # apps.json is a cache, not a guest list: every tab declares its own package.
    _sheet_says({"com.new.app": ["77"]}, monkeypatch)
    assert resolve_packages(["com.new.app"], APPS, SHEET) == [
        {"package": "com.new.app", "gid": "77"}
    ]


def test_two_tabs_for_one_package_is_refused(monkeypatch):
    # Picking one silently would diff the build against the wrong checklist.
    _sheet_says({"com.new.app": ["77", "88"]}, monkeypatch)
    with pytest.raises(SystemExit) as err:
        resolve_packages(["com.new.app"], APPS, SHEET)
    assert "77" in str(err.value) and "88" in str(err.value)


def test_package_no_tab_declares_is_refused(monkeypatch):
    # Nothing to compare the build against -- not the same as a clean app.
    _sheet_says({}, monkeypatch)
    with pytest.raises(SystemExit) as err:
        resolve_packages(["com.new.app"], APPS, SHEET)
    assert "com.new.app" in str(err.value)


def test_an_app_name_is_rejected_before_the_sheet_is_asked(monkeypatch):
    # "Nexus" is not a package; blaming the sheet would send the reader looking
    # for a tab that was never going to exist.
    def boom(*a, **k):
        raise AssertionError("không được hỏi sheet cho chuỗi không phải package")

    import sheet_tabs

    monkeypatch.setattr(sheet_tabs, "gids_by_package", boom)
    with pytest.raises(SystemExit) as err:
        resolve_packages(["Nexus"], APPS, SHEET)
    assert "Nexus" in str(err.value)

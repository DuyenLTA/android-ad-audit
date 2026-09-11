import sheet_tabs
from sheet_tabs import gids_by_package, sheet_id, tab_gids, tab_package

SHEET = "https://docs.google.com/spreadsheets/d/ABC123/edit"


def _resp(text):
    return type("R", (), {"text": text})()


def test_sheet_id_is_pulled_out_of_the_share_url():
    assert sheet_id(SHEET) == "ABC123"


def test_every_tab_is_listed_once_in_sheet_order():
    html = 'a gid=0 b gid=53703266 c gid=0 d gid=99'
    assert tab_gids(SHEET, get=lambda url, timeout=None: _resp(html)) == ["0", "53703266", "99"]


def test_a_tab_is_identified_by_the_package_it_declares():
    # Tab names are project codes, so the only honest link is the row the tab
    # itself carries.
    csv = "Section,\nPackage name,com.example.app\nApp ID,ca-app-pub-1~2\n"
    assert tab_package(SHEET, "0", get=lambda url, timeout=None: _resp(csv)) == "com.example.app"


def test_a_tab_naming_no_package_maps_to_nothing():
    csv = "Section,\nAdjust token,abc123\n"
    assert tab_package(SHEET, "0", get=lambda url, timeout=None: _resp(csv)) is None


def test_two_tabs_for_one_app_are_both_kept(tmp_path, monkeypatch):
    # Picking one silently is how a run diffs against the wrong checklist.
    monkeypatch.setattr(sheet_tabs, "TAB_CACHE", str(tmp_path / "tabs.json"))
    monkeypatch.setattr(sheet_tabs, "CACHE_DIR", str(tmp_path))
    mapping = gids_by_package(
        SHEET,
        gids_fn=lambda url: ["7", "8"],
        package_fn=lambda url, gid: "com.example.app",
    )
    assert mapping == {"com.example.app": ["7", "8"]}


def test_the_tab_map_is_cached_between_runs(tmp_path, monkeypatch):
    monkeypatch.setattr(sheet_tabs, "TAB_CACHE", str(tmp_path / "tabs.json"))
    monkeypatch.setattr(sheet_tabs, "CACHE_DIR", str(tmp_path))
    calls = []

    def gids(url):
        calls.append(url)
        return ["0"]

    for _ in range(2):
        gids_by_package(SHEET, gids_fn=gids, package_fn=lambda url, gid: "com.a")
    assert len(calls) == 1

    gids_by_package(SHEET, refresh=True, gids_fn=gids, package_fn=lambda url, gid: "com.a")
    assert len(calls) == 2

from app_label import apk_app_label, match_apps, names_for

APPS = [
    {"label": "AI Art", "package": "ai.photogenerator.aiart", "gid": "0"},
    {"label": "AI Beauty", "package": "com.aiphotoeditor.aibeauty", "gid": "1"},
]
SCREEN = {
    "ai.photogenerator.aiart": "Nexus AI - AI Video Generator",
    "com.aiphotoeditor.aibeauty": "Lynix: AI Photo & Video Maker",
}


def _screen(package):
    return SCREEN.get(package)


def test_the_name_on_the_phone_finds_the_app():
    # "AI Art" is the internal nickname; nobody sees it on the device.
    found = match_apps("Nexus", APPS, screen_name_fn=_screen)
    assert [a["package"] for a in found] == ["ai.photogenerator.aiart"]


def test_the_registry_nickname_still_works():
    found = match_apps("ai art", APPS, screen_name_fn=_screen)
    assert [a["package"] for a in found] == ["ai.photogenerator.aiart"]


def test_the_package_still_works():
    found = match_apps("com.aiphotoeditor.aibeauty", APPS, screen_name_fn=_screen)
    assert [a["package"] for a in found] == ["com.aiphotoeditor.aibeauty"]


def test_an_alias_declared_in_the_registry_works():
    apps = [{**APPS[0], "aliases": ["Video Gen"]}]
    assert match_apps("video gen", apps, screen_name_fn=_screen)


def test_a_name_several_apps_answer_to_returns_them_all():
    # The caller shows these and lets a person pick; guessing one is how the
    # wrong app gets its data wiped.
    found = match_apps("AI", APPS, screen_name_fn=_screen)
    assert len(found) == 2


def test_an_exact_name_beats_a_longer_one_containing_it():
    apps = [
        {"label": "AI Art", "package": "com.a", "gid": "0"},
        {"label": "AI Art Pro", "package": "com.b", "gid": "1"},
    ]
    found = match_apps("AI Art", apps, screen_name_fn=lambda p: None)
    assert [a["package"] for a in found] == ["com.a"]


def test_an_unknown_name_matches_nothing():
    assert match_apps("Artspire", APPS, screen_name_fn=_screen) == []
    assert match_apps("   ", APPS, screen_name_fn=_screen) == []


def test_names_skip_what_the_app_does_not_have():
    app = {"package": "com.a"}
    assert names_for(app, screen_name_fn=lambda p: None) == ["com.a"]


def test_label_is_read_out_of_the_badging_dump(monkeypatch, tmp_path):
    import app_label

    dump = "package: name='com.a'\napplication-label:'Nexus AI - AI Video Generator'\n"
    monkeypatch.setattr(
        app_label.subprocess, "run",
        lambda *a, **k: type("R", (), {"stdout": dump})(),
    )
    assert apk_app_label(str(tmp_path / "a.apk"), aapt2="/aapt2") == "Nexus AI - AI Video Generator"


def test_missing_aapt2_is_not_a_crash(monkeypatch, tmp_path):
    import app_label

    monkeypatch.setattr(app_label, "find_aapt2", lambda: None)
    assert apk_app_label(str(tmp_path / "a.apk")) is None

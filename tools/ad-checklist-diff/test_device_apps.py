import json

import device_apps
from device_apps import installed_packages, labels


def test_installed_packages_reads_the_third_party_list(monkeypatch):
    out = "package:com.b\npackage:com.a\n\n"
    monkeypatch.setattr(
        device_apps.subprocess, "run",
        lambda *a, **k: type("R", (), {"stdout": out})(),
    )
    assert installed_packages() == ["com.a", "com.b"]


def test_a_dead_adb_is_not_a_crash(monkeypatch):
    def boom(*a, **k):
        raise OSError("no device")

    monkeypatch.setattr(device_apps.subprocess, "run", boom)
    assert installed_packages() == []


def _cache_at(tmp_path, monkeypatch, payload=None):
    path = tmp_path / "app-labels.json"
    if payload is not None:
        path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(device_apps, "LABEL_CACHE", str(path))
    monkeypatch.setattr(device_apps, "CACHE_DIR", str(tmp_path))
    return path


def test_labels_are_read_once_and_cached(tmp_path, monkeypatch):
    _cache_at(tmp_path, monkeypatch)
    reads = []

    def fake_read(package, serial=None):
        reads.append(package)
        return f"App {package}"

    found = labels(["com.a"], read_label_fn=fake_read, version_fn=lambda p: "7")
    assert found == {"com.a": "App com.a"}

    again = labels(["com.a"], read_label_fn=fake_read, version_fn=lambda p: "7")
    assert again == {"com.a": "App com.a"}
    assert reads == ["com.a"]  # lần hai đọc từ cache


def test_a_new_build_invalidates_the_cached_label(tmp_path, monkeypatch):
    # An update can rename the app; a label pinned to the old build would lie.
    _cache_at(tmp_path, monkeypatch, {"com.a": {"version_code": "7", "label": "Cũ"}})
    found = labels(["com.a"], read_label_fn=lambda p, s=None: "Mới", version_fn=lambda p: "8")
    assert found == {"com.a": "Mới"}


def test_an_app_whose_label_cannot_be_read_is_skipped_not_faked(tmp_path, monkeypatch):
    _cache_at(tmp_path, monkeypatch)
    found = labels(["com.a"], read_label_fn=lambda p, s=None: None, version_fn=lambda p: "7")
    assert found == {}

import os
import zipfile

import apk_source


def _stub_device(monkeypatch, version_code, apk_bytes=b"PK-not-a-zip", pulls=None):
    """Stand in for the connected device: fixed versionCode + a fake `adb pull`."""
    monkeypatch.setattr(apk_source, "device_version_code", lambda pkg: version_code)
    monkeypatch.setattr(apk_source, "device_apk_path", lambda pkg: "/data/app/x/base.apk")

    def fake_run(cmd, **kwargs):
        if pulls is not None:
            pulls.append(cmd)
        with open(cmd[-1], "wb") as f:
            f.write(apk_bytes)

        class R:
            returncode = 0

        return R()

    monkeypatch.setattr(apk_source.subprocess, "run", fake_run)


def _zip_bytes(tmp_path):
    src = tmp_path / "src.apk"
    with zipfile.ZipFile(src, "w") as zf:
        zf.writestr("classes.dex", b"ca-app-pub-111/222")
    return src.read_bytes()


def test_second_call_reuses_cached_apk_and_skips_the_pull(tmp_path, monkeypatch):
    monkeypatch.setattr(apk_source, "CACHE_DIR", str(tmp_path / "cache"))
    pulls = []
    _stub_device(monkeypatch, "4565408", _zip_bytes(tmp_path), pulls)

    first, ephemeral_first = apk_source.base_apk("com.example.app")
    second, ephemeral_second = apk_source.base_apk("com.example.app")

    assert first == second
    assert (ephemeral_first, ephemeral_second) == (False, False)
    assert len(pulls) == 1  # the second call never went to the device


def test_new_version_code_pulls_again_and_prunes_the_old_build(tmp_path, monkeypatch):
    monkeypatch.setattr(apk_source, "CACHE_DIR", str(tmp_path / "cache"))
    apk_bytes = _zip_bytes(tmp_path)
    _stub_device(monkeypatch, "1", apk_bytes)
    old, _ = apk_source.base_apk("com.example.app")

    _stub_device(monkeypatch, "2", apk_bytes)
    new, _ = apk_source.base_apk("com.example.app")

    assert new != old
    assert os.path.exists(new)
    assert not os.path.exists(old)


def test_unreadable_version_code_falls_back_to_an_ephemeral_copy(tmp_path, monkeypatch):
    monkeypatch.setattr(apk_source, "CACHE_DIR", str(tmp_path / "cache"))
    _stub_device(monkeypatch, None, _zip_bytes(tmp_path))

    path, ephemeral = apk_source.base_apk("com.example.app")

    assert ephemeral is True
    assert not path.startswith(str(tmp_path / "cache"))
    os.unlink(path)


def test_truncated_cache_entry_is_not_trusted(tmp_path, monkeypatch):
    # A non-zip file sitting at the cache path (a pull killed mid-flight in an
    # older build of this tool) must trigger a fresh pull, not a parse failure.
    cache = tmp_path / "cache"
    cache.mkdir()
    monkeypatch.setattr(apk_source, "CACHE_DIR", str(cache))
    (cache / "com.example.app-9.apk").write_bytes(b"truncated")
    pulls = []
    _stub_device(monkeypatch, "9", _zip_bytes(tmp_path), pulls)

    path, _ = apk_source.base_apk("com.example.app")

    assert len(pulls) == 1
    assert zipfile.is_zipfile(path)


def test_version_code_parsed_from_dumpsys_output():
    dumpsys = "    versionName=1.2.3\n    versionCode=4565408 minSdk=17 targetSdk=34\n"
    assert apk_source.VERSION_CODE_RE.search(dumpsys).group(1) == "4565408"


def test_cacheable_pull_lands_on_the_cache_filesystem(tmp_path, monkeypatch):
    # Regression: the APK was pulled into the system temp dir and then
    # os.replace'd into ~/.cache -- which fails with EXDEV whenever those are
    # different filesystems (tmpfs vs the home partition), so nothing ever
    # got cached.
    cache = tmp_path / "cache"
    monkeypatch.setattr(apk_source, "CACHE_DIR", str(cache))
    seen = []
    monkeypatch.setattr(apk_source, "device_version_code", lambda pkg: "7")
    monkeypatch.setattr(apk_source, "device_apk_path", lambda pkg: "/data/app/x/base.apk")
    apk_bytes = _zip_bytes(tmp_path)

    def fake_run(cmd, **kwargs):
        seen.append(cmd[-1])
        with open(cmd[-1], "wb") as f:
            f.write(apk_bytes)

        class R:
            returncode = 0

        return R()

    monkeypatch.setattr(apk_source.subprocess, "run", fake_run)
    path, _ = apk_source.base_apk("com.example.app")

    assert seen and os.path.dirname(seen[0]) == str(cache)
    assert path == str(cache / "com.example.app-7.apk")

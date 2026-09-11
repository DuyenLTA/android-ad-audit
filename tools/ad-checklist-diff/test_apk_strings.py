import io
import zipfile

from apk_source import apk_contains


def _apk(tmp_path, entries):
    path = tmp_path / "t.apk"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, blob in entries.items():
            zf.writestr(name, blob)
    path.write_bytes(buf.getvalue())
    return str(path)


def test_a_string_is_found_with_the_entry_holding_it(tmp_path):
    apk = _apk(tmp_path, {"classes.dex": b"xx show_inter_feature yy"})
    assert apk_contains(apk, ["show_inter_feature"]) == {"show_inter_feature": ["classes.dex"]}


def test_an_absent_string_comes_back_empty_not_missing(tmp_path):
    apk = _apk(tmp_path, {"classes.dex": b"nothing here"})
    assert apk_contains(apk, ["4070123043"]) == {"4070123043": []}


def test_utf16_strings_count_too(tmp_path):
    # dex stores plenty of strings UTF-16LE; a UTF-8-only sweep calls a
    # placement missing from a build that ships it.
    apk = _apk(tmp_path, {"classes.dex": "show_inter_feature".encode("utf-16-le")})
    assert apk_contains(apk, ["show_inter_feature"])["show_inter_feature"] == ["classes.dex"]


def test_every_entry_is_swept_not_just_dex_and_resources(tmp_path):
    apk = _apk(tmp_path, {"assets/config.bin": b"ca-app-pub-1/2"})
    assert apk_contains(apk, ["ca-app-pub-1/2"])["ca-app-pub-1/2"] == ["assets/config.bin"]


def test_one_pass_answers_every_needle(tmp_path):
    apk = _apk(tmp_path, {"a.dex": b"alpha", "b.dex": b"beta"})
    hits = apk_contains(apk, ["alpha", "beta", "gamma"])
    assert hits["alpha"] == ["a.dex"]
    assert hits["beta"] == ["b.dex"]
    assert hits["gamma"] == []

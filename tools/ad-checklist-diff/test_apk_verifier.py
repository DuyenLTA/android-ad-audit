import os
import zipfile

from apk_source import apk_ad_ids, app_id_from_xmltree
from apk_verifier import (
    AD_ID_IN_APK_NOTE,
    AD_ID_NOT_IN_APK_NOTE,
    APP_ID_UNVERIFIED_NOTE,
    is_app_id,
    verify_apk_rows,
)

AAPT2_DUMP = """N: android=http://schemas.android.com/apk/res/android
  E: manifest (line=2)
        E: meta-data (line=165)
            A: http://schemas.android.com/apk/res/android:name(0x01010003)="com.google.android.gms.ads.APPLICATION_ID" (Raw: "com.google.android.gms.ads.APPLICATION_ID")
            A: http://schemas.android.com/apk/res/android:value(0x01010024)="ca-app-pub-111~222" (Raw: "ca-app-pub-111~222")
        E: meta-data (line=169)
            A: http://schemas.android.com/apk/res/android:name(0x01010003)="com.facebook.sdk.ApplicationId"
            A: http://schemas.android.com/apk/res/android:value(0x01010024)="fb1406453134191470"
"""


def test_is_app_id_distinguishes_app_id_from_ad_unit_id():
    assert is_app_id("ca-app-pub-111~222")
    assert not is_app_id("ca-app-pub-111/222")
    assert not is_app_id("com.example.app")


def test_app_id_from_xmltree_picks_the_admob_entry_not_a_neighbour():
    assert app_id_from_xmltree(AAPT2_DUMP) == "ca-app-pub-111~222"


def test_app_id_from_xmltree_returns_none_when_absent():
    assert app_id_from_xmltree("E: manifest (line=2)\n") is None


def _fake_apk(tmp_path, dex_body: bytes, extra_name="assets/skipped.png"):
    apk = tmp_path / "base.apk"
    with zipfile.ZipFile(apk, "w") as zf:
        zf.writestr("classes.dex", dex_body)
        # Media entries are skipped by design; an ID hidden in one must not count.
        zf.writestr(extra_name, b"ca-app-pub-999/999")
    return str(apk)


def test_apk_ad_ids_reads_dex_and_skips_media_entries(tmp_path):
    apk = _fake_apk(tmp_path, b"\x00junk ca-app-pub-111/222 more ca-app-pub-111~333 junk")
    assert apk_ad_ids(apk) == {"ca-app-pub-111/222", "ca-app-pub-111~333"}


def _result(rows):
    return {"sections": {"S": rows}}


def test_ad_id_row_present_in_apk_counts_as_found_with_apk_labelled_note(tmp_path):
    # Regression: placements the capture never exercised (an uninstall survey
    # flow, deep-funnel screens) read as "Lệch" though the build carried the
    # exact checklist ID.
    apk = _fake_apk(tmp_path, b"ca-app-pub-111/222")
    result = _result([{"label": "Uninstall", "value": "ca-app-pub-111/222", "found": False, "note": "old"}])
    verify_apk_rows(result, "com.example.app", apk_fn=lambda pkg: (apk, False))
    row = result["sections"]["S"][0]
    assert row["found"] is True
    assert row["note"] == AD_ID_IN_APK_NOTE


def test_ad_id_row_matches_via_sheet_column_c_alt_value(tmp_path):
    # Placement-flag rows carry their ad unit ID in column C, not column B.
    apk = _fake_apk(tmp_path, b"ca-app-pub-111/222")
    result = _result(
        [
            {
                "label": "Uninstall",
                "value": "inter_uninstall_high",
                "alt_values": ["ca-app-pub-111/222"],
                "found": False,
                "note": "old",
            }
        ]
    )
    verify_apk_rows(result, "com.example.app", apk_fn=lambda pkg: (apk, False))
    assert result["sections"]["S"][0]["found"] is True


def test_ad_id_absent_from_apk_is_flagged_as_not_in_build(tmp_path):
    apk = _fake_apk(tmp_path, b"ca-app-pub-111/222")
    result = _result([{"label": "Onb4", "value": "ca-app-pub-111/777", "found": False, "note": "old"}])
    verify_apk_rows(result, "com.example.app", apk_fn=lambda pkg: (apk, False))
    row = result["sections"]["S"][0]
    assert row["found"] is False
    assert row["note"] == AD_ID_NOT_IN_APK_NOTE


def test_row_already_matched_in_log_keeps_its_log_verdict(tmp_path):
    apk = _fake_apk(tmp_path, b"ca-app-pub-111/222")
    result = _result([{"label": "Home", "value": "ca-app-pub-111/999", "found": True, "note": None}])
    verify_apk_rows(result, "com.example.app", apk_fn=lambda pkg: (apk, False))
    assert result["sections"]["S"][0]["found"] is True


def test_unavailable_apk_marks_app_id_unverified_rather_than_wrong():
    result = _result([{"label": "App ID", "value": "ca-app-pub-111~222", "found": False, "note": "old"}])
    verify_apk_rows(result, "com.example.app", apk_fn=lambda pkg: (None, False))
    row = result["sections"]["S"][0]
    assert row["found"] is False
    assert row["note"] == APP_ID_UNVERIFIED_NOTE


def test_no_package_in_checklist_leaves_rows_untouched():
    result = _result([{"label": "App ID", "value": "ca-app-pub-111~222", "found": False, "note": "old"}])
    verify_apk_rows(result, None, apk_fn=lambda pkg: ("unused", False))
    assert result["sections"]["S"][0]["note"] == "old"


def test_cached_apk_is_not_deleted_after_use(tmp_path):
    # The whole point of the cache: a pulled APK survives the run so the next
    # one skips the ~45MB pull. Only an uncacheable (ephemeral) copy is removed.
    apk = _fake_apk(tmp_path, b"ca-app-pub-111/222")
    result = _result([{"label": "X", "value": "ca-app-pub-111/222", "found": False, "note": None}])
    verify_apk_rows(result, "com.example.app", apk_fn=lambda pkg: (apk, False))
    assert os.path.exists(apk)


def test_ephemeral_apk_is_deleted_after_use(tmp_path):
    apk = _fake_apk(tmp_path, b"ca-app-pub-111/222")
    result = _result([{"label": "X", "value": "ca-app-pub-111/222", "found": False, "note": None}])
    verify_apk_rows(result, "com.example.app", apk_fn=lambda pkg: (apk, True))
    assert not os.path.exists(apk)


def test_token_like_accepts_opaque_tokens_and_rejects_words():
    from apk_verifier import is_token_like

    assert is_token_like("uz6fb8kyeww0")                      # Adjust app token
    assert is_token_like("y9idfz")                            # Adjust event token
    assert is_token_like("1676822933375650")                  # Facebook app id
    assert is_token_like("b0fec8b50648f21fecccce7125c0e349")  # client token
    # "production" appears in every APK ever built; calling that a match would
    # pass a row nobody checked.
    assert not is_token_like("production")
    assert not is_token_like("true")
    assert not is_token_like("vi")
    assert not is_token_like("ai.photogenerator.aivideo.aiart")


def test_a_token_compiled_into_the_build_stops_reading_as_a_mismatch(monkeypatch, tmp_path):
    import apk_verifier

    result = {"sections": {"S": [
        {"label": "Adjust config token", "value": "uz6fb8kyeww0", "alt_values": [], "found": False, "note": None},
        {"label": "Adjust config environment", "value": "production", "alt_values": [], "found": False, "note": None},
    ]}}
    monkeypatch.setattr(apk_verifier, "apk_contains", lambda path, needles: {n: ["classes.dex"] for n in needles})
    apk_verifier.verify_apk_rows(result, "com.a", apk_fn=lambda pkg: (str(tmp_path / "a.apk"), False))

    token, environment = result["sections"]["S"]
    assert token["found"] is True
    assert "có trong build" in token["note"]
    # The plain word was never swept, so it stays unverified rather than passing.
    assert environment["found"] is False


def test_a_token_absent_from_the_build_says_so(monkeypatch, tmp_path):
    import apk_verifier

    result = {"sections": {"S": [
        {"label": "Adjust config token", "value": "uz6fb8kyeww0", "alt_values": [], "found": False, "note": None},
    ]}}
    monkeypatch.setattr(apk_verifier, "apk_contains", lambda path, needles: {n: [] for n in needles})
    apk_verifier.verify_apk_rows(result, "com.a", apk_fn=lambda pkg: (str(tmp_path / "a.apk"), False))

    row = result["sections"]["S"][0]
    assert row["found"] is False
    assert "không tồn tại trong build" in row["note"]

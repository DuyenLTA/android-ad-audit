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

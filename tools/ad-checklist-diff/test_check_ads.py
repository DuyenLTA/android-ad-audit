import check_ads
from check_ads import (
    diff,
    extract_key_cooccurrences,
    extract_key_value_pairs,
    extract_label_value_pairs,
    extract_values,
    load_trusted_lines,
    parse_checklist_csv,
    sheet_csv_url,
)


def test_extract_values_trailing_colon_shape():
    lines = ["08-29 23:45:48.584 20978 20978 I FOR_TESTER_CONFIG: Adjust config token: uz6fb8kyeww0\n"]
    assert "uz6fb8kyeww0" in extract_values(lines)


def test_extract_values_bracket_list_shape():
    lines = [
        "08-29 23:49:41.390 22072 22072 I FO_VslTemplate4FirstOpenSDK: LFO1: "
        "[ca-app-pub-4973559944609228/6280116312, ca-app-pub-4973559944609228/9966424892]\n"
    ]
    values = extract_values(lines)
    assert "ca-app-pub-4973559944609228/6280116312" in values
    assert "ca-app-pub-4973559944609228/9966424892" in values


def test_extract_values_bare_id_shape():
    lines = ["... Received app ID: `ca-app-pub-4973559944609228~7143022911`.\n"]
    assert "ca-app-pub-4973559944609228~7143022911" in extract_values(lines)


def test_extract_values_trailing_colon_survives_earlier_bracket():
    # Regression: an earlier [tag]-style bracket on the line must not
    # suppress extraction of a later `Label: value` pair.
    lines = ["... FOR_TESTER_CONFIG: [debug] Adjust config token: uz6fb8kyeww0\n"]
    values = extract_values(lines)
    assert "uz6fb8kyeww0" in values
    assert "debug" in values  # bracket item still extracted too


def test_extract_values_remote_config_key_shape_strips_show_prefix():
    lines = [
        "09-07 23:24:58.779 26748 26784 D RemoteConfigRepository: "
        "\U0001f4be [Boolean] key=show_native_loading_high, value=true\n"
    ]
    values = extract_values(lines)
    assert "show_native_loading_high" in values
    assert "native_loading_high" in values  # show_ prefix stripped too


def test_extract_values_remote_config_key_without_show_prefix_not_stripped():
    lines = ["... key=enable_401_home_a_inter_high, value=true\n"]
    values = extract_values(lines)
    assert "enable_401_home_a_inter_high" in values
    assert "enable_401_home_a_inter" not in values  # only a literal show_ prefix is stripped


def test_extract_values_remote_config_key_false_is_not_a_match():
    lines = ["... key=show_native_loading_high, value=false\n"]
    values = extract_values(lines)
    assert "show_native_loading_high" not in values
    assert "native_loading_high" not in values


def test_extract_label_value_pairs():
    lines = ["08-29 23:45:48.584 20978 20978 I FOR_TESTER_CONFIG: Adjust config token: uz6fb8kyeww0\n"]
    assert extract_label_value_pairs(lines) == {"Adjust config token": "uz6fb8kyeww0"}


def test_extract_label_value_pairs_ignores_lines_without_a_separate_label():
    # Only tag+value, no ": "-separated label in between -- nothing to key off.
    lines = ["... Received app ID: `ca-app-pub-4973559944609228~7143022911`.\n"]
    assert extract_label_value_pairs(lines) == {}


def test_extract_key_value_pairs_includes_both_prefixed_and_stripped_keys():
    lines = ["... key=show_native_loading_high, value=false\n"]
    pairs = extract_key_value_pairs(lines)
    assert pairs["show_native_loading_high"] == "false"
    assert pairs["native_loading_high"] == "false"


def test_extract_key_cooccurrences_groups_keys_on_the_same_line():
    lines = [
        "... loadDoubleIds: canShowHigh=true (key=enable_401_home_a_inter_high), "
        "canShowNormal=true (key=show_inter_feature)\n"
    ]
    cooccurrences = extract_key_cooccurrences(lines)
    assert cooccurrences["show_inter_feature"] == {"enable_401_home_a_inter_high"}
    assert cooccurrences["enable_401_home_a_inter_high"] == {"show_inter_feature"}


def test_extract_key_cooccurrences_ignores_a_lone_key_on_a_line():
    lines = ["... key=show_inter_feature, value=true\n"]
    assert extract_key_cooccurrences(lines) == {}


def test_load_trusted_lines_reports_zero_matches_per_filter(tmp_path):
    log = tmp_path / "capture.log"
    log.write_text("TAG_A: hello\nTAG_A: world\n", encoding="utf-8")
    trusted = load_trusted_lines(str(log), ["TAG_A", "TAG_B"])
    assert len(trusted["TAG_A"]) == 2
    assert trusted["TAG_B"] == []


def test_sheet_csv_url_preserves_gid():
    url = "https://docs.google.com/spreadsheets/d/ABC123/edit#gid=456"
    assert sheet_csv_url(url) == (
        "https://docs.google.com/spreadsheets/d/ABC123/export?format=csv&gid=456"
    )


def test_sheet_csv_url_without_gid():
    url = "https://docs.google.com/spreadsheets/d/ABC123/edit"
    assert sheet_csv_url(url) == "https://docs.google.com/spreadsheets/d/ABC123/export?format=csv"


def test_parse_checklist_csv_section_headers_and_rows():
    csv_text = (
        "Thông số kỹ thuật,\n"
        "Adjust config environment,production\n"
        ",\n"
        "2. ID ads FO,\n"
        "show_101_spl_a_banner_high,ca-app-pub-4973559944609228/3458511852\n"
    )
    rows = parse_checklist_csv(csv_text)
    assert rows == [
        {
            "section": "Thông số kỹ thuật",
            "label": "Adjust config environment",
            "value": "production",
            "alt_values": [],
        },
        {
            "section": "2. ID ads FO",
            "label": "show_101_spl_a_banner_high",
            "value": "ca-app-pub-4973559944609228/3458511852",
            "alt_values": [],
        },
    ]


def test_parse_checklist_csv_detects_swapped_columns():
    # Column A holds the ID, column B holds the label -- opposite of every
    # other section. Must still land value=ID, label=name.
    csv_text = (
        "4. ID ads resume,\n"
        "ca-app-pub-4973559944609228/2562724354,show_501_aoa_high\n"
    )
    rows = parse_checklist_csv(csv_text)
    assert rows == [
        {
            "section": "4. ID ads resume",
            "label": "show_501_aoa_high",
            "value": "ca-app-pub-4973559944609228/2562724354",
            "alt_values": [],
        }
    ]


def test_parse_checklist_csv_reads_optional_alt_values_column():
    csv_text = (
        "3. ID ads inapp,\n"
        "Home,inter_feature_high,enable_401_home_a_inter_high\n"
    )
    rows = parse_checklist_csv(csv_text)
    assert rows == [
        {
            "section": "3. ID ads inapp",
            "label": "Home",
            "value": "inter_feature_high",
            "alt_values": ["enable_401_home_a_inter_high"],
        }
    ]


def test_diff_marks_missing_and_extra():
    checklist = [
        {"section": "S", "label": "a", "value": "111"},
        {"section": "S", "label": "b", "value": "222"},
    ]
    result = diff(checklist, {"111", "999"})
    rows = result["sections"]["S"]
    assert {r["label"]: r["found"] for r in rows} == {"a": True, "b": False}
    assert result["extra"] == ["999"]


def test_diff_matches_via_known_alias(monkeypatch):
    # KNOWN_ALIASES starts empty by default (every entry must be a confirmed
    # mapping, not a guess) -- this test only exercises the mechanism.
    monkeypatch.setitem(check_ads.KNOWN_ALIASES, "placement_x", ["internal_key_y"])
    checklist = [{"section": "S", "label": "Home", "value": "placement_x"}]
    result = diff(checklist, {"internal_key_y"})
    assert result["sections"]["S"][0]["found"] is True
    assert result["extra"] == []


def test_diff_matches_via_alt_values():
    checklist = [
        {"section": "S", "label": "Home", "value": "inter_feature_high",
         "alt_values": ["enable_401_home_a_inter_high"]},
    ]
    result = diff(checklist, {"enable_401_home_a_inter_high"})
    assert result["sections"]["S"][0]["found"] is True


def test_diff_alt_values_excluded_from_extra():
    checklist = [
        {"section": "S", "label": "Home", "value": "inter_feature_high",
         "alt_values": ["enable_401_home_a_inter_high"]},
    ]
    result = diff(checklist, {"enable_401_home_a_inter_high"})
    assert result["extra"] == []


def test_diff_matched_row_has_no_note():
    checklist = [{"section": "S", "label": "a", "value": "111"}]
    result = diff(checklist, {"111"})
    assert result["sections"]["S"][0]["note"] is None


def test_diff_note_shows_actual_logged_value_for_label_mismatch():
    checklist = [{"section": "S", "label": "Adjust config token", "value": "uz6fb8kyeww0"}]
    result = diff(
        checklist, set(), label_value_pairs={"Adjust config token": "different_token_abc"}
    )
    assert result["sections"]["S"][0]["note"] == "Log đang có giá trị khác: different_token_abc"


def test_diff_note_shows_flag_disabled_for_key_mismatch():
    checklist = [{"section": "S", "label": "Loading", "value": "native_loading_high"}]
    result = diff(
        checklist, set(), key_value_pairs={"native_loading_high": "false"}
    )
    assert result["sections"]["S"][0]["note"] == "Flag có trong log nhưng đang tắt (value=false)"


def test_diff_note_falls_back_when_nothing_at_all_available():
    checklist = [{"section": "S", "label": "show_101", "value": "ca-app-pub-1/2"}]
    result = diff(checklist, set())
    assert result["sections"]["S"][0]["note"] == "Không thấy giá trị lạ nào liên quan trong log"


def test_diff_note_lists_leftover_ids_for_id_shaped_row():
    checklist = [{"section": "S", "label": "show_101", "value": "ca-app-pub-1/2"}]
    trusted_values = {"ca-app-pub-9/9"}  # an unrelated extra ID, not this row's value
    result = diff(checklist, trusted_values)
    assert result["sections"]["S"][0]["note"] == (
        "Giá trị lạ thấy trong log (chưa rõ có phải cùng placement): ca-app-pub-9/9"
    )


def test_diff_note_lists_cooccurrence_candidates_from_matched_sibling():
    # Mirrors the real Home/inter_feature_high case: a matched sibling row's
    # key (show_inter_feature) co-occurs on the same log line as an
    # unclaimed key (enable_401_home_a_inter_high) -- a targeted candidate
    # for the row that couldn't otherwise be matched.
    checklist = [
        {"section": "S", "label": "Home", "value": "inter_feature"},
        {"section": "S", "label": "Home", "value": "inter_feature_high"},
    ]
    result = diff(
        checklist,
        {"inter_feature"},
        key_cooccurrences={"show_inter_feature": {"enable_401_home_a_inter_high"}},
    )
    rows = result["sections"]["S"]
    assert rows[0]["found"] is True
    assert rows[1]["found"] is False
    assert rows[1]["note"] == (
        "Giá trị lạ thấy trong log (chưa rõ có phải cùng placement): enable_401_home_a_inter_high"
    )


def test_diff_note_truncates_long_candidate_lists():
    checklist = [
        {"section": "S", "label": "Home", "value": "inter_feature"},
        {"section": "S", "label": "Home", "value": "inter_feature_high"},
    ]
    many_keys = {f"key_{i}" for i in range(8)}
    result = diff(
        checklist, {"inter_feature"}, key_cooccurrences={"show_inter_feature": many_keys}
    )
    note = result["sections"]["S"][1]["note"]
    assert note.startswith("Giá trị lạ thấy trong log")
    assert "(+3 khác)" in note

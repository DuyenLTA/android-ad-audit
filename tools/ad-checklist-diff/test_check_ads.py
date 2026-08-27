from check_ads import diff, extract_values, load_trusted_lines, parse_checklist_csv, sheet_csv_url


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
        },
        {
            "section": "2. ID ads FO",
            "label": "show_101_spl_a_banner_high",
            "value": "ca-app-pub-4973559944609228/3458511852",
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

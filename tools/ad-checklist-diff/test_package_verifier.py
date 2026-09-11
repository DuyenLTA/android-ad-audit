from package_verifier import is_package_name, verify_package_rows


def test_is_package_name_matches_real_package():
    assert is_package_name("ai.photogenerator.aivideo.aivideogenerator.aiart")


def test_is_package_name_rejects_other_checklist_value_shapes():
    assert not is_package_name("production")
    assert not is_package_name("uz6fb8kyeww0")
    assert not is_package_name("show_101_spl_a_banner_high")
    assert not is_package_name("ca-app-pub-4973559944609228~7143022911")
    assert not is_package_name("ca-app-pub-4973559944609228/3458511852")


def test_verify_package_rows_overrides_found_status():
    result = {
        "sections": {
            "S": [
                {"label": "Package name", "value": "ai.photogenerator.aivideo.aiart", "found": False},
                {"label": "some ad id", "value": "ca-app-pub-1/2", "found": False},
            ]
        }
    }
    verify_package_rows(result, installed_packages_fn=lambda: {"ai.photogenerator.aivideo.aiart"})
    rows = result["sections"]["S"]
    assert rows[0]["found"] is True
    assert rows[1]["found"] is False  # untouched -- not a package-name shape


def test_verify_package_rows_leaves_status_alone_when_adb_query_fails():
    result = {
        "sections": {
            "S": [{"label": "Package name", "value": "ai.photogenerator.aivideo.aiart", "found": False}]
        }
    }

    def failing_lookup():
        raise OSError("adb not found")

    verify_package_rows(result, installed_packages_fn=failing_lookup)
    assert result["sections"]["S"][0]["found"] is False


def test_log_tags_match_case_sensitively(tmp_path):
    # A capture that never enabled the tester dump still carried one unrelated
    # `config_for_tester:` line -- lowercase, and enough to make the "filter
    # matched nothing" warning stay silent while five correct rows read as
    # mismatched.
    from log_extractor import load_trusted_lines

    log = tmp_path / "c.log"
    log.write_text(
        "I config_for_tester: Firebase token: abc\n"
        "D AdSdkAdjust: Event success data: {\"app_token\":\"uz6fb8kyeww0\"}\n",
        encoding="utf-8",
    )
    by = load_trusted_lines(str(log), ["FOR_TESTER", "AdSdkAdjust"])
    assert by["FOR_TESTER"] == []
    assert len(by["AdSdkAdjust"]) == 1

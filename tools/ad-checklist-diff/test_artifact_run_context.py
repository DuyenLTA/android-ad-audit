from artifact_run_context import capture_warning, delta_note, mode_label


def test_delta_of_an_unchanged_rerun_says_so():
    assert delta_note({"delta": {"changed": False}}) == "không đổi"


def test_delta_names_what_actually_moved():
    note = delta_note({"delta": {"changed": True, "broke": [1, 2], "fixed": [], "new_leftover_ids": [3]}})
    assert "2 dòng mới lệch" in note
    assert "1 ID lạ mới" in note
    assert "đã fix" not in note


def test_no_triage_admits_it_does_not_know():
    assert delta_note(None) == "không rõ"
    assert capture_warning(None) == ""


def test_a_run_that_never_captured_is_called_out():
    warn = capture_warning({"missed_home": None})
    assert "không capture" in warn


def test_a_journey_that_stopped_short_names_the_pass():
    warn = capture_warning({"missed_home": ["old"]})
    assert "old" in warn and "chưa tới được Home" in warn


def test_a_full_capture_earns_no_banner():
    assert capture_warning({"missed_home": [], "empty_filters": []}) == ""


def test_a_filter_that_matched_nothing_is_called_out():
    warn = capture_warning({"missed_home": [], "empty_filters": ["FOR_TESTER"]})
    assert "FOR_TESTER" in warn


def test_triage_from_the_old_tool_says_the_context_is_missing():
    # Absent key is not the same as null: one is "no capture", the other is
    # "nobody recorded whether there was one".
    warn = capture_warning({"delta": {"changed": False}})
    assert "bản tool cũ" in warn


def test_capture_warning_escapes_what_it_quotes():
    warn = capture_warning({"missed_home": ["<script>"]})
    assert "<script>" not in warn


def test_mode_label_falls_back_to_whatever_it_was_given():
    assert "lái máy" in mode_label("capture")
    assert mode_label("") == "không rõ"
    assert mode_label("weird") == "weird"


# --- What the page may and may not claim about the build --------------------

def test_a_run_with_no_log_says_the_variant_was_never_checked():
    # Every dev-build signal lives in what the app printed at runtime. Saying
    # nothing here reads as "checked, it is a release build".
    warning = capture_warning({"missed_home": None, "dev_build_signals": None})
    assert "build release hay build dev" in warning


def test_a_capture_that_found_nothing_does_not_raise_the_question():
    # [] is an answer: the log was read and named no dev-build signal.
    warning = capture_warning({"missed_home": [], "dev_build_signals": []})
    assert "build release hay build dev" not in warning


def test_a_reused_capture_is_declared_on_the_page():
    # The reader's default assumption is that the phone ran just now.
    warning = capture_warning(
        {"missed_home": [], "capture_reused_from": "2026-09-14T08:00:00+00:00"}
    )
    assert "dùng lại log" in warning and "2026-09-14" in warning


def test_a_fresh_capture_says_nothing_about_reuse():
    assert "dùng lại log" not in capture_warning({"missed_home": []})

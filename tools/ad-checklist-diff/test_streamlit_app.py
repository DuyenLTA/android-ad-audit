"""In-process UI test using Streamlit's AppTest -- no browser needed.

Exercises the real Start/Stop flow against the actual connected device, but
without requiring precisely-timed phone taps: it captures for a couple of
seconds of ambient logcat traffic, which is enough to prove the subprocess
lifecycle and report pipeline work end-to-end, even if the checklist match
count itself is low (nothing was deliberately triggered on the phone).
"""
import subprocess
import time

from streamlit.testing.v1 import AppTest


class _FakeProc:
    """Duck-types subprocess.Popen just enough for the Stop button's terminate/wait calls."""

    def terminate(self):
        pass

    def wait(self, timeout=None):
        pass


def _device_attached() -> bool:
    out = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=10).stdout
    return any(ln.strip().endswith("device") for ln in out.splitlines()[1:])


def test_start_stop_lifecycle_with_real_device():
    if not _device_attached():
        import pytest

        pytest.skip("no adb device attached -- skipping live capture test")

    at = AppTest.from_file("streamlit_app.py")
    at.run()

    at.text_input[0].set_value(
        "https://docs.google.com/spreadsheets/d/14XivZl9VPAnyf8hYICgRh-TOUmkGTZDCqoyWmPM57hM/edit"
    )
    at.run()

    assert not at.session_state["capture_proc"]
    at.button(key="start_btn").click().run()
    assert at.session_state["capture_proc"] is not None
    assert at.session_state["log_path"].exists()

    time.sleep(2)  # let a couple seconds of ambient logcat accumulate

    at.button(key="stop_btn").click().run(timeout=20)  # includes a real network fetch of the sheet
    assert at.session_state["capture_proc"] is None
    assert not at.exception
    # Report must be linked over the app's own http origin -- a file://
    # URL is blocked by the browser when navigated to from an http page.
    assert at.get("link_button")[0].url.startswith("/app/static/")


def test_stop_with_invalid_sheet_url_shows_clean_error(tmp_path):
    # Regression: check_ads' pipeline raises SystemExit for user-facing
    # errors (bad sheet URL). Streamlit's own error boundary only catches
    # Exception, so an uncaught SystemExit previously froze the page
    # instead of showing st.error.
    log_path = tmp_path / "capture.log"
    log_path.write_text("some captured line\n", encoding="utf-8")

    at = AppTest.from_file("streamlit_app.py")
    at.run()
    at.session_state["capture_proc"] = _FakeProc()
    at.session_state["log_path"] = log_path
    at.session_state["run_sheet_url"] = "https://example.com/not-a-sheet"
    at.session_state["run_filters"] = ["FOR_TESTER"]
    at.run()

    at.button(key="stop_btn").click().run(timeout=20)
    assert not at.exception
    assert at.session_state["capture_proc"] is None
    assert any("Not a recognizable Google Sheet URL" in e.value for e in at.error)


def test_stop_with_zero_byte_capture_shows_clean_error(tmp_path):
    log_path = tmp_path / "empty.log"
    log_path.touch()

    at = AppTest.from_file("streamlit_app.py")
    at.run()
    at.session_state["capture_proc"] = _FakeProc()
    at.session_state["log_path"] = log_path
    at.session_state["run_sheet_url"] = "https://docs.google.com/spreadsheets/d/x/edit"
    at.session_state["run_filters"] = ["FOR_TESTER"]
    at.run()

    at.button(key="stop_btn").click().run(timeout=20)
    assert not at.exception
    assert at.session_state["capture_proc"] is None
    assert any("Captured 0 bytes" in e.value for e in at.error)

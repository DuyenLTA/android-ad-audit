"""A dev build has to be named as one before anybody reads its mismatches."""
import build_identity
import device_navigator
from build_identity import dev_build_signals

SAMPLE_ID = "ca-app-pub-3940256099942544/2247696110"
REAL_ID = "ca-app-pub-4973559944609228/2720278708"


def _result(extra=(), found=(), missing=()):
    rows = [{"value": v, "found": True} for v in found]
    rows += [{"value": v, "found": False} for v in missing]
    return {"extra": list(extra), "sections": {"1. Thông số kỹ thuật": rows}}


def test_sample_ad_units_are_a_dev_build_signal():
    signals = dev_build_signals(_result(extra=[f"NATIVE - {SAMPLE_ID}"]))
    assert len(signals) == 1
    assert "ID mẫu" in signals[0]
    assert "3940256099942544" in signals[0]


def test_adjust_sandbox_is_a_dev_build_signal():
    assert dev_build_signals(_result(extra=["sandbox"])) == [
        "Adjust đang ở môi trường sandbox"
    ]


def test_both_signals_are_reported_together():
    assert len(dev_build_signals(_result(extra=["sandbox", SAMPLE_ID]))) == 2


def test_a_release_build_raises_nothing():
    # The regression to avoid in the other direction: crying dev build on a
    # release run would train everyone to ignore the banner.
    assert dev_build_signals(_result(extra=[REAL_ID], found=["production"])) == []


def test_sandbox_inside_a_longer_value_is_not_the_marker():
    # res/raw/omsdk_sandbox.js and friends are not the Adjust environment.
    assert dev_build_signals(_result(extra=["omsdk_sandbox.js", "my-sandbox-key"])) == []


def test_a_sample_id_the_checklist_itself_claims_still_counts():
    # An app shipping a test id on purpose is still a build serving test ads;
    # the row matching does not make the ads real.
    assert dev_build_signals(_result(found=[SAMPLE_ID])) != []


def test_nothing_collected_means_nothing_claimed():
    assert dev_build_signals(None) == []
    assert dev_build_signals({}) == []


# --- The journey stops when the build names itself a dev build --------------

def test_watcher_reports_the_marker_once_it_arrives(tmp_path):
    path = tmp_path / "c.log"
    path.write_text("", encoding="utf-8")
    watch = build_identity.log_watcher(str(path))

    assert watch() is None
    path.write_text("I AdSdk: Config variant dev: true\n", encoding="utf-8")
    assert "Config variant dev" in watch()


def test_watcher_sees_a_marker_split_across_two_reads(tmp_path):
    # Only what has arrived since the last call is read, so a marker landing on
    # a chunk boundary has to survive the seam or the run walks every screen.
    path = tmp_path / "c.log"
    path.write_text("I AdSdk: Config variant d", encoding="utf-8")
    watch = build_identity.log_watcher(str(path))
    assert watch() is None

    with open(path, "a", encoding="utf-8") as handle:
        handle.write("ev: true\n")
    assert watch() is not None


def test_watcher_is_quiet_on_a_release_log(tmp_path):
    path = tmp_path / "c.log"
    path.write_text("I AdSdk: Config variant dev: false\n", encoding="utf-8")
    assert build_identity.log_watcher(str(path))() is None


def test_watcher_survives_a_capture_file_that_is_not_there_yet(tmp_path):
    # Not readable yet is not an answer about the build; the next poll asks again.
    assert build_identity.log_watcher(str(tmp_path / "missing.log"))() is None


def test_drive_stops_when_asked_to_abandon():
    calls = {"n": 0}

    def run(args, **kw):
        calls["n"] += 1
        return "mCurrentFocus=Window{1 u0 com.x/com.x.Splash}\n"

    result = device_navigator.drive_to_home(
        package="com.x",
        run=run,
        sleep=lambda s: None,
        xml_fn=lambda: "<node />",
        should_abandon=lambda: "build tự khai Config variant dev: true",
    )

    assert result["stopped"] == "abandoned"
    assert result["reached_home"] is False
    assert "Config variant dev" in result["actions"][-1]
    # Abandoned before driving anything: the point is not to walk the journey.
    assert calls["n"] == 0


def test_drive_carries_on_while_the_watcher_is_quiet():
    result = device_navigator.drive_to_home(
        package="com.x",
        timeout=0,
        run=lambda args, **kw: "mCurrentFocus=Window{1 u0 com.x/com.x.Splash}\n",
        sleep=lambda s: None,
        xml_fn=lambda: "<node />",
        should_abandon=lambda: None,
    )
    assert result["stopped"] != "abandoned"

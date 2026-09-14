"""Trusted lines are the evidence base; a line from another app is not evidence."""
import log_extractor


# --- Another app's Firebase batch is not evidence about this build ----------

FA = "09-14 13:41:11.206 31646 21554 V FA-SVC  : "


def _log(tmp_path, *lines):
    path = tmp_path / "capture.log"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def test_a_batch_naming_another_app_is_dropped(tmp_path):
    # The real hazard, seen in a real capture: a neighbouring app's batch is
    # uploaded during this capture and its ad unit id read as this build's.
    path = _log(
        tmp_path,
        FA + "app_id: com.other.app",
        FA + "inter_ads ca-app-pub-999/888",
    )
    lines = log_extractor.load_trusted_lines(path, ["inter_ads"], package="com.mine")
    assert lines["inter_ads"] == []


def test_the_batch_of_the_audited_app_stays(tmp_path):
    path = _log(
        tmp_path,
        FA + "app_id: com.mine",
        FA + "inter_ads ca-app-pub-111/222",
    )
    lines = log_extractor.load_trusted_lines(path, ["inter_ads"], package="com.mine")
    assert len(lines["inter_ads"]) == 1


def test_a_later_batch_ends_the_previous_one(tmp_path):
    path = _log(
        tmp_path,
        FA + "app_id: com.other.app",
        FA + "inter_ads ca-app-pub-999/888",
        FA + "app_id: com.mine",
        FA + "inter_ads ca-app-pub-111/222",
    )
    lines = log_extractor.load_trusted_lines(path, ["inter_ads"], package="com.mine")
    assert len(lines["inter_ads"]) == 1
    assert "111/222" in lines["inter_ads"][0]


def test_lines_outside_fa_svc_are_never_dropped(tmp_path):
    # The app's own tags are not batched and carry no owner; a foreign batch
    # must not silence them.
    path = _log(
        tmp_path,
        FA + "app_id: com.other.app",
        "09-14 13:41:12.000 111 111 I inter_ads: ca-app-pub-111/222",
    )
    lines = log_extractor.load_trusted_lines(path, ["inter_ads"], package="com.mine")
    assert len(lines["inter_ads"]) == 1


def test_an_unnamed_batch_is_kept(tmp_path):
    # Unknown is not foreign: dropping unnamed batches would lose real evidence.
    path = _log(tmp_path, FA + "inter_ads ca-app-pub-111/222")
    lines = log_extractor.load_trusted_lines(path, ["inter_ads"], package="com.mine")
    assert len(lines["inter_ads"]) == 1


def test_without_a_package_nothing_is_dropped(tmp_path):
    path = _log(
        tmp_path,
        FA + "app_id: com.other.app",
        FA + "inter_ads ca-app-pub-999/888",
    )
    lines = log_extractor.load_trusted_lines(path, ["inter_ads"])
    assert len(lines["inter_ads"]) == 1

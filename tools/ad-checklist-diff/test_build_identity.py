"""A dev build has to be named as one before anybody reads its mismatches."""
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

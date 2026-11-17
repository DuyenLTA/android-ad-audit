"""Foreign-driver guard and native-ad parsing, on dumps captured from a real device."""
from pathlib import Path

from device_guard import foreign_package
from ui_nodes import area, intersection, is_fullscreen_ad_activity, native_parts, parse_nodes

PKG = "com.hairai.hairstyletryon.haircolorchanger"
FIX = Path(__file__).resolve().parent / "fixtures"


def _nodes(name):
    return parse_nodes((FIX / name).read_text(encoding="utf-8"))


def test_another_app_on_screen_is_foreign():
    assert foreign_package({PKG, "com.aihomedesign.aihomedecor.designidea.aiinterior"}, PKG, False) \
        == "com.aihomedesign.aihomedecor.designidea.aiinterior"


def test_system_dialogs_and_ad_destinations_are_not_foreign():
    assert foreign_package({PKG, "com.android.systemui", "com.google.android.permissioncontroller"}, PKG, False) is None
    # Play Store right after our own ad tap is where the ad sent us.
    assert foreign_package({"com.android.vending"}, PKG, after_ad_tap=True) is None
    assert foreign_package({"com.android.vending"}, PKG, after_ad_tap=False) == "com.android.vending"


def test_settled_native_has_every_measured_part():
    parts = native_parts(_nodes("native-settled-hair-language2.xml"))
    assert all(parts[k] for k in ("native", "media", "cta", "attribution", "adchoices"))
    assert parts["shimmer"] is None
    ad, choices = parts["native"]["bounds"], parts["adchoices"]["bounds"]
    assert intersection(ad, choices) == area(choices)  # AdChoices fully inside the native


def test_native_still_loading_has_shimmer_and_no_adchoices():
    parts = native_parts(_nodes("native-loading-hair-language1.xml"))
    assert parts["shimmer"] is not None and parts["adchoices"] is None


def test_fullscreen_ad_activities_are_recognised():
    assert is_fullscreen_ad_activity(f"{PKG}/com.google.android.libraries.ads.mobile.sdk.common.AdActivity")
    assert not is_fullscreen_ad_activity(f"{PKG}/com.vsl.aip862_aihairstyle.ui.splash.SplashActivity")


def test_hold_device_khi_job_cha_da_giu_khoa(monkeypatch, tmp_path):
    # Bot rc-check giu khoa may cho ca job va dat RCR_GIU_MAY=<serial>: policy-check chay ben trong khong tu chan minh.
    import device_guard
    monkeypatch.setattr(device_guard, "lock_path", lambda s: tmp_path / f".may-{s}.lock")
    with device_guard.hold_device("S1"):
        monkeypatch.setenv("RCR_GIU_MAY", "S1")
        with device_guard.hold_device("S1"):          # cung serial voi job cha -> khong khoa lai
            pass
        monkeypatch.setenv("RCR_GIU_MAY", "S2")
        import pytest
        with pytest.raises(BlockingIOError):         # serial khac van bi chan nhu cu
            with device_guard.hold_device("S1"):
                pass

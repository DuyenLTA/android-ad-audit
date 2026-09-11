from device_navigator import drive_to_home
from device_flow import DEFAULT_RULES, rule_for


def test_rule_matches_by_activity_substring():
    assert rule_for("com.x.VslTemplate4Language14Activity", DEFAULT_RULES)["match"] == "Language"
    assert rule_for("com.google.android.gms.ads.AdActivity", DEFAULT_RULES)["match"] == "AdActivity"
    assert rule_for("com.x.SomethingElse", DEFAULT_RULES) is None


class _FakeDevice:
    """Replays a scripted screen sequence, advancing on each performed step."""

    def __init__(self, screens):
        self.screens = list(screens)
        self.taps = []

    def run(self, args, **kwargs):
        if args[:3] == ["shell", "dumpsys", "window"]:
            return f"mCurrentFocus=Window{{1 u0 com.x/{self.screens[0]}}}\n"
        if "input" in args:
            self.taps.append(" ".join(args))
            if len(self.screens) > 1:
                self.screens.pop(0)
        return ""


def test_drives_through_screens_until_home():
    device = _FakeDevice(
        [
            "com.x.VslTemplate4OnboardingActivity",
            "com.x.VslTemplate4QuestionActivity",
            "com.x.MainActivity",
        ]
    )
    xml = (
        '<node resource-id="com.x:id/btnNextOnboarding" text="Next" bounds="[10,10][90,50]" />'
        '<node resource-id="com.x:id/ivQuestionImage" text="" bounds="[10,60][90,100]" />'
    )
    result = drive_to_home(
        timeout=30, dwell=0, xml_fn=lambda: xml, run=device.run, sleep=lambda s: None
    )
    assert result["reached_home"] is True
    assert result["visited"][-1] == "MainActivity"


def test_gives_up_at_timeout_without_claiming_home():
    device = _FakeDevice(["com.x.UnknownActivity"])
    result = drive_to_home(
        timeout=0.2, dwell=0, xml_fn=lambda: "", run=device.run, sleep=lambda s: None
    )
    assert result["reached_home"] is False


def test_ad_screen_keeps_retrying_its_close_steps():
    # Regression: an interstitial whose countdown had not finished consumed
    # every step on the first pass and the run then sat on that screen until
    # timeout. The closing steps must cycle instead.
    device = _FakeDevice(["com.google.android.gms.ads.AdActivity"])
    xml = '<node text="Fechar" content-desc="" bounds="[100,100][200,160]" />'
    drive_to_home(
        timeout=1.2, dwell=0, xml_fn=lambda: xml, run=device.run, sleep=lambda s: None
    )
    closes = [t for t in device.taps if "tap" in t or "keyevent" in t]
    assert len(closes) > 1, "phải thử đóng nhiều lần, không chỉ một lần"


def test_each_arrival_at_a_screen_restarts_its_steps():
    # Two distinct language activities share one rule; the second must run the
    # full pick-then-confirm pair rather than resuming mid-way.
    device = _FakeDevice(
        ["com.x.Language14Activity", "com.x.Language24Activity", "com.x.MainActivity"]
    )
    xml = '<node resource-id="com.x:id/checkboxLanguageItem" text="" bounds="[10,10][90,50]" />'
    drive_to_home(
        timeout=30, dwell=0, xml_fn=lambda: xml, run=device.run, sleep=lambda s: None
    )
    assert len(device.taps) >= 2


def test_another_app_is_never_mistaken_for_home():
    # Regression: an ad tap opened YouTube, whose own `InternalMainActivity`
    # matched the home pattern and ended the run on the wrong app.
    class Device:
        def __init__(self):
            self.screens = [
                ("com.google.android.youtube", "com.google.android.youtube.InternalMainActivity"),
                ("com.x", "com.x.MainActivity"),
            ]
            self.launches = 0

        def run(self, args, **kwargs):
            if args[:3] == ["shell", "dumpsys", "window"]:
                pkg, act = self.screens[0]
                return f"mCurrentFocus=Window{{1 u0 {pkg}/{act}}}\n"
            if "monkey" in args:
                self.launches += 1
                self.screens.pop(0)
            return ""

    device = Device()
    result = drive_to_home(
        package="com.x", timeout=30, dwell=0, xml_fn=lambda: "",
        run=device.run, sleep=lambda s: None,
    )
    assert device.launches == 1, "phải mở lại app khi lạc sang app khác"
    assert result["reached_home"] is True
    assert result["visited"][-1] == "MainActivity"

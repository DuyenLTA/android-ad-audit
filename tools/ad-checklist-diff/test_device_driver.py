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


def test_every_pass_starts_from_an_empty_log_buffer(tmp_path, monkeypatch):
    # Regression: `adb logcat` replays the whole ring buffer before following,
    # so with a single clear up front the second pass re-appended everything the
    # first had already written -- half the capture duplicated itself and no
    # pass could be read on its own.
    import device_driver

    calls = []

    class _Proc:
        def terminate(self): pass
        def wait(self, timeout=None): pass

    monkeypatch.setattr(device_driver, "adb_run", lambda args, **k: calls.append(args) or "")
    monkeypatch.setattr(device_driver.subprocess, "Popen", lambda *a, **k: _Proc())
    monkeypatch.setattr(device_driver, "wipe_app_data", lambda *a, **k: None)
    monkeypatch.setattr(device_driver, "force_stop", lambda *a, **k: None)
    monkeypatch.setattr(device_driver, "launch", lambda *a, **k: None)
    monkeypatch.setattr(device_driver, "splash_logo_spam", lambda *a, **k: 0)
    monkeypatch.setattr(
        device_driver, "drive_to_home",
        lambda **k: {"reached_home": True, "visited": [], "actions": []},
    )
    # The Home wait watches a real clock; this test is about the log buffer.
    monkeypatch.setattr(device_driver, "wait_for_ad_quiet", lambda *a, **k: 0.0)

    device_driver.capture_session("com.x", str(tmp_path / "capture.log"))
    clears = [c for c in calls if c == ["logcat", "-c"]]
    assert len(clears) == len(device_driver.DEFAULT_PASSES)


def test_each_pass_writes_somewhere_an_orphan_cannot_reach(tmp_path, monkeypatch):
    # A killed run leaves `adb logcat` alive holding the capture file open. It
    # kept appending for half an hour -- other apps' logs included -- into the
    # file the audit then read.
    import device_driver

    written = []

    def fake_pass(package, log_file, **kwargs):
        written.append(log_file.name)
        log_file.write(f"log của {kwargs['fresh']}\n")
        return {"reached_home": True, "visited": [], "actions": []}

    monkeypatch.setattr(device_driver, "capture_pass", fake_pass)
    out = tmp_path / "capture.log"
    device_driver.capture_session("com.a", str(out))

    assert len(written) == 2
    assert all(str(out) != path for path in written)  # không lượt nào ghi thẳng
    assert out.read_text(encoding="utf-8").count("log của") == 2  # ghép đủ


def test_a_logcat_that_ignores_terminate_is_killed(monkeypatch, tmp_path):
    import subprocess as sp

    import device_driver

    killed = []

    class Stubborn:
        # subprocess.run() opens Popen as a context manager, and patching the
        # module attribute reaches every caller -- so the stub has to behave.
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def terminate(self):
            pass

        def kill(self):
            killed.append(True)

        def wait(self, timeout=None):
            if not killed:
                raise sp.TimeoutExpired("adb logcat", timeout)

    monkeypatch.setattr(device_driver, "adb_run", lambda *a, **k: "")
    monkeypatch.setattr(device_driver.subprocess, "Popen", lambda *a, **k: Stubborn())
    monkeypatch.setattr(device_driver, "wipe_app_data", lambda *a, **k: None)
    monkeypatch.setattr(device_driver, "force_stop", lambda *a, **k: None)
    monkeypatch.setattr(device_driver, "launch", lambda *a, **k: None)
    monkeypatch.setattr(device_driver, "splash_logo_spam", lambda *a, **k: True)
    monkeypatch.setattr(
        device_driver, "drive_to_home",
        lambda **k: {"reached_home": True, "visited": [], "actions": []},
    )
    with open(tmp_path / "p.log", "w", encoding="utf-8") as f:
        device_driver.capture_pass("com.a", f, fresh=False)
    assert killed == [True]


class _FakeDeviceWithPackages:
    """Like _FakeDevice, but each screen also declares which package owns it."""

    def __init__(self, screens):
        self.screens = list(screens)
        self.taps = []
        self.launches = 0

    def run(self, args, **kwargs):
        if args[:3] == ["shell", "dumpsys", "window"]:
            package, activity = self.screens[0]
            return f"mCurrentFocus=Window{{1 u0 {package}/{activity}}}\n"
        if args[:2] == ["shell", "monkey"]:
            self.launches += 1
            return ""
        if "input" in args:
            self.taps.append(" ".join(args))
            if len(self.screens) > 1:
                self.screens.pop(0)
        return ""


def test_permission_dialog_is_answered_rather_than_fled():
    # The notification prompt on Android 13+ is drawn by permissioncontroller,
    # so the "focus left the app" guard used to relaunch the app underneath it.
    # That does not dismiss the dialog -- it reappears, and the run burned its
    # whole timeout looping there instead of ever reaching Home.
    device = _FakeDeviceWithPackages(
        [
            ("com.android.permissioncontroller", "com.android.permissioncontroller."
             "permission.ui.GrantPermissionsActivity"),
            ("com.x", "com.x.MainActivity"),
        ]
    )
    xml = (
        '<node resource-id="com.android.permissioncontroller:id/permission_allow_button"'
        ' text="Allow" bounds="[10,10][90,50]" />'
    )
    result = drive_to_home(
        package="com.x", timeout=30, dwell=0,
        xml_fn=lambda: xml, run=device.run, sleep=lambda s: None,
    )
    assert result["reached_home"] is True
    assert device.launches == 0, "không được mở lại app đè lên hộp thoại quyền"
    assert any("tap" in t for t in device.taps)


def test_a_genuinely_foreign_app_is_still_left():
    # The escape hatch above must stay narrow: an ad tap that throws the device
    # into another app has no rule, so the driver still goes back to our app.
    device = _FakeDeviceWithPackages(
        [
            ("com.google.android.youtube", "com.google.android.youtube.InternalMainActivity"),
            ("com.x", "com.x.MainActivity"),
        ]
    )
    result = drive_to_home(
        package="com.x", timeout=1, dwell=0,
        xml_fn=lambda: "", run=device.run, sleep=lambda s: None,
    )
    assert device.launches >= 1, "app lạ thì vẫn phải mở lại app của mình"
    assert result["reached_home"] is False, "MainActivity của app khác không phải Home của mình"


def test_home_wait_ends_once_the_ad_lines_stop(tmp_path):
    # Measured on device: every trusted line lands within ~2s of reaching Home.
    # The wait should notice the quiet and return, not sit out the full cap.
    import device_driver

    path = tmp_path / "capture.log"
    path.write_text("", encoding="utf-8")
    clock = {"t": 0.0}

    def now():
        return clock["t"]

    def sleep(seconds):
        clock["t"] += seconds
        if clock["t"] <= 2.0:  # app still requesting
            with open(path, "a", encoding="utf-8") as f:
                f.write("D inter_ads: load inter ads\n")

    waited = device_driver.wait_for_ad_quiet(str(path), sleep=sleep, now=now)
    assert waited < device_driver.HOME_DWELL_CAP
    assert waited >= device_driver.HOME_MIN_SECONDS


def test_home_wait_never_outlasts_the_old_fixed_dwell(tmp_path):
    # An app that keeps logging must not extend the run indefinitely -- the cap
    # is what the wait used to be, so the worst case cannot get worse.
    import device_driver

    path = tmp_path / "capture.log"
    path.write_text("", encoding="utf-8")
    clock = {"t": 0.0}

    def sleep(seconds):
        clock["t"] += seconds
        with open(path, "a", encoding="utf-8") as f:
            f.write("D inter_ads: still going\n")

    waited = device_driver.wait_for_ad_quiet(
        str(path), sleep=sleep, now=lambda: clock["t"]
    )
    assert waited <= device_driver.HOME_DWELL_CAP + 1


def test_home_wait_falls_back_to_the_fixed_dwell_without_a_capture_file():
    # Losing the file must not mean skipping the wait: Home's placements would
    # never get a chance to request, and the capture would look clean.
    import device_driver

    slept = []
    waited = device_driver.wait_for_ad_quiet(
        "/nonexistent/capture.log", sleep=slept.append, now=lambda: 0.0
    )
    assert slept == [device_driver.HOME_DWELL_CAP]
    assert waited == device_driver.HOME_DWELL_CAP

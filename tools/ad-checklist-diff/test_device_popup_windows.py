from device_flow import perform_step
from device_popup_windows import popup_frames, uncovered_point

PKG = "com.aivideogenerator.aiphotoeditor.beautyeditor.imagetoimage"
ACT = "com.visionlab.tutorial.vsltemplate4.onboarding.question.VslTemplate4QuestionActivity"

# `dumpsys input` lines from the OPPO CPH2375 question screen (AIP882, 29/10/2026):
# two stacked validator popups, the activity's own window, and a system overlay.
DUMPSYS_INPUT = f"""
      2: name='Window{{1667c85 u0 ScreenDecorOverlay}}', displayId=0, visible=true, canReceiveKeys=false, flags=0x20800128, type=0x000007e8, frame=[0,0][720,101], touchableRegion=<empty>
      6: name='Window{{3cdc752 u0 {PKG}/{ACT}}}', displayId=0, paused=false, hasFocus=false, visible=true, canReceiveKeys=false, flags=0x00000328, type=0x00000002, frame=[0,674][640,984], touchableRegion=[0,674][640,984]
      7: name='Window{{5897c u0 {PKG}/{ACT}}}', displayId=0, paused=false, hasFocus=false, visible=true, canReceiveKeys=false, flags=0x00000328, type=0x00000002, frame=[0,674][640,984], touchableRegion=[0,674][640,984]
      8: name='Window{{3275184 u0 {PKG}/{ACT}}}', displayId=0, paused=false, hasFocus=true, visible=true, canReceiveKeys=true, flags=0x81810120, type=0x00000001, frame=[0,0][720,1612], touchableRegion=[0,0][720,1612]
"""

# Continue button behind the popup: x 32..688, y 872..952.
BUTTON = (32, 872, 688, 952)


def test_reads_popup_frames_but_not_full_screen_or_system_windows():
    assert popup_frames(DUMPSYS_INPUT, 720, 1612) == [(0, 674, 640, 984)]


def test_tap_lands_on_the_uncovered_end_of_the_button():
    x, y = uncovered_point(BUTTON, [(0, 674, 640, 984)])
    assert 640 <= x <= 672 and y == 912


def test_no_popup_means_the_centre():
    assert uncovered_point(BUTTON, []) == (360, 912)


def test_fully_covered_button_is_not_tapped():
    assert uncovered_point(BUTTON, [(0, 0, 720, 1612)]) is None


def test_continue_step_avoids_the_popup():
    xml = ('<hierarchy><node bounds="[0,0][720,1612]" />'
           '<node resource-id="x:id/btnNext" text="Go to Home" clickable="true" enabled="true" '
           'bounds="[32,872][688,952]" /></hierarchy>')
    taps = []

    def run(args, **kwargs):
        if args[:3] == ["shell", "dumpsys", "input"]:
            return DUMPSYS_INPUT
        if "tap" in args:
            taps.append((int(args[-2]), int(args[-1])))
        return ""

    label = perform_step({"tap_continue": True}, lambda: xml, run)
    assert label.startswith("continue (né popup")
    assert taps and taps[0][0] >= 640 and taps[0][1] == 912

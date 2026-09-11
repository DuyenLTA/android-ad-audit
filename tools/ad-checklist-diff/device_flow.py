"""The VSL onboarding flow as data: which screen wants which step, in order.

Screens are identified by focused activity name. Each screen has an ordered
step list; the driver performs one step per poll and remembers how far it got,
so a screen that needs several actions (pick a language, *then* confirm)
advances instead of repeating its first action forever.

Step kinds:
  {"tap": {...}}   tap a node, matched by resource-id / text / content-desc
  {"language": "English"}  pick a language, unfolding its variants if needed
  {"swipe": "left"}  page a pager forward
  {"wait": n}      do nothing this step (let an ad or screen settle)
  {"key": "..."}   send a keyevent, the fallback for ad/paywall dismissal

The order below mirrors the real flow, measured on device:
splash -> language -> onboarding (next, next, swipe, get started) -> question
-> interstitial -> paywall -> home.
"""
from device_language_picker import DEFAULT_LANGUAGE
from device_language_picker import pick as pick_language
from device_ui import find_close_center, find_node_center, key_event, swipe_left, tap

# Any language would reach Home, but the capture is read by people afterwards
# and a run in हिन्दी is a run nobody can check. See device_language_picker for
# why "first checkbox" landed there. The confirm button is `buttonLanguageNext`
# on some builds and `imageButtonLanguageNext` on others; a tap whose node is
# absent does nothing, so both are listed rather than guessed between.
LANGUAGE_STEPS = [
    {"language": DEFAULT_LANGUAGE},
    {"tap": {"resource_id": "id/buttonLanguageNext"}},
    {"tap": {"resource_id": "id/imageButtonLanguageNext"}},
]

# Page 3 advances by swipe rather than by the Next button.
ONBOARDING_STEPS = [
    {"tap": {"resource_id": "id/btnNextOnboarding"}},
    {"tap": {"resource_id": "id/btnNextOnboarding"}},
    {"wait": 2},
    {"swipe": "left"},
    {"tap": {"resource_id": "id/btnNextOnboarding"}},
    {"tap": {"text": "Get started"}},
]

# The question grid's cards carry no resource-id of their own; their inner
# image does. Nothing advances the screen until a card is picked -- the
# continue button is only added to the tree afterwards -- and its label depends
# on remote config, so try the known ones in turn.
QUESTION_STEPS = [
    {"tap": {"resource_id": "id/ivQuestionImage"}},
    {"tap": {"resource_id": "id/btnNextOnboardingImage"}},
    {"tap": {"text": "Go to Home"}},
    {"tap": {"text": "Next"}},
]
QUESTION_REPEAT_FROM = 1

# Let the interstitial actually load and show -- the audit exists to observe
# that -- then close it. The close control only appears once the countdown
# ends, so the first attempt is deliberately late, and the closing steps repeat
# until the screen actually changes rather than giving up after one pass.
INTERSTITIAL_STEPS = [
    {"wait": 9},
    {"tap_close": True},
    {"key": "KEYCODE_BACK"},
]
INTERSTITIAL_REPEAT_FROM = 1

PAYWALL_STEPS = [
    {"wait": 3},
    {"tap_close": True},
    {"tap": {"text": "Continue with ads"}},
    {"key": "KEYCODE_BACK"},
]
PAYWALL_REPEAT_FROM = 1

DEFAULT_RULES: list[dict] = [
    {"match": "Language", "steps": LANGUAGE_STEPS},
    {"match": "OnboardingActivity", "steps": ONBOARDING_STEPS},
    {"match": "QuestionActivity", "steps": QUESTION_STEPS, "repeat_from": QUESTION_REPEAT_FROM},
    {"match": "AdActivity", "steps": INTERSTITIAL_STEPS, "repeat_from": INTERSTITIAL_REPEAT_FROM},
    {"match": "BillingActivity", "steps": PAYWALL_STEPS, "repeat_from": PAYWALL_REPEAT_FROM},
]

DEFAULT_HOME_MATCH = "MainActivity"


def rule_for(activity: str, rules: list[dict]) -> dict | None:
    """First rule whose `match` appears in the focused activity name."""
    for rule in rules:
        if rule["match"] in activity:
            return rule
    return None


def perform_step(step: dict, xml_fn, run, sleep=None) -> str | None:
    """Carry out one step. Returns a label when something happened.

    A tap whose node is absent does nothing and reports None, so the driver can
    move on to the next step rather than stalling on a screen that skipped it.
    """
    if "language" in step:
        return pick_language(step["language"], xml_fn, run, sleep=sleep)
    if "wait" in step:
        if sleep:
            sleep(step["wait"])
        return f"wait {step['wait']}s"
    if "tap_close" in step:
        center = find_close_center(xml_fn())
        if not center:
            return None
        tap(*center, run=run)
        return "close"
    if "swipe" in step:
        swipe_left(run=run)
        return "swipe"
    if "key" in step:
        key_event(step["key"], run=run)
        return step["key"]
    target = step["tap"]
    center = find_node_center(xml_fn(), **target)
    if not center:
        return None
    tap(*center, run=run)
    return next(iter(target.values()))

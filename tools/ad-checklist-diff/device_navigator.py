"""Walk an app to its Home screen: poll the focused screen, act, repeat.

The navigation state machine only. `device_flow` says what to do on each
screen, `device_driver` owns launching and log capture.

Recognising screens by focused activity (rather than by pixels or by a fixed
sequence) is what lets one rule set serve both journeys: a first-open user
passes through language and onboarding screens that a returning user never
sees, and the loop simply never matches those rules on the second run.
"""
import time

from device_flow import DEFAULT_HOME_MATCH, DEFAULT_RULES, perform_step, rule_for
from device_ui import adb_run, focused_package_activity, screen_size, spam_tap, ui_xml

SPLASH_TAPS = 40
# Home placements (banner, native) request after the screen settles, and some
# non-`_high` fallbacks only fire once their `_high` sibling finishes.
DEFAULT_DWELL_SECONDS = 12
POLL_SECONDS = 2


def launch(package: str, run=adb_run) -> None:
    run(["shell", "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1"])


def wipe_app_data(package: str, run=adb_run) -> None:
    """`pm clear` -- destroys app data to recreate a first-open user."""
    run(["shell", "pm", "clear", package], timeout=120)


def force_stop(package: str, run=adb_run) -> None:
    """Cold-start the next launch.

    Without this the returning-user pass just resumes the Home screen left by
    the previous pass: no splash, no tester log dump, none of the placements
    that journey is supposed to exercise.
    """
    run(["shell", "am", "force-stop", package], timeout=60)


SPLASH_CHUNK = 8


def splash_logo_spam(
    tap_xy: tuple[int, int] | None, package: str | None = None, run=adb_run
) -> tuple[int, int]:
    """Spam the splash logo, stopping the moment the splash is gone.

    Tapping blind past the splash is how a run once ended up inside YouTube:
    an interstitial had appeared and the remaining taps landed on the ad. So
    the taps go in small bursts and stop as soon as focus leaves the app or an
    ad activity takes over.
    """
    if tap_xy is None:
        w, h = screen_size(run=run) or (1080, 2280)
        tap_xy = (w // 2, int(h * 0.44))
    for _ in range(0, SPLASH_TAPS, SPLASH_CHUNK):
        spam_tap(tap_xy[0], tap_xy[1], SPLASH_CHUNK, run=run)
        found = focused_package_activity(run=run)
        if not found:
            break
        pkg, activity = found
        if (package and pkg != package) or "AdActivity" in activity:
            break
    return tap_xy


def drive_to_home(
    *,
    package: str | None = None,
    home_match: str = DEFAULT_HOME_MATCH,
    rules: list[dict] | None = None,
    timeout: int = 240,
    dwell: int = DEFAULT_DWELL_SECONDS,
    xml_fn=None,
    run=adb_run,
    sleep=time.sleep,
) -> dict:
    """Poll the focused screen, perform its next step, stop at Home or timeout."""
    xml_fn = xml_fn or (lambda: ui_xml(run=run))
    rules = rules if rules is not None else DEFAULT_RULES

    visited: list[str] = []
    actions: list[str] = []
    # Step counter per *visit*, not per rule: the flow passes through two
    # separate language activities that share one rule, and comes back to the
    # interstitial a second time after the question screen. Keying by rule
    # would carry a spent counter into the next screen; keying by visit gives
    # every arrival its own fresh run through the steps.
    visits: dict[str, int] = {}
    progress: dict[tuple[str, int], int] = {}
    last_short = None
    deadline = time.monotonic() + timeout
    reached_home = False

    while time.monotonic() < deadline:
        found = focused_package_activity(run=run)
        focused_pkg, activity = found if found else ("", "")
        short = activity.rsplit(".", 1)[-1]
        if short and short != last_short:
            visits[short] = visits.get(short, 0) + 1
            visited.append(short)
            last_short = short

        # An ad tap can hand the device to another app entirely. That app's own
        # screens must never be driven, and its "MainActivity" must never be
        # mistaken for ours -- come back and carry on.
        if package and focused_pkg and focused_pkg != package:
            actions.append(f"{short}: ngoài app ({focused_pkg}) -- mở lại app")
            launch(package, run=run)
            sleep(POLL_SECONDS)
            continue

        if home_match in activity and (not package or focused_pkg == package):
            reached_home = True
            break

        rule = rule_for(activity, rules)
        if rule:
            key = (short, visits.get(short, 1))
            index = progress.get(key, 0)
            steps = rule["steps"]
            if index >= len(steps) and "repeat_from" in rule:
                # Ads and paywalls do not always yield on the first attempt --
                # the close control appears only after a countdown. Cycle the
                # closing steps instead of stranding the run on that screen.
                index = rule["repeat_from"]
            if index < len(steps):
                label = perform_step(steps[index], xml_fn, run, sleep=sleep)
                # A step whose node is absent still counts as consumed: the
                # screen simply skipped it (labels differ by remote config),
                # and retrying it forever would stall the run.
                progress[key] = index + 1
                if label:
                    actions.append(f"{short}: {label}")
        sleep(POLL_SECONDS)

    if reached_home:
        sleep(dwell)  # let Home's own placements request
    return {"reached_home": reached_home, "visited": visited, "actions": actions}



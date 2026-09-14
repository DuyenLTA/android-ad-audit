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

SPLASH_TAPS_PER_SPOT = 10
# Where the splash logo sits, as a fraction of screen height. It is a sweep
# rather than one point because the logo's height differs per app and a miss is
# silent: tapping the logo is what turns on the app's tester logging, and the
# single 0.44 this used to guess landed in the empty gap 254px BELOW Cast to
# TV's logo. Every FOR_TESTER line was lost, which in turn cost the checklist
# its only runtime evidence -- rows then fell back to APK-only reasoning and one
# fell through even that. Measured: a tap costs ~22ms on device, so covering the
# whole band is cheaper than being wrong once.
SPLASH_SPOT_FRACTIONS = (0.25, 0.33, 0.40, 0.47)
# The splash window only opens ~400ms after launch; tapping before it is drawn
# spends the first burst on the launcher.
SPLASH_APPEAR_SECONDS = 0.5
# Home placements (banner, native) request after the screen settles, and some
# non-`_high` fallbacks only fire once their `_high` sibling finishes.
DEFAULT_DWELL_SECONDS = 12
POLL_SECONDS = 2
# Polls with nothing left to try before calling the journey stuck. A screen only
# goes idle here when no rule matches it, or its rule ran out of steps and has no
# `repeat_from` -- the countdown case keeps performing steps, so it never idles
# and is never cut short. 15 polls is ~30s of a screen that changed nothing and
# offered nothing, against the 300s a stuck journey used to burn in full.
STUCK_POLLS = 15


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


def splash_spots(
    tap_xy: tuple[int, int] | None, run=adb_run
) -> list[tuple[int, int]]:
    """The points to try, centred horizontally, sweeping the logo band.

    An app whose splash does not follow the template can pin one point via the
    registry's `splash_tap`; then that point is the only one tried.
    """
    if tap_xy is not None:
        return [tap_xy]
    w, h = screen_size(run=run) or (1080, 2280)
    return [(w // 2, int(h * f)) for f in SPLASH_SPOT_FRACTIONS]


def splash_logo_spam(
    tap_xy: tuple[int, int] | None,
    package: str | None = None,
    run=adb_run,
    sleep=time.sleep,
) -> list[tuple[int, int]]:
    """Tap the splash logo to turn on tester logging, stopping when it is gone.

    Each spot gets its own burst rather than the taps being spread across the
    band: the gesture is a count of taps on the logo, so ten in a row on the
    right spot beats forty scattered over four.

    Tapping blind past the splash is how a run once ended up inside YouTube: an
    interstitial had appeared and the remaining taps landed on the ad. So the
    bursts stop as soon as focus is seen to be another app or an ad activity.

    Seen to be -- an unreadable focus is not one of those. `mCurrentFocus` reads
    `null` while the splash window is still being drawn, which is exactly when
    these bursts run, and treating that as "we left the app" stopped the sweep
    after its first spot. One spot is a guess again, the thing the sweep exists
    to stop being: that spot missed the logo, tester logging never came on, and
    the capture carried zero FOR_TESTER lines -- the whole runtime evidence for
    the ad rows. Driving the same four spots by hand, ignoring the null, turned
    it on and produced 27 of them.
    """
    sleep(SPLASH_APPEAR_SECONDS)
    spots = splash_spots(tap_xy, run=run)
    tapped = []
    for spot in spots:
        spam_tap(spot[0], spot[1], SPLASH_TAPS_PER_SPOT, run=run)
        tapped.append(spot)
        found = focused_package_activity(run=run)
        if not found:
            # Transitional, not a departure: keep sweeping the band.
            continue
        pkg, activity = found
        if (package and pkg != package) or "AdActivity" in activity:
            break
    return tapped


def drive_to_home(
    *,
    package: str | None = None,
    home_match: str = DEFAULT_HOME_MATCH,
    rules: list[dict] | None = None,
    timeout: int = 240,
    dwell: int = DEFAULT_DWELL_SECONDS,
    stuck_polls: int = STUCK_POLLS,
    xml_fn=None,
    run=adb_run,
    sleep=time.sleep,
    should_abandon=None,
) -> dict:
    """Poll the focused screen, perform its next step, stop at Home.

    Four ways out: Home, nothing left to try (`stuck`), the deadline, or
    `should_abandon` saying the journey is not worth finishing. The deadline is
    the backstop, not the plan -- a journey that cannot reach Home used to sit on
    a dead screen until the full timeout elapsed, which is pure waste and, worse,
    indistinguishable in the summary from a slow success.

    `should_abandon` is called once per poll and returns a reason, or None to
    carry on. It exists for facts that only the log can tell and that settle the
    whole run: an app announcing itself a dev build one second after launch means
    every screen after this one is being driven for a report nobody should read.
    """
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
    stopped = "timeout"
    idle = 0

    while time.monotonic() < deadline:
        if should_abandon:
            reason = should_abandon()
            if reason:
                actions.append(reason)
                stopped = "abandoned"
                break

        found = focused_package_activity(run=run)
        focused_pkg, activity = found if found else ("", "")
        short = activity.rsplit(".", 1)[-1]
        if short and short != last_short:
            visits[short] = visits.get(short, 0) + 1
            visited.append(short)
            last_short = short
            idle = 0  # a new screen is progress, whatever happens on it

        rule = rule_for(activity, rules)

        # An ad tap can hand the device to another app entirely. That app's own
        # screens must never be driven, and its "MainActivity" must never be
        # mistaken for ours -- come back and carry on.
        #
        # Exception: a screen whose rule is marked `system` is drawn by another
        # package *on behalf of* this app -- the runtime permission dialog. It
        # sits on top of our own activity, so relaunching does not dismiss it;
        # it just puts the dialog straight back, and the run loops there until
        # it times out. Those screens are handled instead of fled.
        if package and focused_pkg and focused_pkg != package and not (rule and rule.get("system")):
            actions.append(f"{short}: ngoài app ({focused_pkg}) -- mở lại app")
            launch(package, run=run)
            idle = 0  # relaunching is an act, and the next screen is unknown
            sleep(POLL_SECONDS)
            continue

        if home_match in activity and (not package or focused_pkg == package):
            reached_home = True
            stopped = "home"
            break

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
                idle = 0  # something was still worth trying on this screen
                if label:
                    actions.append(f"{short}: {label}")
                sleep(POLL_SECONDS)
                continue

        # Nothing matched this screen, or its steps are spent and it does not
        # ask to cycle. Waiting longer cannot change either fact.
        idle += 1
        if idle >= stuck_polls:
            actions.append(f"{short}: hết cách thử -- dừng sớm")
            stopped = "stuck"
            break
        sleep(POLL_SECONDS)

    if reached_home:
        sleep(dwell)  # let Home's own placements request
    return {
        "reached_home": reached_home,
        "stopped": stopped,
        "visited": visited,
        "actions": actions,
    }



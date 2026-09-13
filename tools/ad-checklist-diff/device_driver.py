"""Capture one audit's worth of logcat by driving the app, unattended.

A full audit needs **both** user journeys in one log, because they exercise
different placements:

- **new user** (`pm clear` first): splash -> language -> onboarding -> question
  -> interstitial -> paywall -> home. This is what produces the first-open (FO)
  placements.
- **returning user** (no wipe): splash -> question -> paywall -> home, with the
  resume / in-app placements instead.

Both passes append to the same capture file, so one run of the diff sees
everything. Navigation itself lives in `device_navigator`; the screen rules in
`device_flow`.

Measured facts this rests on:
- Launching with no taps yields **zero** `FOR_TESTER` lines; spamming the splash
  logo yields hundreds. Several checklist sections have no other source, so the
  spam step is mandatory.
- An interstitial's close control only appears after its countdown and is
  labelled in the ad creative's own language, so closing is retried rather than
  attempted once.
"""
import argparse
import subprocess
import sys

from device_flow import DEFAULT_HOME_MATCH
from collections.abc import Sequence

from device_navigator import drive_to_home, force_stop, launch, splash_logo_spam, wipe_app_data
from device_ui import adb_run
from console_encoding import use_utf8_console

PASS_NEW_USER = "new"
PASS_RETURNING = "old"
DEFAULT_PASSES = (PASS_NEW_USER, PASS_RETURNING)


def _adb(serial: str | None):
    def run(args, serial=serial, timeout=30):
        return adb_run(args, serial=serial, timeout=timeout)

    return run


def capture_pass(
    package: str,
    log_file,
    *,
    fresh: bool,
    serial: str | None = None,
    timeout: int = 300,
    home_match: str = DEFAULT_HOME_MATCH,
    tap_xy: tuple[int, int] | None = None,
) -> dict:
    """One journey, appended to an already-open capture file."""
    run = _adb(serial)
    if fresh:
        wipe_app_data(package, run=run)
    else:
        # Returning user still needs a cold start -- otherwise the app simply
        # resumes wherever the previous pass left it.
        force_stop(package, run=run)

    # `adb logcat` replays the whole ring buffer before it starts following, so
    # a second pass would otherwise re-append everything the first pass already
    # wrote: half the capture was a duplicate of itself, line numbers pointed at
    # two places at once, and neither pass could be read on its own.
    run(["logcat", "-c"])
    cmd = ["adb"] + (["-s", serial] if serial else []) + ["logcat"]
    proc = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT)
    try:
        launch(package, run=run)
        tapped = splash_logo_spam(tap_xy, package=package, run=run)
        result = drive_to_home(package=package, home_match=home_match, timeout=timeout, run=run)
    finally:
        proc.terminate()
        proc.wait(timeout=10)
    result["splash_tap"] = tapped
    return result


def capture_session(
    package: str,
    out_path: str,
    *,
    passes=DEFAULT_PASSES,
    serial: str | None = None,
    timeout: int = 300,
    home_match: str = DEFAULT_HOME_MATCH,
    tap_xy: tuple[int, int] | None = None,
    also_stop: Sequence[str] = (),
) -> list[dict]:
    """Run the requested journeys into one capture file.

    `adb logcat` is device-wide, so anything else still running writes into this
    app's capture. That is not hypothetical: an app left running after its own
    audit kept loading ads for two minutes into the next app's capture, and its
    ad unit IDs were then read as evidence about the wrong build. `also_stop`
    names the apps to silence first -- the other apps of this run -- and the app
    is stopped again on the way out so it cannot leak into whoever comes next.
    """
    run = _adb(serial)
    for other in also_stop:
        if other != package:
            force_stop(other, run=run)

    results = []
    with open(out_path, "w", encoding="utf-8") as log_file:
        for name in passes:
            fresh = name == PASS_NEW_USER
            if fresh:
                print(f"[{name}] pm clear {package} -- xoá dữ liệu app để tạo lại user mới")
            else:
                print(f"[{name}] mở lại app, không xoá dữ liệu")
            result = capture_pass(
                package,
                log_file,
                fresh=fresh,
                serial=serial,
                timeout=timeout,
                home_match=home_match,
                tap_xy=tap_xy,
            )
            result["pass"] = name
            results.append(result)
            print("  màn đã đi qua: " + " -> ".join(result["visited"]))
            for action in result["actions"]:
                print(f"    {action}")
            # Why a pass stopped changes what its silence in the log means, so
            # the summary says it rather than calling every failure a timeout.
            why = {
                "stuck": "KHÔNG (hết cách thử, dừng sớm)",
                "timeout": "KHÔNG (hết giờ)",
            }.get(result.get("stopped", "timeout"), "KHÔNG")
            print(f"  tới Home: {'có' if result['reached_home'] else why}")
    # Leaving it running is what contaminated the next app's capture.
    force_stop(package, run=run)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Tự mở app, đi tới Home cho cả luồng new user và old user, vừa capture logcat"
    )
    parser.add_argument("--package", required=True)
    parser.add_argument("--out", default="capture.log")
    parser.add_argument("--serial", help="adb serial, khi cắm nhiều máy")
    parser.add_argument(
        "--pass",
        dest="passes",
        action="append",
        choices=[PASS_NEW_USER, PASS_RETURNING],
        help="Chạy riêng một luồng. Mặc định chạy cả hai (new rồi old)",
    )
    parser.add_argument("--timeout", type=int, default=300, help="Giới hạn mỗi luồng, giây")
    parser.add_argument("--home-match", default=DEFAULT_HOME_MATCH)
    parser.add_argument("--tap", help="toạ độ spam logo dạng x,y (mặc định giữa màn)")
    args = parser.parse_args()

    tap_xy = None
    if args.tap:
        x, y = args.tap.split(",")
        tap_xy = (int(x), int(y))

    results = capture_session(
        args.package,
        args.out,
        passes=tuple(args.passes) if args.passes else DEFAULT_PASSES,
        serial=args.serial,
        timeout=args.timeout,
        home_match=args.home_match,
        tap_xy=tap_xy,
    )
    print(f"log: {args.out}")
    return 0 if all(r["reached_home"] for r in results) else 2


if __name__ == "__main__":
    use_utf8_console()
    sys.exit(main())

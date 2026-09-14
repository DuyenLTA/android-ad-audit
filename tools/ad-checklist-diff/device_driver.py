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
import os
import shutil
import subprocess
import tempfile
import time
import sys

from check_ads import DEFAULT_FILTERS
from device_flow import DEFAULT_HOME_MATCH
from device_navigator import drive_to_home, force_stop, launch, splash_logo_spam, wipe_app_data
from device_ui import adb_run

PASS_NEW_USER = "new"
PASS_RETURNING = "old"
DEFAULT_PASSES = (PASS_NEW_USER, PASS_RETURNING)

# Sitting on Home exists to let its own placements request. How long that takes
# was never measured -- 12 seconds was a round number. Measured on device, every
# trusted line arrived within 2.2s of reaching Home and nothing followed for the
# next 45. But that run came back "No fill" on every unit, which is the fastest
# an ad request can resolve; a run that actually fills will log later.
#
# So the constant is not lowered. The wait ends when the log goes quiet instead:
# short whenever the app is done, and still capped at the old 12s, so the worst
# case is exactly what it was before.
HOME_MIN_SECONDS = 3
HOME_QUIET_SECONDS = 4
HOME_DWELL_CAP = 12
HOME_POLL_SECONDS = 0.5


def wait_for_ad_quiet(
    path: str,
    *,
    minimum: float = HOME_MIN_SECONDS,
    quiet: float = HOME_QUIET_SECONDS,
    cap: float = HOME_DWELL_CAP,
    filters=DEFAULT_FILTERS,
    sleep=time.sleep,
    now=time.monotonic,
) -> float:
    """Stay on Home until its placements stop logging. Returns seconds waited.

    Only the lines the audit actually reads count as activity -- logcat never
    falls silent on its own, so watching the file grow would wait out the cap
    every time.
    """
    try:
        stream = open(path, encoding="utf-8", errors="replace")
    except OSError:
        # No capture file to watch: fall back to the fixed wait rather than
        # cutting Home's placements short.
        sleep(cap)
        return cap

    started = now()
    last_line_at = started
    with stream:
        stream.seek(0, os.SEEK_END)
        while True:
            elapsed = now() - started
            if elapsed >= cap:
                return elapsed
            if elapsed >= minimum and now() - last_line_at >= quiet:
                return elapsed
            if any(flt in line for line in stream.readlines() for flt in filters):
                last_line_at = now()
            sleep(HOME_POLL_SECONDS)


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
        # dwell=0: the wait on Home is done here instead, where the capture file
        # is in hand and can say when the app has actually finished requesting.
        result = drive_to_home(
            package=package, home_match=home_match, timeout=timeout, dwell=0, run=run
        )
        if result["reached_home"]:
            log_file.flush()
            path = getattr(log_file, "name", None)
            result["dwell_seconds"] = (
                round(wait_for_ad_quiet(path), 1) if path else HOME_DWELL_CAP
            )
    finally:
        # Một `adb logcat` sống sót vẫn giữ file descriptor và ghi tiếp vào file
        # capture hàng chục phút sau khi lượt chạy kết thúc -- lẫn cả log của app
        # khác. Audit đọc chính file đó, nên phải chắc chắn nó chết.
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
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
) -> list[dict]:
    """Run the requested journeys into one capture file."""
    results = []
    # Mỗi lượt ghi ra file tạm riêng, xong mới ghép vào `out_path`. Nếu lượt
    # trước bị kill và để lại logcat mồ côi, nó vẫn đang ghi vào file tạm cũ --
    # không chạm được vào file kết quả, nên capture này không bị lẫn.
    parts = []
    with tempfile.TemporaryDirectory(prefix="adcheck-capture-") as workdir:
        for index, name in enumerate(passes):
            part = os.path.join(workdir, f"{index}-{name}.log")
            parts.append(part)
            fresh = name == PASS_NEW_USER
            if fresh:
                print(f"[{name}] pm clear {package} -- xoá dữ liệu app để tạo lại user mới")
            else:
                print(f"[{name}] mở lại app, không xoá dữ liệu")
            with open(part, "w", encoding="utf-8") as log_file:
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
            reached = "có" if result["reached_home"] else "KHÔNG (timeout)"
            waited = result.get("dwell_seconds")
            note = f" -- đợi thêm {waited}s tới khi log ads im" if waited is not None else ""
            print(f"  tới Home: {reached}{note}")

        with open(out_path, "w", encoding="utf-8") as out:
            for part in parts:
                with open(part, encoding="utf-8", errors="replace") as chunk:
                    shutil.copyfileobj(chunk, out)
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
    sys.exit(main())

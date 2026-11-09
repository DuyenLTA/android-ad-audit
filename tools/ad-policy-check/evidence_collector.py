"""Drive an app splash -> Home with rc-check's driver and keep the policy evidence.

Driving is rc-check's `fo_flow.walk_to`, the same driver rc-check and its bot run
every day: a state machine over activity rules (`data/fo_flow.yaml`) that re-reads
the screen before every step. That matters here: tapping an ad mid-journey (to
test click handling) used to derail a linear step-by-step flow, while walk_to just
reads where it is and carries on. No per-app flow file is needed either.

Beside the driver this collector keeps:
  - every app screen walk_to reads: its UI dump + a screenshot (`chup` hook);
  - a screen recording of the whole journey (timing rules), see evidence_screenrecord;
  - the resumed activity sampled every 0.5s (ad open/close moments);
  - full logcat;
  - one tap per native / banner to see whether the click is handled, see evidence_click_probe;
  - after Home: HOME key -> wait -> reopen from the launcher, for the resume ad;
  - Home exploration (settings / utility screens / content / paywall), see evidence_home_explorer;
  - a test purchase + in-app cancel option + cancel on Play, see evidence_sub_purchase;
  - the shared device lock + a guard that stops when another session drives the phone.

Run with rc-check's venv (it provides the driver):
  <check_remote_config>/.venv/Scripts/python evidence_collector.py --package <pkg> --serial <serial>

Output: out/<package>/<run-id>/{frames/, video/, activities.jsonl, click-probes.jsonl,
logcat.txt, walk.json, meta.json}
"""
import argparse
import asyncio
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "ad-checklist-diff"))   # device_close_button (pure parsing)

from device_guard import RC_REPO, ForeignDriverError, foreign_package, hold_device  # noqa: E402

sys.path.insert(0, str(RC_REPO / "src"))
from rcr import device_app, fo_flow, ui_dump  # noqa: E402
from rcr.adb_client import AdbClient  # noqa: E402

from adb_sync import a_top_activity, adb, safe_dump, screencap_png, top_activity  # noqa: E402
from evidence_click_probe import ClickProber  # noqa: E402
from evidence_home_explorer import HomeExplorer  # noqa: E402
from evidence_sub_purchase import purchase_pass  # noqa: E402
from evidence_screenrecord import ScreenRecorder  # noqa: E402
from ui_nodes import is_fullscreen_ad_activity, parse_nodes  # noqa: E402
import re  # noqa: E402

TUTORIAL_RESUME_RE = re.compile(r"onboarding(?!.*question)", re.I)

OUT_ROOT = HERE / "out"
ACTIVITY_POLL_SECONDS = 0.5
WALK_TIMEOUT = 300
RESUME_AWAY_SECONDS = 6
RESUME_WATCH_DUMPS = 3
DUMP_REMOTE = "/sdcard/policy-dump.xml"


def _ms(t0: float) -> int:
    return int((time.monotonic() - t0) * 1000)


def _sample_activities(serial: str, t0: float, path: Path, stop: threading.Event) -> None:
    """Thread: write the resumed activity every time it changes."""
    last = None
    with path.open("a", encoding="utf-8") as f:     # append: a follow-up pass continues the same run
        while not stop.is_set():
            try:
                act = top_activity(serial)
            except Exception:  # one missed sample is fine; a dead sampler is not
                act = None
            if act and act != last:
                f.write(json.dumps({"t": _ms(t0), "activity": act}) + "\n")
                f.flush()
                last = act
            stop.wait(ACTIVITY_POLL_SECONDS)


def _dump_ui(serial: str) -> str:
    return safe_dump(serial, DUMP_REMOTE)


class Evidence:
    """The `chup(activity, xml)` hook walk_to calls on every app screen it reads."""

    def __init__(self, serial: str, package: str, frames: Path, t0: float, prober: ClickProber):
        self.serial, self.package, self.frames, self.t0, self.prober = serial, package, frames, t0, prober
        self.resume_tried = False

    def save(self, xml: str) -> None:
        if "<hierarchy" not in (xml or ""):
            return                    # a failed dump is not evidence
        ms = _ms(self.t0)
        png = screencap_png(self.serial)
        if png:
            (self.frames / f"{ms:07d}.png").write_bytes(png)
        (self.frames / f"{ms:07d}.xml").write_text(xml, encoding="utf-8")

    async def __call__(self, activity: str, xml: str) -> None:
        await asyncio.to_thread(self.save, xml)
        nodes = parse_nodes(xml)
        stranger = foreign_package({n["pkg"] for n in nodes}, self.package, self.prober.recently_tapped())
        if stranger:
            raise ForeignDriverError(
                f"màn hình đang là app {stranger}, không phải app đang check: có phiên khác lái chung máy")
        # walk_to names the activity without its package; the prober compares full names.
        full = activity if "/" in activity else f"{self.package}/{activity}"
        if not self.resume_tried and TUTORIAL_RESUME_RE.search(full):
            self.resume_tried = True
            try:
                await _tutorial_resume_trial(self.serial, self.package, self.prober, self.frames.parent, self.t0)
            except Exception as exc:  # best effort; driving must go on
                print(f"[resume] bỏ qua: {exc}")
            return                         # back on the same Onboarding screen; no ad probe on this read
        try:
            await self.prober.maybe_probe(full, nodes, xml)
        except Exception as exc:  # probing is best effort; driving must go on
            print(f"[probe] bỏ qua: {exc}")


def _hook_fullscreen_probe(prober: ClickProber, serial: str):
    """walk_to never calls `chup` on a full-screen ad, so watch its UI dumps instead.

    fo_flow looks `ui_dump.dump` up at call time; wrapping it lets the prober see every
    dump the driver takes while an interstitial is up, tap its CTA once (from the 2nd
    full-screen ad on, see evidence_click_probe), and hand the driver a fresh dump of
    wherever the phone is after the trip.
    """
    original = ui_dump.dump

    async def dump(client, serial_arg: str) -> str:
        xml = await original(client, serial_arg)
        try:
            activity = await a_top_activity(serial)
            from ui_nodes import is_fullscreen_ad_activity
            if is_fullscreen_ad_activity(activity):
                if await prober.maybe_probe(activity, parse_nodes(xml), xml):
                    xml = await original(client, serial_arg)
            else:
                prober.in_fullscreen = False
        except Exception as exc:  # probing is best effort; the driver's dump must still return
            print(f"[probe inter] bỏ qua: {exc}")
        return xml

    ui_dump.dump = dump
    return original


async def _tutorial_resume_trial(serial: str, package: str, prober: ClickProber, out_dir: Path, t0: float) -> None:
    """Resume ads show only inside the tutorial (Language / Onboarding), never on Home (rule QA settled):
    hide the app on the first Onboarding screen, reopen it from the launcher, and if a resume ad shows,
    let the recording see it over the app, then tap it once (resume click rule) and close it."""
    screen = top_activity(serial) or ""
    adb(serial, "shell", "input", "keyevent", "KEYCODE_HOME")
    await asyncio.sleep(RESUME_AWAY_SECONDS)
    adb(serial, "shell", "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1")
    ad = None
    for _ in range(16):
        await asyncio.sleep(0.5)
        act = await a_top_activity(serial) or ""
        if is_fullscreen_ad_activity(act):
            ad = act
            break
    if ad:
        await asyncio.sleep(4)            # several seconds of the ad over the app for the background rule
        nodes = parse_nodes(await asyncio.to_thread(_dump_ui, serial))
        await prober.tap_fullscreen("resume", ad, nodes)
        await prober._close_fullscreen_with_back()
    with (out_dir / "resume-trials.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({"t": _ms(t0), "screen": screen, "ad": ad}, ensure_ascii=False) + "\n")


async def _resume_pass(client, serial: str, package: str, ev: Evidence) -> None:
    """HOME -> wait -> reopen from the launcher (not Recents), then look for the resume ad."""
    adb(serial, "shell", "input", "keyevent", "KEYCODE_HOME")
    await asyncio.sleep(RESUME_AWAY_SECONDS)
    await device_app.launch(client, serial, package)
    for _ in range(RESUME_WATCH_DUMPS):
        await asyncio.sleep(1.5)
        await asyncio.to_thread(ev.save, await asyncio.to_thread(_dump_ui, serial))


async def collect(package: str, serial: str, fresh: bool, buy_sub: bool = True, keep_session: bool = False) -> Path:
    out_dir = OUT_ROOT / package / time.strftime("%y%m%d-%H%M%S")
    frames = out_dir / "frames"
    frames.mkdir(parents=True, exist_ok=True)
    client = AdbClient()
    width, height = await device_app.screen_size(client, serial)
    density = adb(serial, "shell", "wm", "density").strip().split()[-1]
    t0 = time.monotonic()

    # keep_session: the tester picked an ad source in Ad Inspector (shake); that choice lives only in the
    # running process, so neither force-stop nor pm clear may touch the app.
    if not keep_session:
        await device_app.force_stop(client, serial, package)
        if fresh:
            adb(serial, "shell", "pm", "clear", package)
    # The app's own heads-up notification ("daily lesson") drops over the top bar and swallows taps on
    # Next / Continue; mute heads-up for the run, restore the tester's setting afterwards.
    heads_up = adb(serial, "shell", "settings", "get", "global", "heads_up_notifications_enabled").strip()
    adb(serial, "shell", "settings", "put", "global", "heads_up_notifications_enabled", "0")
    adb(serial, "logcat", "-c")
    stop = threading.Event()
    sampler = threading.Thread(target=_sample_activities, args=(serial, t0, out_dir / "activities.jsonl", stop),
                               daemon=True)
    recorder = ScreenRecorder(serial, out_dir, t0)
    prober = ClickProber(serial, package, (width, height), out_dir, t0)
    ev = Evidence(serial, package, frames, t0, prober)
    trail: list[str] = []
    log_file = (out_dir / "logcat.txt").open("w", encoding="utf-8", errors="replace")
    logcat = subprocess.Popen(["adb", "-s", serial, "logcat", "-v", "monotonic"], stdout=log_file,
                              stderr=subprocess.STDOUT)
    sampler.start()
    recorder.start()
    walk, error = {}, None
    original_dump = _hook_fullscreen_probe(prober, serial)
    try:
        await device_app.launch(client, serial, package)
        walk = await fo_flow.walk_to(client, serial, package, "", timeout=WALK_TIMEOUT,
                                     log_fn=trail.append, chup=ev)
        if walk.get("reached"):
            await _resume_pass(client, serial, package, ev)
            explorer = HomeExplorer(serial, package, ev, out_dir)
            explored = await explorer.explore()
            if buy_sub and explored.get("paywall"):
                await purchase_pass(explorer, out_dir)
    except Exception as exc:  # keep whatever evidence exists; say why it stopped
        error = f"{type(exc).__name__}: {exc}"
    except BaseException:             # Ctrl+C / cancel: still leave a gradable run behind
        error = error or "interrupted"
        raise
    finally:
        ui_dump.dump = original_dump
        adb(serial, "shell", "settings", "put", "global", "heads_up_notifications_enabled",
            heads_up if heads_up in ("0", "1") else "1")
        stop.set()
        segments = []
        # Each cleanup step on its own: one failing (a pull timing out) must not leave adb logcat
        # running or the run without meta.json.
        for step in (lambda: segments.extend(recorder.stop()), logcat.terminate,
                     lambda: logcat.wait(timeout=10), log_file.close, lambda: sampler.join(timeout=5)):
            try:
                step()
            except Exception:
                if step is not None:
                    try:
                        logcat.kill()
                    except Exception:
                        pass
        _write_meta(out_dir, package, serial, width, height, density, fresh, error, walk, trail, segments, frames)
    return out_dir


def _write_meta(out_dir, package, serial, width, height, density, fresh, error, walk, trail, segments, frames):

    (out_dir / "walk.json").write_text(json.dumps({"walk": walk, "log": trail}, ensure_ascii=False, indent=2,
                                                  default=str), encoding="utf-8")
    meta = {
        "package": package, "serial": serial, "screen_px": [width, height], "density_dpi": int(density),
        "fresh": fresh, "error": error, "reached_home": bool(walk.get("reached")),
        "stopped_at": walk.get("screen") or walk.get("activity"),
        "video_segments": segments, "frames": len(list(frames.glob("*.xml"))),
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


SUB_TEST_LIFETIME_SECONDS = 40 * 60   # weekly test sub: 6 renewals x 5 min, plus margin


def active_test_sub(package: str) -> str | None:
    """A test sub bought by an earlier run and not cancelled keeps the app premium (no ads), and
    `pm clear` does not remove it: every ad rule would come out empty. Say so instead of running."""
    for buy in sorted((OUT_ROOT / package).glob("*/purchase.json"), reverse=True)[:3]:
        rec = json.loads(buy.read_text(encoding="utf-8"))
        bought = rec.get("purchased_at") or buy.stat().st_mtime
        if rec.get("purchased") and not rec.get("cancelled") and time.time() - bought < SUB_TEST_LIFETIME_SECONDS:
            mins = int((SUB_TEST_LIFETIME_SECONDS - (time.time() - bought)) / 60) + 1
            return f"lượt {buy.parent.name} đã mua sub test và chưa huỷ được — app đang Pro, chờ ~{mins} phút"
    return None


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Lái app splash -> Home bằng trình lái rc-check, gom bằng chứng policy ads")
    ap.add_argument("--package", required=True)
    ap.add_argument("--serial", required=True)
    ap.add_argument("--no-sub", action="store_true", help="không chạy lượt mua sub")
    ap.add_argument("--no-fresh", action="store_true", help="không pm clear (luồng user cũ)")
    ap.add_argument("--keep-session", action="store_true",
                    help="không force-stop, không pm clear: giữ nguồn ad đã chọn trong Ad Inspector (lắc máy)")
    args = ap.parse_args()
    busy_sub = active_test_sub(args.package)
    if busy_sub:
        print(f"Dừng: {busy_sub}.")
        return 5
    try:
        with hold_device(args.serial):
            out = asyncio.run(collect(args.package, args.serial, fresh=not (args.no_fresh or args.keep_session),
                                     buy_sub=not args.no_sub, keep_session=args.keep_session))
    except BlockingIOError as exc:
        print(f"Dừng: {exc}. Chờ lượt đó xong rồi chạy lại.")
        return 3
    print(out)
    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    if meta["error"]:
        print(f"Lượt dừng giữa chừng: {meta['error']}")
        return 4
    print("Tới Home" if meta["reached_home"] else f"Không tới Home, dừng ở {meta['stopped_at']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

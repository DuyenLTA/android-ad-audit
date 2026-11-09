"""Follow-up pass on an existing run: settle what the main pass left BLOCKED, into the same run dir.

The main pass (evidence_collector) drives splash -> Home once; when it could not reach a screen a
rule needs (Settings / utility pages, an AI result, the paywall, a purchase), this pass opens the
app again where it already is (no `pm clear`, FO already done), runs the Home exploration and the
purchase again, and appends its evidence to the same run. Times continue after the run's last
event, so checkers read old and new evidence as one run.

  <check_remote_config>/.venv/Scripts/python evidence_followup.py <run-dir> --serial <serial> [--no-sub]
"""
import argparse
import asyncio
import json
import sys
import threading
import time
from pathlib import Path

import evidence_collector as ec  # sets up sys.path for rc-check's driver
from adb_sync import adb
from evidence_click_probe import ClickProber
from evidence_home_explorer import HomeExplorer
from evidence_sub_purchase import purchase_pass

GAP_MS = 60_000


def _last_ms(run_dir: Path) -> int:
    """Latest time any evidence of the run carries."""
    times = [int(p.stem) for p in (run_dir / "frames").glob("*.xml")]
    for name in ("activities.jsonl", "click-probes.jsonl", "utility-visits.jsonl"):
        p = run_dir / name
        if p.exists():
            times += [json.loads(x)["t"] for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
    return max(times, default=0)


async def follow_up(run_dir: Path, serial: str, buy_sub: bool) -> dict:
    meta = json.loads((run_dir / "meta.json").read_text(encoding="utf-8"))
    package = meta["package"]
    width, height = meta["screen_px"]
    # Continue the run's clock: new evidence sorts after the old one.
    t0 = time.monotonic() - (_last_ms(run_dir) + GAP_MS) / 1000
    stop = threading.Event()
    sampler = threading.Thread(target=ec._sample_activities, args=(serial, t0, run_dir / "activities.jsonl", stop),
                               daemon=True)
    prober = ClickProber(serial, package, (width, height), run_dir, t0)
    ev = ec.Evidence(serial, package, run_dir / "frames", t0, prober)
    ev.resume_tried = True                 # the resume trial belongs to the tutorial, done in the main pass
    sampler.start()
    done: dict = {}
    try:
        adb(serial, "shell", "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1")
        await asyncio.sleep(6)
        explorer = HomeExplorer(serial, package, ev, run_dir)
        await explorer.close_fullscreen_ad()       # an ad left open (BACK does not close new-SDK ads)
        done = await explorer.explore()
        if buy_sub and done.get("paywall") and not json.loads(
                (run_dir / "purchase.json").read_text(encoding="utf-8") if (run_dir / "purchase.json").exists()
                else "{}").get("purchased"):
            await purchase_pass(explorer, run_dir)
    finally:
        stop.set()
        sampler.join(timeout=5)
    meta.setdefault("follow_ups", []).append({"at": time.strftime("%Y-%m-%d %H:%M:%S"), "done": done})
    (run_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return done


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--serial", required=True)
    ap.add_argument("--no-sub", action="store_true", help="không mua sub")
    args = ap.parse_args()
    try:
        with ec.hold_device(args.serial):
            done = asyncio.run(follow_up(args.run_dir, args.serial, not args.no_sub))
    except BlockingIOError as exc:
        print(f"Dừng: {exc}. Chờ lượt đó xong rồi chạy lại.")
        return 3
    print(json.dumps(done, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Record the screen for the whole journey, in chained segments.

UI dumps take ~2s each, far too coarse for the timing rules (loading before an
interstitial, placeholder visible on entry, close button within 15s). A low-res
screen recording runs beside everything else, costs nothing on the host, and
gives a frame-accurate timeline afterwards.

`screenrecord` stops itself at --time-limit (max 180s), so segments are chained.
Each segment's start is noted on the same monotonic clock as the rest of the
evidence; adb start latency makes that accurate to a few hundred ms, which the
checkers account for.
"""
import json
import subprocess
import threading
import time
from pathlib import Path

SEGMENT_SECONDS = 170
SIZE = "540x1200"
BIT_RATE = "2000000"
REMOTE_DIR = "/sdcard"


class ScreenRecorder:
    def __init__(self, serial: str | None, out_dir: Path, t0: float):
        self.serial = serial
        self.out_dir = out_dir / "video"
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.t0 = t0
        self.segments: list[dict] = []
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._proc: subprocess.Popen | None = None
        self.error = ""

    def _adb(self) -> list[str]:
        return ["adb"] + (["-s", self.serial] if self.serial else [])

    def _loop(self) -> None:
        index = 0
        quick_fails = 0
        while not self._stop.is_set():
            remote = f"{REMOTE_DIR}/policy-rec-{index}.mp4"
            cmd = self._adb() + ["shell", "screenrecord", "--size", SIZE, "--bit-rate", BIT_RATE,
                                 "--time-limit", str(SEGMENT_SECONDS), remote]
            start_ms = int((time.monotonic() - self.t0) * 1000)
            self._proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.segments.append({"index": index, "remote": remote, "start_ms": start_ms})
            while self._proc.poll() is None and not self._stop.is_set():
                time.sleep(0.2)
            index += 1
            lived = int((time.monotonic() - self.t0) * 1000) - start_ms
            if not self._stop.is_set() and lived < 5000:
                quick_fails += 1
                if quick_fails >= 3:      # encoder refuses the size / device gone: stop, say so
                    self.error = "screenrecord thoát ngay 3 lần — không có video"
                    return
                time.sleep(2)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> list[dict]:
        """Stop cleanly (SIGINT finalizes the mp4), pull every segment, remove them from the device."""
        self._stop.set()
        subprocess.run(self._adb() + ["shell", "pkill", "-INT", "screenrecord"], capture_output=True, timeout=15)
        if self._proc is not None:
            try:
                self._proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        self._thread.join(timeout=20)
        time.sleep(1.0)  # let the device flush the moov atom before pulling
        for seg in self.segments:
            local = self.out_dir / f"segment-{seg['index']}.mp4"
            subprocess.run(self._adb() + ["pull", seg["remote"], str(local)], capture_output=True, timeout=120)
            subprocess.run(self._adb() + ["shell", "rm", "-f", seg["remote"]], capture_output=True, timeout=15)
            seg["file"] = local.name if local.exists() else None
        (self.out_dir / "segments.json").write_text(json.dumps(self.segments, indent=2), encoding="utf-8")
        return self.segments

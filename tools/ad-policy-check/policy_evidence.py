"""Load one evidence run (written by evidence_collector) into something checkers can query.

A checker never touches the device: it reads this object, so it can be re-run on an
old run and unit-tested on a saved one.
"""
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from ui_nodes import is_fullscreen_ad_activity, native_parts, parse_nodes

LAUNCHER_MARKERS = ("nexuslauncher", "launcher3", ".launcher")
BROWSER_PACKAGES = ("com.android.chrome", "com.android.vending", "com.google.android.youtube")


@dataclass
class Frame:
    t: int
    xml: Path
    png: Path | None
    activity: str
    nodes: list[dict]

    @property
    def native(self) -> dict:
        return native_parts(self.nodes)

    def texts(self) -> list[str]:
        return [n["text"] for n in self.nodes if n["text"].strip()]


@dataclass
class Episode:
    """One full-screen ad on screen: from its AdActivity appearing to the app coming back."""
    start: int
    end: int | None
    before: str
    after: str
    index: int


@dataclass
class Run:
    root: Path
    meta: dict
    activities: list[dict]
    probes: list[dict]
    frames: list[Frame] = field(default_factory=list)

    def jsonl(self, name: str) -> list[dict]:
        p = self.root / name
        if not p.exists():
            return []
        return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]

    def json(self, name: str) -> dict:
        p = self.root / name
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

    def frame_near(self, t: int) -> "Frame | None":
        later = [f for f in self.frames if f.t >= t]
        return later[0] if later else None

    def rel(self, p: Path | None) -> str:
        """Evidence path as the report links it: relative to the run, or as given when outside it."""
        if not p:
            return ""
        try:
            return str(Path(p).relative_to(self.root)).replace("\\", "/")
        except ValueError:
            return str(p).replace("\\", "/")

    def activity_at(self, t: int) -> str:
        cur = ""
        for a in self.activities:
            if a["t"] > t:
                break
            cur = a["activity"]
        return cur

    def app_activities(self) -> list[dict]:
        pkg = self.meta["package"] + "/"
        return [a for a in self.activities if a["activity"].startswith(pkg)]

    def episodes(self) -> list[Episode]:
        """Full-screen ad episodes; trips to Chrome/Play opened by our own tap stay inside the episode."""
        out: list[Episode] = []
        cur: Episode | None = None
        last_app = ""
        for a in self.activities:
            act = a["activity"]
            if is_fullscreen_ad_activity(act):
                if cur is None:
                    cur = Episode(start=a["t"], end=None, before=last_app, after="", index=len(out) + 1)
                continue
            if cur is not None and act.split("/")[0] in BROWSER_PACKAGES:
                continue
            if cur is not None:
                cur.end, cur.after = a["t"], act
                out.append(cur)
                cur = None
            if act.startswith(self.meta["package"] + "/"):
                last_app = act
        if cur is not None:
            out.append(cur)
        return out

    def resume_window(self) -> list[dict]:
        """Activities of the resume pass: from the launcher (HOME pressed on Home) until 10s after the
        app is back. Later screens belong to the Home exploration, not to the resume."""
        pkg = self.meta["package"] + "/"
        for i, a in enumerate(self.activities):
            if i <= 2 or not any(m in a["activity"] for m in LAUNCHER_MARKERS):
                continue
            back = next((x for x in self.activities[i + 1:] if x["activity"].startswith(pkg)), None)
            limit = (back["t"] if back else a["t"]) + 10000
            return [x for x in self.activities[i:] if x["t"] <= limit]
        return []

    def video_sheet(self, start_ms: int, end_ms: int, name: str, fps: float = 1.0, cols: int = 6) -> Path | None:
        """Contact sheet of the screen recording between two run times (one tile per 1/fps s)."""
        try:
            import imageio_ffmpeg
        except ImportError:
            return None
        segs = [x for x in self.meta.get("video_segments") or [] if x.get("file")]
        # The segment that was recording at start_ms (segments chain every ~170s).
        covering = [x for x in segs if x["start_ms"] <= start_ms] or segs[:1]
        for seg in covering[-1:]:
            offset = max(0.0, (start_ms - seg["start_ms"]) / 1000)
            dur = max(1.0, (end_ms - start_ms) / 1000)
            tiles = max(1, int(dur * fps))
            rows = (tiles + cols - 1) // cols
            out = self.root / "sheets" / f"{name}.png"
            out.parent.mkdir(exist_ok=True)
            cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-loglevel", "error", "-y", "-ss", f"{offset:.2f}",
                   "-t", f"{dur:.2f}", "-i", str(self.root / "video" / seg["file"]),
                   "-vf", f"fps={fps},scale=270:-1,drawtext=text='%{{pts\\:hms}}':x=4:y=4:fontsize=18:"
                          f"fontcolor=yellow:box=1:boxcolor=black,tile={cols}x{rows}", "-frames:v", "1", str(out)]
            r = subprocess.run(cmd, capture_output=True, timeout=120)
            if r.returncode != 0:  # drawtext needs a font; retry without the timestamp overlay
                cmd[cmd.index("-vf") + 1] = f"fps={fps},scale=270:-1,tile={cols}x{rows}"
                subprocess.run(cmd, capture_output=True, timeout=120)
            return out if out.exists() else None
        return None


def load_run(root: Path) -> Run:
    root = Path(root)
    meta = json.loads((root / "meta.json").read_text(encoding="utf-8"))

    def jsonl(name: str) -> list[dict]:
        p = root / name
        if not p.exists():
            return []
        return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]

    run = Run(root=root, meta=meta, activities=jsonl("activities.jsonl"), probes=jsonl("click-probes.jsonl"))
    for xml in sorted((root / "frames").glob("*.xml")):
        t = int(xml.stem)
        png = xml.with_suffix(".png")
        run.frames.append(Frame(t=t, xml=xml, png=png if png.exists() else None,
                                activity=run.activity_at(t),
                                nodes=parse_nodes(xml.read_text(encoding="utf-8"))))
    return run

"""Build the policy report page (one self-contained HTML) from a graded run.

  python policy_report.py <run-dir> --app "Fravix 2.9.0 (release)" [--notes notes.json] [--out page.html]

Layout follows the rc-check report the testers settled on: counters first, then what
needs a person, then every rule grouped by ad format with its evidence. Images are
embedded as small JPEGs so the page stands alone.
"""
import argparse
import base64
import html
import json
import subprocess
import sys
from pathlib import Path

STATUS = {  # label, css class, order in the "needs attention" block
    "FAIL": ("FAIL", "fail", 0), "CAN_XEM": ("Cần xem", "look", 1), "BLOCKED": ("BLOCKED", "blocked", 2),
    "PASS": ("PASS", "pass", 3), "NA": ("N/A", "na", 4),
}
GROUPS = [("inter", "Interstitial"), ("resume", "Resume (App open)"), ("native", "Native"),
          ("banner_native", "Native + Banner"), ("banner", "Banner"), ("any", "Mọi loại ad"),
          ("reward", "Reward"), ("app", "App"), ("sub", "Gói mua (Sub / Lifetime)"), ("", "Rule mới chưa có checker")]
TEMPLATE = Path(__file__).resolve().parent / "policy_report_template.html"


def _thumb(path: Path, width: int) -> str:
    """JPEG data URI of an evidence image, scaled down; empty when it cannot be made."""
    try:
        import imageio_ffmpeg
        jpg = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-loglevel", "error", "-i", str(path),
                              "-vf", f"scale={width}:-1", "-q:v", "5", "-f", "image2pipe", "-vcodec", "mjpeg", "-"],
                             capture_output=True, timeout=60).stdout
    except Exception:
        return ""
    return "data:image/jpeg;base64," + base64.b64encode(jpg).decode() if jpg else ""


def _evidence(run_dir: Path, rel_paths: list[str], cache: dict) -> str:
    imgs, files = [], []
    for rel in rel_paths:
        p = run_dir / rel
        if p.suffix.lower() == ".png" and p.exists():
            if rel not in cache:
                cache[rel] = _thumb(p, 900 if rel.startswith("sheets/") else 300)
            if cache[rel]:
                cls = "sheet" if rel.startswith("sheets/") else "shot"
                imgs.append(f'<figure class="{cls}"><img src="{cache[rel]}" alt="{html.escape(rel)}" loading="lazy">'
                            f'<figcaption>{html.escape(rel)}</figcaption></figure>')
                continue
        files.append(f"<code>{html.escape(rel)}</code>")
    out = ""
    if imgs:
        out += f'<div class="ev">{"".join(imgs)}</div>'
    if files:
        out += f'<p class="files">Nguồn: {", ".join(files)}</p>'
    return out


def _row(r: dict, run_dir: Path, cache: dict) -> str:
    label, cls, _ = STATUS[r["status"]]
    rules = r["rules"]
    title = html.escape(rules[0]["text"]) if rules else html.escape(r["checker"])
    refs = " · ".join(f"{html.escape(x['tab'])} #{html.escape(x['no'] if not x['no'].startswith('h') else '–')}"
                      for x in rules)
    others = "".join(f"<li>{html.escape(x['text'])}</li>" for x in rules[1:] if x["text"] != rules[0]["text"])
    judged = '<span class="by">Claude chấm trên ảnh</span>' if r.get("judged_by") else ""
    body = (f'<p class="reason">{html.escape(r["reason"])} {judged}</p>'
            + (f'<ul class="also">{others}</ul>' if others else "")
            + _evidence(run_dir, r.get("evidence") or [], cache))
    return (f'<details class="rule" data-status="{cls}"><summary><span class="pill {cls}">{label}</span>'
            f'<span class="t">{title}</span><span class="refs">{refs}</span></summary>{body}</details>')


def build(run_dir: Path, app: str, notes: list[dict], title: str) -> str:
    data = json.loads((run_dir / "results.json").read_text(encoding="utf-8"))
    results, meta, cache = data["results"], data["meta"], {}
    counts = {k: sum(1 for r in results if r["status"] == k) for k in STATUS}
    tiles = "".join(f'<button class="tile {STATUS[k][1]}" data-filter="{STATUS[k][1]}" type="button">'
                    f'<b>{counts[k]}</b><span>{STATUS[k][0]}</span></button>' for k in STATUS)
    attention = sorted((r for r in results if r["status"] in ("FAIL", "CAN_XEM", "BLOCKED")),
                       key=lambda r: STATUS[r["status"]][2])
    att_rows = "".join(f'<li><span class="pill {STATUS[r["status"]][1]}">{STATUS[r["status"]][0]}</span> '
                       f'{html.escape(r["rules"][0]["text"][:110] if r["rules"] else r["checker"])}'
                       f'<small>{html.escape(r["reason"])}</small></li>' for r in attention)
    run_state = []
    if meta.get("error") or not meta.get("reached_home"):
        run_state.append(f"Lượt dừng sớm: {meta.get('error') or 'không tới Home, dừng ở ' + str(meta.get('stopped_at'))}"
                         " — các rule chưa tới được là BLOCKED.")
    run_state += data.get("registry_warnings") or []
    notes = [{"title": "Lưu ý về lượt chạy", "detail": x} for x in run_state] + notes
    note_rows = "".join(f'<li><b>{html.escape(n["title"])}</b><small>{html.escape(n["detail"])}</small></li>' for n in notes)
    groups = ""
    for key, name in GROUPS:
        rows = [r for r in results if r["placement"] == key]
        if rows:
            rows.sort(key=lambda r: STATUS[r["status"]][2])
            groups += f'<section class="group"><h2>{name} <small>{len(rows)} rule</small></h2>' \
                      + "".join(_row(r, run_dir, cache) for r in rows) + "</section>"
    acts = [json.loads(line) for line in (run_dir / "activities.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()]
    steps = [a["activity"].rsplit(".", 1)[-1].replace("VslTemplate4", "") for a in acts
             if meta["package"] in a["activity"] or "chrome" in a["activity"]]
    journey = " → ".join(x for i, x in enumerate(steps) if i == 0 or x != steps[i - 1])
    page = TEMPLATE.read_text(encoding="utf-8")
    for k, v in {"{{TITLE}}": html.escape(title), "{{APP}}": html.escape(app), "{{PKG}}": html.escape(meta["package"]),
                 "{{DEVICE}}": html.escape(meta["serial"]), "{{RUN}}": html.escape(data["run"]),
                 "{{TILES}}": tiles, "{{ATTENTION}}": att_rows or "<li>Không có rule nào cần người xem.</li>",
                 "{{NOTES}}": note_rows, "{{NOTES_HIDDEN}}": "" if notes else "hidden",
                 "{{JOURNEY}}": html.escape(journey), "{{GROUPS}}": groups}.items():
        page = page.replace(k, v)
    return page


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--app", required=True, help="tên app + version hiện trên report")
    ap.add_argument("--title", required=True, help="tên trang (tab / gallery), vd 'Policy Fravix 2.9.0'")
    ap.add_argument("--notes", type=Path, help="JSON [{title, detail}] ghi nhận ngoài sheet")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    notes = json.loads(args.notes.read_text(encoding="utf-8")) if args.notes else []
    out = args.out or args.run_dir / "policy-report.html"
    out.write_text(build(args.run_dir, args.app, notes, args.title), encoding="utf-8")
    print(f"{out} ({out.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

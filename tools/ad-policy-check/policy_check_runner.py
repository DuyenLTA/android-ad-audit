"""Grade one evidence run against the live policy sheet.

  python policy_check_runner.py <run-dir>
      -> <run-dir>/results.json      one entry per checker (status, reason, evidence, rules)
      -> <run-dir>/visual-queue.json entries Claude must judge by looking at the images
  python policy_check_runner.py <run-dir> --visual <verdicts.json>
      -> merges Claude's verdicts {checker_id: {"status": "PASS|FAIL|CAN_XEM", "reason": "..."}}

Checkers never guess: anything not measurable from the evidence is CAN_XEM (with
what to look at), BLOCKED (the run did not create the condition) or NA (the app
has no such thing in this journey).
"""
import argparse
import json
import sys
from pathlib import Path

from checkers_fullscreen_resume import CHECKERS as FULLSCREEN
from checkers_native_banner import CHECKERS as NATIVE
from checkers_reward_app_sub import CHECKERS as APP_SUB
from policy_evidence import load_run
from policy_registry import build_registry, load_checker_map
from policy_source import fetch_policy_rules

ALL = {**FULLSCREEN, **NATIVE, **APP_SUB}
STATUSES = ("PASS", "FAIL", "CAN_XEM", "BLOCKED", "NA")


def mark_off_sub(results: list[dict], why: str) -> None:
    """App ships without subscriptions (plan tuần "Off subs"): the Sub rules do not apply, they are not
    blocked. A paywall that showed anyway still gets graded — that contradiction is worth a look."""
    for r in results:
        if r["checker"].startswith("sub_") and r["status"] == "BLOCKED":
            r["status"], r["reason"] = "NA", f"app không bán sub ({why}) — {r['reason']}"


def grade(run_dir: Path, off_sub: str | None = None) -> dict:
    checker_map = load_checker_map()
    reg = build_registry(fetch_policy_rules(checker_map["tabs"]), checker_map)
    run = load_run(run_dir)
    results = []
    for c in reg["checkers"]:
        if c["kind"] == "ios_only":
            continue                  # the tool checks Android only: iOS rules are skipped, not graded N/A
        fn = ALL.get(c["id"])
        if fn is None:
            res = {"status": "CAN_XEM", "reason": "chưa có code chấm cho checker này — chấm tay", "evidence": []}
        else:
            try:
                res = fn(run, c.get("params") or {})
            except Exception as exc:  # one broken checker must not hide the others
                res = {"status": "CAN_XEM", "reason": f"checker lỗi ({type(exc).__name__}: {exc}) — chấm tay",
                       "evidence": []}
        results.append({"checker": c["id"], "kind": c["kind"], "placement": c["placement"],
                        "rules": [{"tab": r["tab"], "no": r["no"], "group": r["group"], "text": r["text"],
                                   "good_example": r["good_example"], "bad_example": r["bad_example"]}
                                  for r in c["rule_objs"]], **res})
    for r in reg["unmapped"]:
        results.append({"checker": f"unmapped-{r['tab']}-{r['no']}", "kind": "manual", "placement": "",
                        "rules": [r], "status": "CAN_XEM", "reason": "rule mới trong sheet, chưa có checker — chấm tay",
                        "evidence": []})
    # A run that stopped early has not looked at most of the app: "not applicable" would read as clean.
    if run.meta.get("error") or not run.meta.get("reached_home"):
        why = run.meta.get("error") or f"không tới được Home (dừng ở {run.meta.get('stopped_at')})"
        for r in results:
            if r["status"] == "NA":
                r["status"], r["reason"] = "BLOCKED", f"lượt dừng sớm ({why}) — {r['reason']}"
    if off_sub:
        mark_off_sub(results, off_sub)
    drifted = {d["checker"] for d in reg["drifted"]}
    for r in results:
        if r["checker"] in drifted and r["status"] in ("PASS", "FAIL", "NA"):
            r["status"], r["reason"] = "CAN_XEM", "rule trong sheet đã đổi chữ, checker chưa cập nhật — " + r["reason"]
    warnings = [f"{m['checker']}: rule {m['tab']} #{m['no']} không còn trong sheet" for m in reg["missing"]] + \
               [f"{d['checker']}: rule {d['rule']['tab']} #{d['rule']['no']} đã đổi chữ" for d in reg["drifted"]]
    out = {"package": run.meta["package"], "run": run_dir.name, "meta": run.meta, "results": results,
           "registry_warnings": warnings}
    (run_dir / "results.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    queue = [{"checker": r["checker"], "rules": [x["text"] for x in r["rules"]], **r["visual"]}
             for r in results if r.get("visual")]
    (run_dir / "visual-queue.json").write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def apply_visual(run_dir: Path, verdict_path: Path) -> dict:
    out = json.loads((run_dir / "results.json").read_text(encoding="utf-8"))
    verdicts = json.loads(verdict_path.read_text(encoding="utf-8"))
    for r in out["results"]:
        v = verdicts.get(r["checker"])
        if not v:
            continue
        if v["status"] not in STATUSES:
            raise SystemExit(f"{r['checker']}: trạng thái lạ {v['status']!r}")
        r["status"], r["reason"], r["judged_by"] = v["status"], v["reason"], v.get("judged_by", "Claude nhìn ảnh")
        r["evidence"] = list(dict.fromkeys(r.get("evidence", []) + v.get("evidence", [])))
    (run_dir / "results.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--visual", type=Path, help="file verdict của Claude để gộp vào results.json")
    ap.add_argument("--off-sub", metavar="LY_DO", help="app không bán sub (vd 'plan tuần ghi Off subs'): rule Sub thành N/A")
    args = ap.parse_args()
    out = apply_visual(args.run_dir, args.visual) if args.visual else grade(args.run_dir, args.off_sub)
    counts = {s: sum(1 for r in out["results"] if r["status"] == s) for s in STATUSES}
    print(" · ".join(f"{k} {v}" for k, v in counts.items()))
    for r in out["results"]:
        print(f"  {r['status']:8} {r['checker']}: {r['reason'][:110]}")
    open_items = unresolved(out)
    if open_items:
        # The report only goes out with every rule settled (user, 09/11/2026): PASS / FAIL, or N/A when the
        # app has no such thing. Each open item needs a follow-up run on the device or Claude's verdict.
        print(f"CÒN {len(open_items)} MỤC CHƯA CHỐT: " + ", ".join(open_items))
        return 2
    return 0


def unresolved(out: dict) -> list[str]:
    return [r["checker"] for r in out["results"] if r["status"] in ("CAN_XEM", "BLOCKED")]


if __name__ == "__main__":
    sys.exit(main())

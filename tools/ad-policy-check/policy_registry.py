"""Join the live policy sheet with the checker map in policy-checkers.json.

Answers three questions before any device work starts:
  - which checker covers each rule (one checker may cover the same rule repeated
    across tabs, e.g. "click ad có xử lý" in both Ad_VN and Đối tác);
  - which sheet rules have no checker yet  -> reported as "chưa có checker, chấm tay",
    never dropped silently;
  - which mapped rules were reworded since the map was reviewed (text_hash drift)
    or no longer exist in the sheet -> warnings, so a stale map is visible.

CLI:
  python policy_registry.py            # print coverage summary
  python policy_registry.py --stamp    # after reviewing the map, record current rule hashes
"""
import argparse
import json
import sys
from pathlib import Path

from policy_source import fetch_policy_rules

MAP_PATH = Path(__file__).resolve().parent / "policy-checkers.json"
KINDS = {"auto", "visual", "auto_visual", "ios_only"}


def load_checker_map(path: Path = MAP_PATH) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    seen: set[str] = set()
    for c in data["checkers"]:
        if c["id"] in seen:
            raise ValueError(f"Duplicate checker id: {c['id']}")
        if c["kind"] not in KINDS:
            raise ValueError(f"Checker {c['id']}: unknown kind '{c['kind']}'")
        seen.add(c["id"])
    return data


def build_registry(rules: list[dict], checker_map: dict) -> dict:
    """Pair rules with checkers.

    Returns {"checkers": [checker + resolved "rule_objs"], "unmapped": [rules],
             "missing": [refs not in sheet], "drifted": [(ref, rule)]}.
    """
    by_key = {(r["tab"], r["no"]): r for r in rules}
    mapped_keys: set[tuple[str, str]] = set()
    checkers, missing, drifted = [], [], []
    for c in checker_map["checkers"]:
        rule_objs = []
        for ref in c["rules"]:
            key = (ref["tab"], ref["no"])
            rule = by_key.get(key)
            if rule is None:
                missing.append({"checker": c["id"], **ref})
                continue
            mapped_keys.add(key)
            if ref.get("text_hash") and ref["text_hash"] != rule["text_hash"]:
                drifted.append({"checker": c["id"], "ref": ref, "rule": rule})
            rule_objs.append(rule)
        checkers.append({**c, "rule_objs": rule_objs})
    unmapped = [r for r in rules if (r["tab"], r["no"]) not in mapped_keys]
    return {"checkers": checkers, "unmapped": unmapped, "missing": missing, "drifted": drifted}


def stamp_hashes(rules: list[dict], checker_map: dict) -> int:
    """Write each ref's current text_hash into the map. Returns how many refs changed."""
    by_key = {(r["tab"], r["no"]): r for r in rules}
    changed = 0
    for c in checker_map["checkers"]:
        for ref in c["rules"]:
            rule = by_key.get((ref["tab"], ref["no"]))
            if rule and ref.get("text_hash") != rule["text_hash"]:
                ref["text_hash"] = rule["text_hash"]
                changed += 1
    return changed


def _save_map(checker_map: dict, path: Path = MAP_PATH) -> None:
    path.write_text(json.dumps(checker_map, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _print_summary(reg: dict) -> None:
    counts: dict[str, int] = {}
    for c in reg["checkers"]:
        counts[c["kind"]] = counts.get(c["kind"], 0) + 1
    print(f"Checkers: {len(reg['checkers'])} ({', '.join(f'{k}={v}' for k, v in sorted(counts.items()))})")
    print(f"Rule chưa có checker (chấm tay): {len(reg['unmapped'])}")
    for r in reg["unmapped"]:
        print(f"  - [{r['tab']} #{r['no']}] {r['group']}: {r['text'][:80]}")
    for m in reg["missing"]:
        print(f"  ! {m['checker']}: rule [{m['tab']} #{m['no']}] không còn trong sheet")
    for d in reg["drifted"]:
        print(f"  ! {d['checker']}: rule [{d['rule']['tab']} #{d['rule']['no']}] đã bị sửa chữ, xem lại map")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stamp", action="store_true", help="ghi text_hash hiện tại của rule vào map")
    args = ap.parse_args(argv)
    checker_map = load_checker_map()
    rules = fetch_policy_rules(checker_map["tabs"])
    if args.stamp:
        n = stamp_hashes(rules, checker_map)
        _save_map(checker_map)
        print(f"Đã ghi hash cho {n} rule.")
    reg = build_registry(rules, checker_map)
    _print_summary(reg)
    return 1 if reg["missing"] or reg["drifted"] else 0


if __name__ == "__main__":
    sys.exit(main())

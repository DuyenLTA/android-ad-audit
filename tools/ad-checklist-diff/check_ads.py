#!/usr/bin/env python3
"""Diff a Google Sheet ad/config checklist against a captured Android logcat file.

Usage:
    python check_ads.py --sheet <google sheet url> --log <captured logcat file> \
        --filter FOR_TESTER --filter VslTemplate4FirstOpenSDK --out report.html

The log file must already be captured (e.g. `adb logcat > file.log` while
manually triggering the app) -- this script never touches a device.
"""
import argparse
import json
import os
import sys

# Re-exported here so callers (streamlit_app.py, tests) keep importing
# everything from this one module -- the split below is just to keep each
# file under ~200 lines, not a public API change.
from checklist_source import ID_RE, fetch_checklist, parse_checklist_csv, sheet_csv_url  # noqa: F401
from log_extractor import (  # noqa: F401
    SHOW_PREFIX,
    extract_key_cooccurrences,
    extract_key_value_pairs,
    extract_label_value_pairs,
    extract_values,
    load_trusted_lines,
)
from report_renderer import render_html  # noqa: F401

# Confirmed one-off naming mismatches between a checklist value and the
# internal key name the app actually logs it under -- same placement/flag,
# unrelated string, with no derivable rule connecting the two. Only add an
# entry here once you've actually confirmed (source code, or someone who
# owns that flag) that the two names refer to the same thing -- a guess
# based on naming pattern or log-line proximity is not confirmation and
# produces a false "Khớp".
KNOWN_ALIASES: dict[str, list[str]] = {}

# Placement keys come in high/normal price-floor pairs, logged together on
# one `loadDoubleIds` line.
HIGH_SUFFIX = "_high"


MAX_CANDIDATES_SHOWN = 5


def _format_candidates(expected: str, candidates: list[str]) -> str:
    shown = candidates[:MAX_CANDIDATES_SHOWN]
    more = f" (+{len(candidates) - MAX_CANDIDATES_SHOWN} khác)" if len(candidates) > MAX_CANDIDATES_SHOWN else ""
    return (
        f"ID checklist: {expected} (lệch) -- ID lệch thấy trong log: "
        + ", ".join(shown)
        + more
        + " (chưa rõ có phải cùng placement, cần tự đối chiếu)"
    )


def _twin_value(value: str) -> str:
    """The other half of a placement's high/normal price-floor pair."""
    if value.endswith(HIGH_SUFFIX):
        return value[: -len(HIGH_SUFFIX)]
    return f"{value}{HIGH_SUFFIX}"


def _cooccurrence_candidates(
    section_rows: list[dict], key_cooccurrences: dict, checklist_values: set[str]
) -> dict[str, list[str]]:
    """Candidate keys per mismatched row, keyed by that row's checklist value.

    A same-line co-occurrence with a *confirmed* match is an actual signal,
    not a naming-pattern guess -- but it belongs to one specific row, not to
    the whole section. `loadDoubleIds` prints a placement's high/normal pair
    together (`canShowHigh=true (key=A), canShowNormal=true (key=B)`), so
    when B matched and A is unclaimed, A is a lead for B's *twin* row only.
    Spreading it across every mismatched row in the section instead filed an
    interstitial-Home key under unrelated native rows, sending QA to check
    placements the key had nothing to do with.
    """
    unmatched = {r["value"] for r in section_rows if not r["found"]}
    # A candidate already claimed under its show_-prefixed form is not a new
    # lead -- e.g. checklist value "inter_style" already matched, so its
    # co-occurring "show_inter_style" is the same thing, not a new candidate.
    claimed = checklist_values | {f"{SHOW_PREFIX}{v}" for v in checklist_values}

    candidates: dict[str, set[str]] = {}
    for row in section_rows:
        if not row["found"]:
            continue
        twin = _twin_value(row["value"])
        if twin not in unmatched:
            continue
        for key in (row["value"], f"{SHOW_PREFIX}{row['value']}"):
            candidates.setdefault(twin, set()).update(key_cooccurrences.get(key, set()))

    return {value: sorted(keys - claimed) for value, keys in candidates.items() if keys - claimed}


def _mismatch_note(
    row: dict,
    label_value_pairs: dict,
    key_value_pairs: dict,
    cooccurrence_candidates: list[str],
) -> str:
    """Best-effort "what does the log actually show" note for a Lệch row.

    Only ever presents something as a *confirmed* discrepancy when it's
    backed by an exact label or key match in the log (naming pattern or
    line-proximity guessing produced a false "Khớp" once already and was
    reverted), or by a same-line co-occurrence tied to this row's own
    high/normal twin.

    Unclaimed ad unit IDs from the capture are deliberately NOT offered here:
    that list is capture-wide, so pasting it under a row implied a per-row
    finding it never was -- the same three IDs showed up under unrelated
    placements and under the App ID row alike. They are reported once for the
    whole run instead (diff()'s "leftover_ids").
    """
    label, value = row["label"], row["value"]
    if label in label_value_pairs and label_value_pairs[label] != value:
        return f"ID checklist: {value} (lệch) -- ID lệch thấy trong log: {label_value_pairs[label]}"
    for key in (value, f"{SHOW_PREFIX}{value}"):
        if key in key_value_pairs and key_value_pairs[key].lower() != "true":
            return (
                f"ID checklist: {value} (lệch) -- có trong log nhưng đang tắt "
                f"(value={key_value_pairs[key]})"
            )
    if cooccurrence_candidates:
        return _format_candidates(value, cooccurrence_candidates)
    return f"ID checklist: {value} (lệch) -- không thấy ID lệch nào tương ứng trong log"


def diff(
    checklist: list[dict],
    trusted_values: set[str],
    label_value_pairs: dict | None = None,
    key_value_pairs: dict | None = None,
    key_cooccurrences: dict | None = None,
) -> dict:
    """Group checklist rows by section, mark MATCH/MISSING, and find EXTRA values.

    A row also counts as found if any of its optional alt_values (sheet
    column C) or KNOWN_ALIASES entries is present -- for placement keys the
    app logs under a different internal name than the checklist uses.

    label_value_pairs/key_value_pairs/key_cooccurrences (from log_extractor's
    extract_label_value_pairs/extract_key_value_pairs/extract_key_cooccurrences)
    are optional -- when given, a mismatched row gets a "note" explaining
    what the log actually shows for it, when that's derivable without
    guessing.
    """
    label_value_pairs = label_value_pairs or {}
    key_value_pairs = key_value_pairs or {}
    key_cooccurrences = key_cooccurrences or {}

    checklist_values = {row["value"] for row in checklist}
    checklist_values.update(alt for row in checklist for alt in row.get("alt_values", []))
    checklist_values.update(alt for alts in KNOWN_ALIASES.values() for alt in alts)
    extra = sorted(v for v in trusted_values if v not in checklist_values)
    leftover_ids = [v for v in extra if ID_RE.fullmatch(v)]

    # First pass: found status, grouped by section (a row's note may depend
    # on a sibling row elsewhere in the same section, so this can't be done
    # in a single pass).
    sections: dict[str, list[dict]] = {}
    for row in checklist:
        alts = [*row.get("alt_values", []), *KNOWN_ALIASES.get(row["value"], [])]
        found = row["value"] in trusted_values or any(alt in trusted_values for alt in alts)
        sections.setdefault(row["section"], []).append({**row, "found": found, "note": None})

    # Second pass: notes for mismatched rows, now that each section's full
    # sibling set is known.
    for section_rows in sections.values():
        candidates = _cooccurrence_candidates(section_rows, key_cooccurrences, checklist_values)
        for row in section_rows:
            if not row["found"]:
                row["note"] = _mismatch_note(
                    row, label_value_pairs, key_value_pairs, candidates.get(row["value"], [])
                )

    return {"sections": sections, "extra": extra, "leftover_ids": leftover_ids}


def print_summary(result: dict, empty_filters: list[str]) -> None:
    if empty_filters:
        print("WARNING: these --filter values matched 0 log lines this run")
        print("(rows below marked 'Lệch' because of this may just be uncaptured, not broken):")
        for f in empty_filters:
            print(f"  - {f}")
        print()
    for name, rows in result["sections"].items():
        section_matched = sum(1 for r in rows if r["found"])
        print(f"[{section_matched}/{len(rows)}] {name}")
    if result["extra"]:
        print(f"\n{len(result['extra'])} value(s) found in log but not in checklist:")
        for v in result["extra"]:
            print(f"  - {v}")


# The org's standard logcat filters -- the single list, shared by the CLI and
# the GUI, because two copies drift and then a row reads "Khớp" in one and
# "Lệch" in the other.
#
# Why each one is here:
#   FOR_TESTER, VslTemplate4FirstOpenSDK -- the tester build's own ad dump.
#   UserMessagingPlatform, AdsConsentManager -- the AdMob App ID's log line,
#     which the two above never print.
#   RemoteConfigRepository -- the "ID ads inapp" placement flags, which have no
#     tag of their own (just a config dump at app start).
#   inter_ads -- the interstitial high/normal price-floor decision, the source
#     of the co-occurrence hints in mismatch notes.
#   loadInterstitialAd -- the FO interstitial loads its high/normal pair on a
#     bare `D TAG` line that matches nothing above, so the normal half of the
#     pair never reached the capture's value set: an ad unit the build really
#     loads went unlisted in leftover_ids and looked like it was never seen.
DEFAULT_FILTERS = [
    "FOR_TESTER",
    "VslTemplate4FirstOpenSDK",
    "UserMessagingPlatform",
    "AdsConsentManager",
    "RemoteConfigRepository",
    "inter_ads",
    "loadInterstitialAd",
]

EXIT_OK = 0
EXIT_MISMATCH = 2


def main() -> int:
    # Imported here, not at module scope: audit_pipeline imports this module
    # for the diff primitives, so a top-level import would be circular.
    from audit_pipeline import run_audit

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sheet", required=True, help="Google Sheet checklist URL (kèm gid của tab)")
    parser.add_argument("--log", help="Logcat đã capture. Bỏ qua nếu chỉ verify từ APK")
    parser.add_argument(
        "--filter",
        action="append",
        dest="filters",
        help=f"Chuỗi con chọn dòng log tin cậy (lặp lại được). Mặc định: {', '.join(DEFAULT_FILTERS)}",
    )
    parser.add_argument("--apk", help="Verify từ file APK này -- không gọi adb, chạy được song song")
    parser.add_argument("--package", help="Package để pull APK từ máy (cache theo versionCode)")
    parser.add_argument("--out", help="Xuất report HTML")
    parser.add_argument("--json", dest="json_out", help="Xuất kết quả dạng JSON cho agent/script")
    args = parser.parse_args()

    if not args.log and not (args.apk or args.package):
        raise SystemExit("Cần ít nhất --log, hoặc --apk/--package để verify từ APK")
    if args.log and not os.path.isfile(args.log):
        raise SystemExit(f"--log file not found: {args.log}")
    if args.apk and not os.path.isfile(args.apk):
        raise SystemExit(f"--apk file not found: {args.apk}")

    # --apk means "here is the build" -- no device is consulted at all, which
    # is what makes a fan-out across many apps possible without a phone.
    result, empty_filters = run_audit(
        args.sheet,
        args.filters or DEFAULT_FILTERS,
        log_path=args.log,
        package=args.package,
        apk_path=args.apk,
        use_device=not args.apk,
    )

    print_summary(result, empty_filters)
    if args.out:
        render_html(result, empty_filters, args.out)
        print(f"\nReport written to {args.out}")
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"JSON written to {args.json_out}")

    missing = sum(1 for rows in result["sections"].values() for r in rows if not r["found"])
    return EXIT_MISMATCH if missing else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())

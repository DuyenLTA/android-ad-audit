#!/usr/bin/env python3
"""Diff a Google Sheet ad/config checklist against a captured Android logcat file.

Usage:
    python check_ads.py --sheet <google sheet url> --log <captured logcat file> \
        --filter FOR_TESTER --filter VslTemplate4FirstOpenSDK --out report.html

The log file must already be captured (e.g. `adb logcat > file.log` while
manually triggering the app) -- this script never touches a device.
"""
import argparse
import os
import sys

# Re-exported here so callers (streamlit_app.py, tests) keep importing
# everything from this one module -- the split below is just to keep each
# file under ~200 lines, not a public API change.
from checklist_source import fetch_checklist, parse_checklist_csv, sheet_csv_url  # noqa: F401
from log_extractor import extract_values, load_trusted_lines  # noqa: F401
from report_renderer import render_html  # noqa: F401


def diff(checklist: list[dict], trusted_values: set[str]) -> dict:
    """Group checklist rows by section, mark MATCH/MISSING, and find EXTRA values."""
    sections: dict[str, list[dict]] = {}
    for row in checklist:
        sections.setdefault(row["section"], []).append(
            {**row, "found": row["value"] in trusted_values}
        )

    checklist_values = {row["value"] for row in checklist}
    extra = sorted(v for v in trusted_values if v not in checklist_values)

    return {"sections": sections, "extra": extra}


def print_summary(result: dict, empty_filters: list[str]) -> None:
    if empty_filters:
        print("WARNING: these --filter values matched 0 log lines this run")
        print("(rows below marked 'Thiếu' because of this may just be uncaptured, not broken):")
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


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sheet", required=True, help="Google Sheet checklist URL")
    parser.add_argument("--log", required=True, help="Path to a captured logcat text file")
    parser.add_argument(
        "--filter",
        action="append",
        required=True,
        dest="filters",
        help="Substring to select trusted log lines (repeatable)",
    )
    parser.add_argument("--out", default="report.html", help="Output HTML report path")
    args = parser.parse_args()

    if not os.path.isfile(args.log):
        raise SystemExit(f"--log file not found: {args.log}")

    checklist = fetch_checklist(args.sheet)
    trusted_by_filter = load_trusted_lines(args.log, args.filters)
    empty_filters = [f for f, lines in trusted_by_filter.items() if not lines]
    all_trusted_lines = [line for lines in trusted_by_filter.values() for line in lines]
    trusted_values = extract_values(all_trusted_lines)
    result = diff(checklist, trusted_values)

    print_summary(result, empty_filters)
    render_html(result, empty_filters, args.out)
    print(f"\nReport written to {args.out}")


if __name__ == "__main__":
    main()

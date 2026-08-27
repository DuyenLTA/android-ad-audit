#!/usr/bin/env python3
"""Diff a Google Sheet ad/config checklist against a captured Android logcat file.

Usage:
    python check_ads.py --sheet <google sheet url> --log <captured logcat file> \
        --filter FOR_TESTER --filter VslTemplate4FirstOpenSDK --out report.html

The log file must already be captured (e.g. `adb logcat > file.log` while
manually triggering the app) -- this script never touches a device.
"""
import argparse
import csv
import html
import io
import os
import re
import sys

import requests

ID_RE = re.compile(r"ca-app-pub-\d+[/~]\d+")
BRACKET_RE = re.compile(r"\[([^\]]*)\]")


def sheet_csv_url(sheet_url: str) -> str:
    """Convert a Google Sheet share URL into its CSV export URL (preserving the tab, if given)."""
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", sheet_url)
    if not m:
        raise SystemExit(f"Not a recognizable Google Sheet URL: {sheet_url}")
    sheet_id = m.group(1)
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    gid = re.search(r"[#&?]gid=(\d+)", sheet_url)
    if gid:
        url += f"&gid={gid.group(1)}"
    return url


def parse_checklist_csv(csv_text: str) -> list[dict]:
    """Parse checklist CSV text into (section, label, value) rows."""
    reader = csv.reader(io.StringIO(csv_text))
    rows = []
    section = "(no section)"
    for cols in reader:
        col_a = (cols[0].strip() if len(cols) > 0 else "")
        col_b = (cols[1].strip() if len(cols) > 1 else "")
        if not col_a and not col_b:
            continue
        if col_a and not col_b:
            section = col_a
            continue
        # Most sections use label|value, but some rows have it swapped
        # (e.g. an ID-shaped value sitting in column A). Detect by shape
        # instead of hardcoding a per-sheet/per-section exception.
        if ID_RE.fullmatch(col_a) and not ID_RE.fullmatch(col_b):
            label, value = col_b, col_a
        else:
            label, value = col_a, col_b
        rows.append({"section": section, "label": label, "value": value})
    return rows


def fetch_checklist(sheet_url: str) -> list[dict]:
    """Download and parse the checklist sheet into (section, label, value) rows."""
    url = sheet_csv_url(sheet_url)
    resp = requests.get(url, allow_redirects=True, timeout=30)
    if resp.status_code != 200 or "text/html" in resp.headers.get("content-type", ""):
        raise SystemExit(
            "Could not download the sheet as CSV (got HTML/error instead). "
            "Check the sheet is shared as 'Anyone with the link can view'."
        )
    return parse_checklist_csv(resp.text)


def load_trusted_lines(log_path: str, filters: list[str]) -> dict[str, list[str]]:
    """Return, per --filter substring, every log line that contains it.

    Keeping this per-filter (rather than one flat pool) lets the caller warn
    when a given --filter matched zero lines -- a strong signal that this
    run's capture doesn't cover that area at all, distinct from a value
    genuinely being absent from lines that *were* captured.
    """
    trusted: dict[str, list[str]] = {flt: [] for flt in filters}
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            low = line.lower()
            for flt in filters:
                if flt.lower() in low:
                    trusted[flt].append(line)
    return trusted


def extract_values(lines: list[str]) -> set[str]:
    """Pull candidate config/ID values out of trusted log lines.

    Three shapes are supported (all seen in real captures):
      1. `TAG: Adjust config token: uz6fb8kyeww0`      -> trailing value after last colon
      2. `TAG: LFO1: [id1, id2, id3]`                  -> bracket-list members
      3. `... ca-app-pub-123/456 ...` anywhere in line -> AdMob app/unit IDs
    """
    values = set()
    for line in lines:
        for m in ID_RE.finditer(line):
            values.add(m.group(0))

        for bracket in BRACKET_RE.finditer(line):
            for item in bracket.group(1).split(","):
                item = item.strip()
                if item:
                    values.add(item)

        # Independent of whether the line also had a bracket list -- a line
        # can have both a leading `[tag]`-style marker and a trailing
        # `Label: value`.
        last_colon = line.rstrip("\n").rfind(":")
        if last_colon != -1:
            tail = line[last_colon + 1 :].strip()
            if tail and not tail.startswith("["):
                values.add(tail)
    return values


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


def render_html(result: dict, empty_filters: list[str], out_path: str) -> None:
    sections = result["sections"]
    extra = result["extra"]

    total = sum(len(rows) for rows in sections.values())
    matched = sum(1 for rows in sections.values() for r in rows if r["found"])

    section_html = []
    for name, rows in sections.items():
        section_matched = sum(1 for r in rows if r["found"])
        row_html = []
        for r in rows:
            status = "pass" if r["found"] else "fail"
            label_txt = "Khớp" if r["found"] else "Thiếu"
            row_html.append(
                f"<tr><td class='cell-label'>{html.escape(r['label'])}</td>"
                f"<td class='cell-mono'>{html.escape(r['value'])}</td>"
                f"<td><span class='status {status}'><span class='dot'></span>{label_txt}</span></td></tr>"
            )
        section_html.append(
            f"<section><div class='section-head'><h2>{html.escape(name)}</h2>"
            f"<span class='filter-tag'>{section_matched}/{len(rows)} khớp</span></div>"
            f"<div class='table-scroll'><table><thead><tr><th>Label</th><th>Giá trị (sheet)</th>"
            f"<th>Kết quả</th></tr></thead><tbody>{''.join(row_html)}</tbody></table></div></section>"
        )

    warning_html = ""
    if empty_filters:
        chips = "".join(f"<span class='chip'>{html.escape(f)}</span>" for f in empty_filters)
        warning_html = (
            "<div class='callout'><h3>Filter không khớp dòng log nào trong lần capture này</h3>"
            "<p>Các dòng \"Thiếu\" liên quan tới filter này có thể chỉ vì log chưa capture đúng "
            "vùng, không hẳn là app bị lỗi thật -- capture lại rồi chạy lại trước khi kết luận.</p>"
            f"<div class='chip-list'>{chips}</div></div>"
        )

    extra_html = ""
    if extra:
        chips = "".join(f"<span class='chip'>{html.escape(v)}</span>" for v in extra)
        extra_html = (
            "<div class='callout'><h3>Giá trị thấy trong log, không có trong sheet</h3>"
            f"<div class='chip-list'>{chips}</div></div>"
        )

    page = f"""<title>Ad Checklist Diff</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@700;800&family=Public+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root{{--ink:#14171c;--ink-soft:#4b525c;--paper:#f2f3f5;--surface:#fff;--line:#dadfe3;
    --accent:#1f6f78;--accent-soft:#e4eeee;--pass:#2e7d4f;--pass-soft:#e5f3ea;
    --fail:#c0392b;--fail-soft:#fbe9e7;--pending:#b8790c;--pending-soft:#faf1de;}}
  @media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{--ink:#e8eaed;--ink-soft:#a7adb6;
    --paper:#101317;--surface:#171b20;--line:#2a2f36;--accent:#5fc2cb;--accent-soft:#1a2f31;
    --pass:#5fbd85;--pass-soft:#16261c;--fail:#e2695a;--fail-soft:#2b1a18;
    --pending:#dba53f;--pending-soft:#2b2415;}}}}
  :root[data-theme="dark"]{{--ink:#e8eaed;--ink-soft:#a7adb6;--paper:#101317;--surface:#171b20;
    --line:#2a2f36;--accent:#5fc2cb;--accent-soft:#1a2f31;--pass:#5fbd85;--pass-soft:#16261c;
    --fail:#e2695a;--fail-soft:#2b1a18;--pending:#dba53f;--pending-soft:#2b2415;}}
  *{{box-sizing:border-box;}}
  body{{margin:0;background:var(--paper);color:var(--ink);font-family:'Public Sans',sans-serif;line-height:1.5;}}
  h1,h2{{font-family:'Manrope',sans-serif;margin:0;}}
  .wrap{{max-width:900px;margin:0 auto;padding:2rem 1.5rem 4rem;display:flex;flex-direction:column;gap:2rem;}}
  .scorecard{{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:1rem 1.25rem;}}
  .scorecard .num{{font-family:'Manrope',sans-serif;font-weight:800;font-size:1.8rem;color:var(--pass);}}
  .section-head{{display:flex;justify-content:space-between;align-items:baseline;gap:1rem;margin-bottom:0.75rem;flex-wrap:wrap;}}
  .filter-tag{{font-family:'JetBrains Mono',monospace;font-size:0.72rem;background:var(--accent-soft);color:var(--accent);
    padding:0.15rem 0.5rem;border-radius:5px;font-weight:600;}}
  .table-scroll{{overflow-x:auto;border:1px solid var(--line);border-radius:10px;background:var(--surface);}}
  table{{width:100%;border-collapse:collapse;font-size:0.88rem;min-width:480px;}}
  thead th{{text-align:left;font-family:'JetBrains Mono',monospace;font-size:0.68rem;text-transform:uppercase;
    letter-spacing:0.07em;color:var(--ink-soft);padding:0.6rem 1rem;border-bottom:1px solid var(--line);}}
  tbody td{{padding:0.55rem 1rem;border-bottom:1px solid var(--line);}}
  tbody tr:last-child td{{border-bottom:none;}}
  .cell-mono{{font-family:'JetBrains Mono',monospace;font-size:0.83rem;color:var(--ink-soft);}}
  .status{{display:inline-flex;align-items:center;gap:0.35rem;font-family:'JetBrains Mono',monospace;
    font-size:0.72rem;font-weight:600;padding:0.2rem 0.55rem;border-radius:20px;}}
  .status.pass{{background:var(--pass-soft);color:var(--pass);}}
  .status.fail{{background:var(--fail-soft);color:var(--fail);}}
  .status .dot{{width:6px;height:6px;border-radius:50%;background:currentColor;}}
  .callout{{border:1px solid var(--line);border-left:3px solid var(--pending);background:var(--pending-soft);
    border-radius:0 8px 8px 0;padding:1rem 1.25rem;}}
  .chip-list{{display:flex;flex-wrap:wrap;gap:0.5rem;margin-top:0.5rem;}}
  .chip{{font-family:'JetBrains Mono',monospace;font-size:0.76rem;background:var(--surface);
    border:1px solid var(--line);border-radius:6px;padding:0.3rem 0.55rem;}}
</style>
<div class="wrap">
  <h1>Ad &amp; Config Checklist Diff</h1>
  <div class="scorecard"><div class="num">{matched} / {total}</div><div>dòng checklist khớp</div></div>
  {warning_html}
  {''.join(section_html)}
  {extra_html}
</div>
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(page)


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

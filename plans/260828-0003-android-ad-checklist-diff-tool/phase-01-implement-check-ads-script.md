---
phase: 1
title: "Implement check_ads.py"
status: completed
priority: P1
effort: "2-3h"
dependencies: []
---

# Phase 1: Implement check_ads.py

## Overview
Single-file Python script that parses a Google Sheet checklist and a
captured logcat file, diffs them by value per `--filter`, and emits an
HTML report plus a terminal summary.

## Requirements
- Functional:
  - `--sheet <url>` (required) — Google Sheet share URL.
  - `--log <path>` (required) — path to a text file of captured logcat output.
  - `--filter <substring>` (repeatable, required at least once) — one per
    checklist section to check (e.g. `--filter FOR_TESTER --filter VslTemplate4FirstOpenSDK`).
  - `--out <path>` (optional, default `./report.html`).
- Non-functional:
  - No network calls except fetching the sheet CSV.
  - No device/adb interaction of any kind (out of scope, see plan.md).
  - Single file, stdlib + `requests` only — no new heavy dependencies.

## Architecture
Linear pipeline, four stages in one file (functions, no classes needed —
YAGNI):

1. `fetch_checklist(sheet_url) -> list[dict]`
   - Convert share URL to `/export?format=csv` URL, `requests.get(..., allow_redirects=True)`.
   - Parse CSV via `csv.reader`. Track `current_section`: a row where column B
     is empty and column A is non-empty updates `current_section` and is
     skipped as data. A row where both columns are empty is skipped. Every
     other row → `{section, label, value}`.

2. `load_trusted_lines(log_path, filters) -> dict[str, list[str]]`
   - Read log file once. For each filter substring, collect lines containing
     it (case-insensitive) into `trusted[filter]`.

3. `extract_values(lines) -> set[str]`
   - Regex over the trusted lines pool:
     - `ca-app-pub-\d+[/~]\d+` (AdMob app/unit IDs)
     - `:\s*([A-Za-z0-9_.]+)\s*$` (trailing single value after last colon)
     - Comma-split contents of any `[...]` bracket list
   - Return the union as a flat set of candidate value strings (trimmed).

4. `diff(checklist, trusted) -> dict`
   - For each checklist row: MATCH if `row.value` appears verbatim as a
     member of the union of `extract_values(trusted[f])` over all filters;
     else MISSING.
   - EXTRA = `extract_values(all trusted lines) - {row.value for row in checklist}`.
   - Group results by `section` (preserve sheet row order within section).

5. `render_html(diff_result, out_path)`
   - Reuse the visual system from today's artifact (dashboard-style: scorecard
     summary row, per-section table, mono tabular IDs, pass/warn/pending
     status chips, light+dark theme via `prefers-color-scheme`). Self-contained
     HTML, Google Fonts link only, no other external assets.
   - Also print a plain-text summary table to stdout (section, matched/total,
     extra count).

## Related Code Files
- Create: `C:\Users\hoang\tools\ad-checklist-diff\check_ads.py`
- Create: `C:\Users\hoang\tools\ad-checklist-diff\README.md` (usage: the
  `--filter` args, where to get a logcat capture, example command)

## Implementation Steps
1. Scaffold argparse CLI with the 4 flags above; validate `--log` file exists
   before doing any network call (fail fast).
2. Implement `fetch_checklist` — test manually against the real sheet URL
   from today (`14XivZl9VPAnyf8hYICgRh-TOUmkGTZDCqoyWmPM57hM`) to confirm the
   CSV export + redirect handling works via `requests` (WebFetch needed a
   manual redirect follow earlier; `requests` should handle it natively —
   verify, don't assume).
3. Implement `load_trusted_lines` + `extract_values`; unit-test the three
   regex forms against the three real line shapes seen today:
   - `... FOR_TESTER_CONFIG: Adjust config token: uz6fb8kyeww0`
   - `... FOR_TESTER_CONFIG: Facebook Client Token: b0fec8b50648f21fecccce7125c0e349`
   - `... FO_VslTemplate4FirstOpenSDK: LFO1: [ca-app-pub-.../6280116312, ca-app-pub-.../9966424892, ...]`
4. Implement `diff` + `render_html`; keep the HTML generation as an f-string
   template function, not a templating engine dependency (YAGNI).
5. Wire CLI end to end; print stdout summary.

## Success Criteria
- [ ] `python check_ads.py --sheet <url> --log <file> --filter FOR_TESTER --filter VslTemplate4FirstOpenSDK --out report.html` runs without error on today's real sheet URL.
- [ ] Script has zero adb/device/UI-automation code paths.
- [ ] README documents the manual capture step the user still has to do (`adb logcat > file.log` while triggering the app manually).

## Risk Assessment
- Google Sheet CSV export may prompt a Google auth/consent page instead of
  raw CSV for some sheets (permissions differ per sheet) → surface a clear
  error telling the user to check sheet sharing settings, don't fail silently.
- Regex value extraction is a heuristic, not a full parser — a log line shape
  not seen today could be missed. Acceptable per YAGNI; document the 3
  supported shapes in the README so it's obvious when a 4th shape needs a
  regex added later.

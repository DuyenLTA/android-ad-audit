---
phase: 2
title: "Verify against today's real capture data"
status: completed
priority: P1
effort: "30m"
dependencies: [1]
---

# Phase 2: Verify against today's real capture data

## Overview
Prove the script reproduces today's manual result exactly, using the real
logcat captures already collected for the Nexus app in this session — this
is a regression check against a known-good manual result, not a synthetic
test.

## Requirements
- Functional: running the script against the real sheet + real captured logs
  must reproduce the same 40/40 MATCH + 6 EXTRA result documented in the
  artifact from this session.
- Non-functional: no new device interaction needed — reuse existing log
  files.

## Architecture
N/A — verification only, no new code paths beyond phase 1.

## Related Code Files
- Modify: none
- Read: `check_ads.py` output vs the artifact HTML from this session
  (https://claude.ai/code/artifact/afe8d193-8bd7-4839-9d29-7acacb3e6641)

## Implementation Steps
1. Concatenate this session's two real capture files (`full_capture2.log`
   covering `FOR_TESTER`, `full_capture3_tutorial.log` covering
   `VslTemplate4FirstOpenSDK`) into one log file, or run the script twice
   (once per filter) — either should work since `--filter` is repeatable.
2. Run: `python check_ads.py --sheet https://docs.google.com/spreadsheets/d/14XivZl9VPAnyf8hYICgRh-TOUmkGTZDCqoyWmPM57hM/edit --log <concatenated.log> --filter FOR_TESTER --filter VslTemplate4FirstOpenSDK --out verify-report.html`
3. Compare counts: expect 8/8 MATCH in the "Thông số kỹ thuật" section, 32/32
   MATCH in "ID ads FO", 6 EXTRA (the AppResume IDs), 18 rows untouched in
   "ID ads inapp" (no filter covers them — confirm the script reports these
   as "not covered by any filter", not as MISSING, since MISSING should mean
   "filter ran but value absent").
4. If counts don't match, diagnose against the regexes in phase 1 step 3
   before changing the diff logic.

## Success Criteria
- [ ] Script output matches today's manual result exactly (8/8, 32/32, 6 extra).
- [ ] Rows belonging to a checklist section with no matching `--filter`
      argument are reported as "not checked" (distinct status), not silently
      counted as MISSING or MATCH.

## Risk Assessment
- Low risk — this phase only validates phase 1's output against a known
  answer; no new logic introduced here. If mismatch found, root-cause in
  phase 1's regex/parsing before considering the plan done.

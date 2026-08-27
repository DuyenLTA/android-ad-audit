# Android Ad Audit: Manual Process Generalized into Reusable Diff Tool

**Date**: 2026-08-27 15:30
**Severity**: Medium
**Component**: Android ad audit tooling, logcat analysis, CSV diffing
**Status**: Resolved

## What Happened

Took a one-off manual ad-checklist audit (Nexus - AI Video Generator) against a Google Sheet (Facebook/Adjust config + ~40 AdMob ad unit IDs) and generalized it into a reusable, standalone tool. The manual process—capture logcat, grep values, cross-reference with sheet—worked but was error-prone and not scalable. Brainstormed, planned, and built `tools/ad-checklist-diff/check_ads.py` to automate the comparison logic. Implemented 10 unit tests (all passing); code reviewer caught 2 real bugs and 3 additional issues before finalization. End-to-end validation against the original audit's captures confirmed match accuracy.

## The Brutal Truth

The experience surfaced a hard operational lesson: **never automate on-device UI taps/navigation for log capture tasks**. Initial attempt to auto-tap the splash-screen logo (a 1–2s window) to trigger debug logs was unreliable—one blind tap landed in a background Chrome tab and typed text into an unrelated web form. No submit, no real damage, but a real near-miss that could have corrupted data or triggered unintended actions. Humans should always do the physical interaction while tooling owns the capture. This isn't a theoretical concern; it happened in 5 seconds of trying.

Also frustrating: discovering the logcat filtering assumption was wrong. Spent time debugging why `adb logcat -s TAG:*` wasn't matching expected log lines, only to realize the user's "filter names" (e.g. `FOR_TESTER`, `VslTemplate4FirstOpenSDK`) aren't exact tags—they're Android-Studio-Logcat-style substring patterns that match tag *families* like `FOR_TESTER_CONFIG`, `FOR_TESTER_LOAD_AD`, etc. Had to scrap exact matching and grep by substring instead.

## Technical Details

**Initial Manual Audit (Session 1):**
- Connected Android device via adb
- Captured `adb logcat` to text file (~2000 lines)
- Manually cross-referenced ~150 config key–value pairs against Google Sheet
- All checked rows matched; published HTML artifact

**Operational Issue Discovered:**
- Attempted to automate splash-screen logo tap using `adb shell input tap` to trigger debug log dump
- Splash screen visible ~1–2s; tool round-trip latency ~3–5s
- One blind-tap landed in background Chrome tab, typed unrelated text into a form
- Impact: near-miss, no data corruption; lesson: never automate this pattern

**Logcat Filtering Issue:**
- User filter names like `FOR_TESTER`, `VslTemplate4FirstOpenSDK` are **not** exact logcat tags
- `adb logcat -s FOR_TESTER:*` does exact tag matching; misses `FOR_TESTER_CONFIG`, `FOR_TESTER_LOAD_AD`
- Fixed: capture unfiltered logcat, grep by substring post-hoc

**Tool Implementation (check_ads.py):**
- Fetches Google Sheet checklist as CSV (handles `gid` param for tab selection)
- Reads pre-captured logcat text file (user supplies `--log` path)
- Extracts key–value pairs from lines matching user-supplied `--filter` substring(s)
- Diffs by VALUE (not label—placement-key naming varies per app)
- Outputs CSV with MATCHED/MISSING rows and per-filter zero-match warnings
- Scope: no adb/device automation; pure file I/O and text parsing

**Code Review Findings & Fixes (2 bugs, 3 enhancements):**
1. **Bug: Silent skip in `extract_values`** — trailing-colon extraction was skipped if line also contained earlier `[...]` bracket (regex precedence bug). Caused false MISSING results. Fixed: regex rewritten to capture colon-delimited values correctly regardless of bracket presence.
2. **Bug: "Section not checked" heuristic** — used "0/N matched" per section to flag "not yet captured"; masked genuinely broken sections as merely "not yet run" (false negative safety risk). Replaced with explicit per-`--filter` zero-match warnings; no silent guessing.
3. **Enhancement: Early file validation** — was making HTTP request to fetch sheet before checking if `--log` file exists, causing raw traceback crash on missing file. Now validate `--log` early.
4. **Enhancement: Preserve sheet `gid`** — CSV export URL was silently defaulting to first tab instead of preserving user's `gid` param from Google Sheet URL. Now extracts and preserves `gid` in export URL.
5. **Data Quality Fix: Shape detection for swapped columns** — discovered live checklist sheet had one section with label/value columns swapped relative to all others. Rather than hardcode an exception, implemented regex pattern-matching for AdMob ID format to auto-detect and correct column order, generalizing the fix to future sheets.

**Testing:**
- 10 unit tests (test_check_ads.py): value extraction, CSV parsing, diff logic, edge cases (empty logs, no matches, malformed values)
- All passing
- End-to-end validation: re-ran against real sheet + session logcat captures; match counts identical to manual audit

## What We Tried

1. **Auto-tap splash screen** → Failed due to latency and UI timing. Rejected: unreliable, risky (near-miss). Decision: humans tap, tooling captures.
2. **Exact logcat tag filtering** → Failed; misses substring-matched tags. Solution: unfiltered capture + post-hoc grep.
3. **Section-level "not checked" heuristic** → Masks real failures. Solution: per-filter zero-match warnings.
4. **Hardcoding exception for swapped columns** → Brittle. Solution: shape-detection regex.

## Root Cause Analysis

**Why manual process wasn't scalable:** Each app has different tag names, log formats, and sheet structures. Generalizing required: (a) CSV fetch from arbitrary sheets, (b) flexible tag filtering, (c) VALUE-based diffing (not label), (d) robustness to schema variance (swapped columns, missing sections).

**Why automation failed:** On-device UI taps are fundamentally unreliable because:
- Splash screen visible ~1–2s; tool latency ~3–5s
- Race condition between screen state and tap timing
- Blind taps land in unpredictable UI contexts
- No way to verify pre-tap state before issuing command

**Why logcat filtering was wrong:** Terminology collision—"filter" in Android Studio Logcat means substring match on tag families, not exact tag equality. Documentation and tool defaults didn't make this clear.

**Why bugs slipped past initial code:** Missing regression tests for edge cases (brackets in lines, empty section results, malformed CSV). Code review enforced test-driven validation.

## Lessons Learned

1. **Never automate on-device UI interaction for data capture.** Even 1–2 seconds of uncertainty is unacceptable when a near-miss can corrupt data or trigger side effects. Humans should always do the physical interaction (tapping, swiping, navigating) while tooling owns log capture and analysis.

2. **Validate assumptions about library/tool semantics early.** Assumed `adb logcat -s` did exact tag matching; it doesn't. Cost: 30 min debugging. Would have been 2 min with a quick grep test upfront.

3. **Explicit warnings beat guessing heuristics.** Section-level "0/N matched" was neat logic but masked broken state. Per-filter zero-match warnings are verbose but actionable.

4. **Shape detection generalizes better than exceptions.** When discovering data-quality issues (swapped columns), regex pattern-matching beats hardcoding app/section-specific fixes.

5. **Code review catches subtle bugs.** The `extract_values` bracket bug was syntactically correct but logically wrong. Regex edge cases need explicit test cases.

## Next Steps

- Script is complete, tested, and ready for reuse on other apps' checklists
- No immediate action required; tool can generalize to any app with a Google Sheet checklist and logcat captures
- Future: if automation of capture becomes necessary (e.g., many devices, repeated audits), explore structured logging or SDK-level instrumentation instead of UI automation
- Document the logcat-filtering quirk in script comments to prevent future confusion

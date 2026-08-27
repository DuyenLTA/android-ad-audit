---
status: completed
mode: fast
source: brainstorm
brainstormReport: plans/reports/brainstorm-to-planner-android-ad-checklist-diff-tool-report.md
---

# Plan: Android ad-config checklist diff tool

## Overview
Standalone Python script `check_ads.py` — diff a Google Sheet ad/config
checklist against an already-captured Android `logcat` file, so the manual
cross-check done today for the Nexus app (see artifact:
https://claude.ai/code/artifact/afe8d193-8bd7-4839-9d29-7acacb3e6641) can be
repeated for other apps without redoing the matching by hand.

Trivial/well-understood scope (single file, no existing codebase to
integrate with, approach already validated manually) — fast mode, no
research/red-team/validate gates.

## Key constraints (from brainstorm)
- Match by **value**, not by label/placement-key name — label conventions
  differ per app, values (tokens, ad unit IDs) are unique and stable.
- Do **not** automate the on-device trigger (tap logo / navigate tutorial) —
  proven unreliable and risky this session (mis-tap landed in Chrome).
  User always supplies an already-captured log file.
- `--filter` scopes which log lines are trusted per checklist section —
  substring match (Android Studio Logcat style), not exact `adb -s` tag.

## Phases

| # | Phase | Status |
|---|-------|--------|
| 1 | Implement `check_ads.py` | completed |
| 2 | Verify against today's real capture data | completed |

See `phase-01-implement-check-ads-script.md`, `phase-02-verify-with-real-capture-data.md`.

## Location
`C:\Users\hoang\tools\ad-checklist-diff\check_ads.py` — new standalone
folder, not tied to any existing project. Only dependency: `requests`
(already installed).

## Out of scope
- No auto-tap / UI automation.
- No Streamlit/android-qa-agent integration.
- No fuzzy label matching.

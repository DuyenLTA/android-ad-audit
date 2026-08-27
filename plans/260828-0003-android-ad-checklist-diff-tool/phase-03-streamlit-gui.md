---
phase: 3
title: "Streamlit GUI for check_ads"
status: completed
priority: P1
effort: "1-2h"
dependencies: [1, 2]
---

# Phase 3: Streamlit GUI for check_ads

## Overview
Local Streamlit app so the user never touches a terminal: sheet URL + filter
list as inputs, one Start/Stop button that drives `adb logcat` capture while
they operate the phone by hand, then auto-generates and displays the same
HTML report `check_ads.py` produces.

## Key constraint (from user, this turn)
- Artifacts (claude.ai published pages) are sandboxed web pages -- they
  cannot run `adb`/local processes. This GUI is a **local** app the user
  runs on their own machine (`streamlit run app.py`), not a hosted artifact.
  The output is a local HTML report file, displayed inline in the Streamlit
  page. If the user wants a shareable claude.ai link, that's a separate ask
  in a Claude Code chat turn (publish the generated file) -- out of scope
  for this GUI itself.
- Single Start/Stop button covers all filters at once (not per-filter) --
  user confirmed one on-device pass (open app -> go to home) produces log
  lines for every filter simultaneously.
- No on-device automation (tap/navigate) inside the GUI -- same constraint
  as check_ads.py itself, confirmed unreliable/risky this session.

## Requirements
- Functional:
  - Text input: Google Sheet checklist URL.
  - Text area: one `--filter` substring per line.
  - Start button: `adb devices` sanity check (error if no device attached),
    `adb logcat -c`, then start `adb logcat` as a background subprocess
    writing to a temp file. Button becomes "Stop" while running.
  - Stop button: terminate the subprocess, then run the same
    fetch_checklist -> load_trusted_lines -> extract_values -> diff ->
    render_html pipeline as check_ads.py (import the functions, don't
    duplicate them), render the resulting HTML inline in the page.
  - Show any `check_ads` per-filter zero-match warnings prominently (reuse,
    don't reinvent).
- Non-functional: single file, reuses `check_ads.py` via import (DRY) --
  no copy-pasted pipeline logic.

## Architecture
`tools/ad-checklist-diff/streamlit_app.py`, imports from `check_ads.py`
(`fetch_checklist`, `load_trusted_lines`, `extract_values`, `diff`,
`render_html`). Streamlit session state holds the running
`subprocess.Popen` handle and the temp log path across reruns (Streamlit
reruns the whole script on every widget interaction, so the process handle
must survive in `st.session_state`, not a local variable).

## Related Code Files
- Create: `tools/ad-checklist-diff/streamlit_app.py`
- Modify: `tools/ad-checklist-diff/README.md` (add GUI usage section)
- Read: `tools/ad-checklist-diff/check_ads.py` (import target, do not
  duplicate its pipeline)

## Implementation Steps
1. `adb devices` check via `subprocess.run(["adb","devices"], capture_output=True)` -- parse for at least one `\tdevice` line; block Start with a clear error otherwise.
2. Start: `subprocess.run(["adb","logcat","-c"])`, then `subprocess.Popen(["adb","logcat"], stdout=open(log_path,"w"), stderr=subprocess.STDOUT)`; store `proc` + `log_path` in `st.session_state`.
3. Stop: `proc.terminate(); proc.wait(timeout=5)`; clear session state capture flag; run the check_ads pipeline against `log_path`; `st.components.v1.html(report_html_string, height=1200, scrolling=True)`.
4. Handle the trivial case where Stop is clicked with 0 bytes captured (adb never attached properly) -- show a clear error instead of a confusing empty report.
5. Update README with a "GUI" section alongside the existing CLI section.

## Success Criteria
- [ ] `streamlit run streamlit_app.py` opens a page with sheet URL input, filter textarea, Start/Stop button.
- [ ] Start with no device attached shows a clear error, doesn't crash.
- [ ] Full manual run against the real Nexus sheet + real device reproduces the same match counts as `check_ads.py` CLI.
- [ ] No duplicated pipeline logic -- GUI imports from check_ads.py.

## Risk Assessment
- Streamlit reruns the script top-to-bottom on every interaction -- process
  handle must live in `st.session_state`, not a bare module-level variable,
  or Stop won't find the running process. Verify this explicitly during
  manual testing, it's the one Streamlit-specific footgun here.
- Orphaned `adb logcat` process if the user closes the browser tab instead
  of clicking Stop -- acceptable known limitation for a local single-user
  tool (document in README: `adb logcat` processes can be killed via Task
  Manager if this happens), not worth building a cleanup daemon for (YAGNI).

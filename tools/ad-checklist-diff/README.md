# ad-checklist-diff

Diff a Google Sheet ad/config checklist against a captured Android `logcat`
file. Matches by **value** (token, ad unit ID), not by label -- placement
naming differs per app, values are unique.

Full usage guide (overview, install, GUI/CLI walkthrough, troubleshooting):
https://claude.ai/code/artifact/b499b2e9-314b-4fc3-b01c-f7a13da46c18

## What this does NOT do

- `check_ads.py` (the CLI) does not touch a device or run `adb` in any way --
  you capture the log yourself, by hand, and hand it a file.
  `streamlit_app.py` (the GUI) *does* run `adb` locally to capture for you,
  see below -- but neither ever triggers the app's own debug/tester log dump
  (tapping the splash logo, navigating onboarding, etc). You still have to
  operate the phone yourself.
- Does not fuzzy-match labels -- only exact value presence, plus the
  narrowly-scoped fallbacks documented under "Reading the result" below.
- Cannot verify things that never appear inside a trusted (`--filter`-matched)
  line, **in the CLI**. The GUI's fixed filter list (`FOR_TESTER`,
  `VslTemplate4FirstOpenSDK`, `UserMessagingPlatform`, `AdsConsentManager`,
  `RemoteConfigRepository`, `inter_ads`) covers every area the Nexus app
  checklist needs; a plain CLI run with only the first two will still show
  the App ID, Package name, and "ID ads inapp" rows as "Lệch" even when
  correct -- use the GUI, or add the extra `--filter` values by hand.
- Package name is verified separately via `adb shell pm list packages`
  (GUI only) since it's never printed in any log line at all.
- The AdMob **App ID** and the ad unit IDs of placements a capture never
  exercised are verified against the **installed APK** instead (GUI only):
  some apps never print the App ID to logcat, and an ad unit ID only reaches
  logcat when the app actually requests that placement -- which used to mean
  walking every screen, including flows like an uninstall survey that are
  impractical to trigger. An APK match is labelled as such in the report: it
  proves the build contains the ID, *not* that the placement is enabled or
  that the screen is wired to it. A row already confirmed in the log keeps its
  log verdict. Reading the App ID needs `aapt2` from the Android SDK
  build-tools; ad unit IDs need no extra tooling. The pulled APK is cached
  under `~/.cache/ad-checklist-diff/<package>-<versionCode>.apk` and reused
  until the app is updated, so only the first run per build pays the pull.
- Ad unit IDs found in the log but belonging to no checklist row are listed
  **once** per run in the report, not under individual rows -- that list is
  capture-wide, and pasting it under a row read as a per-row finding it never
  was.

## Setup

```
pip install requests streamlit   # streamlit only needed for the GUI
```

## Option A: GUI (no terminal commands after setup)

```
streamlit run streamlit_app.py
```

Opens a local page in your browser: paste the sheet URL, click **Start**.
Filters are fixed (not editable) -- shown as chips. It clears the logcat
buffer and starts capturing in the background -- go operate the phone (open
the app, walk through onboarding, go to home; pause a couple seconds per
screen rather than rushing, some placements only preload after their
`_high` sibling finishes). Click **Stop** when done; a per-section score
summary appears immediately, with a full-width button to open the report
in a new tab and an expander to preview it inline. This is a **local** app
-- it is not a shareable web link. If you want a shareable link, ask Claude
to publish the saved report file as an artifact in a chat turn.

If you close the browser tab (or refresh it) mid-capture instead of
clicking Stop, the `adb logcat` process keeps running orphaned in the
background -- kill it via Task Manager (or `adb kill-server` if you don't
mind resetting other adb connections too) if this happens.

## Option B: CLI

### 1. Capture a log

While your device is connected via `adb`, clear the buffer and capture while
manually triggering the relevant screen/flow in the app:

```
adb logcat -c
adb logcat > capture.log
```

(Ctrl+C to stop once you've triggered what you need.) One capture file can
cover multiple `--filter` values in one run.

### 2. Run the diff

```
python check_ads.py \
  --sheet "https://docs.google.com/spreadsheets/d/<id>/edit" \
  --log capture.log \
  --filter FOR_TESTER \
  --filter VslTemplate4FirstOpenSDK \
  --filter UserMessagingPlatform \
  --filter AdsConsentManager \
  --filter RemoteConfigRepository \
  --filter inter_ads \
  --out report.html
```

`--filter` is a substring match against the raw log text (like Android
Studio's Logcat search box), not an exact `adb logcat -s` tag -- repeat it
once per checklist area you captured this run.

## Reading the result

- Terminal (or the GUI page) prints `[matched/total] section name`, plus any
  value found in the log that isn't in the checklist.
- If a `--filter` you passed matched **zero** log lines this run, that's
  called out as an explicit warning -- it means your capture doesn't cover
  that area at all, so any "Lệch" rows in that area might just be
  uncaptured, not actually broken. Capture again with the right filter/flow
  before trusting those rows.
- Every "Lệch" (mismatch) row gets a short note explaining what's actually
  in the log for it, prefixed with the checklist's own expected ID for
  direct comparison:
  - An exact label match with a different value -> the log's actual value.
  - A remote-config flag present but `value=false` -> says so explicitly.
  - A key seen on the *same log line* as an already-matched sibling row ->
    listed as an unconfirmed candidate (never asserted as a match -- a
    naming-pattern guess produced a false "Khớp" once and was reverted;
    only same-line co-occurrence with a confirmed match counts now).
  - Otherwise -> "không thấy ID lệch nào tương ứng trong log" (nothing
    found), rather than staying silent.
- `report.html` (or the equivalent GUI output) is the same info as a
  browsable report.

## Sheet requirements

Checklist sheet must be shared "Anyone with the link can view", two columns:
column A = label (or a section header when column B is empty), column B =
expected value.

An optional column C lists alternate log values that also count as a match,
comma-separated. Use this when the app logs a placement under a different
internal key name than the checklist uses -- a real naming inconsistency in
the app's own code, not something the tool can derive automatically. Example:
the Nexus checklist's "Home -> inter_feature_high" row is logged in code as
`enable_401_home_a_inter_high` (same placement/flag, different internal
name) -- add that string as column C on that row and it matches correctly
even though the two names share no substring.

# ad-checklist-diff

Diff a Google Sheet ad/config checklist against a captured Android `logcat`
file. Matches by **value** (token, ad unit ID), not by label -- placement
naming differs per app, values are unique.

## What this does NOT do

- `check_ads.py` (the CLI) does not touch a device or run `adb` in any way --
  you capture the log yourself, by hand, and hand it a file.
  `streamlit_app.py` (the GUI) *does* run `adb` locally to capture for you,
  see below -- but neither ever triggers the app's own debug/tester log dump
  (tapping the splash logo, navigating onboarding, etc). You still have to
  operate the phone yourself.
- Does not fuzzy-match labels -- only exact value presence.
- Cannot verify things that never appear inside a trusted (`--filter`-matched)
  line. In the Nexus app checklist, "Package name" and the AdMob "App ID"
  aren't printed under the `FOR_TESTER` tag family at all -- package name
  needs `adb shell pm list packages <name>`, and the App ID line is tagged
  `UserMessagingPlatform`/`AdsConsentManager`. Those rows will show as
  "Thiếu" here even when correct; verify them separately.

## Setup

```
pip install requests streamlit   # streamlit only needed for the GUI
```

## Option A: GUI (no terminal commands after setup)

```
streamlit run streamlit_app.py
```

Opens a local page in your browser: paste the sheet URL, list your filters
(one per line), click **Start**. It clears the logcat buffer and starts
capturing in the background -- go operate the phone (open the app, walk
through to home). Click **Stop** when done; the report renders inline on
the same page, and is also saved as a local HTML file (path shown on
screen). This is a **local** app -- it is not a shareable web link. If you
want a shareable link, ask Claude to publish the saved report file as an
artifact in a chat turn.

One Start/Stop pass covers every `--filter` you listed at once, as long as
whatever you did on the phone during that pass actually exercises all of
them (e.g. going all the way to home covers both a splash-time filter and a
first-open filter in a single capture).

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

(Ctrl+C to stop once you've triggered what you need -- e.g. spam-tapped the
splash logo for a config dump, or run through onboarding for first-open ad
IDs.) One capture file can cover multiple `--filter` values in one run.

### 2. Run the diff

```
python check_ads.py \
  --sheet "https://docs.google.com/spreadsheets/d/<id>/edit" \
  --log capture.log \
  --filter FOR_TESTER \
  --filter VslTemplate4FirstOpenSDK \
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
  that area at all, so any "Thiếu" rows in that area might just be
  uncaptured, not actually broken. Capture again with the right filter/flow
  before trusting those rows.
- `report.html` (or the equivalent GUI output) is the same info as a
  browsable report.

## Sheet requirements

Checklist sheet must be shared "Anyone with the link can view", two columns:
column A = label (or a section header when column B is empty), column B =
expected value.

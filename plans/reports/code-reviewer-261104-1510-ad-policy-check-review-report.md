# Code Review: tools/ad-policy-check

## Scope
- Files: all `*.py` in `tools/ad-policy-check`, `policy-checkers.json`, `policy_report_template.html` (~2.5k LOC)
- Cross-checked against: `check_remote_config/src/rcr/{fo_flow,device_app,ui_dump,bot_hang_doi}.py`, real runs in `out/com.hairai.../`
- Tests: `pytest -q` → 22 passed. Map vs code: all 38 checker ids implemented, none orphaned.
- Focus: wrong statuses (false PASS first), crashes on partial runs, subprocess/adb, lock, HTML.

## Overall
The structure is solid: checkers are pure functions over saved evidence, NA/BLOCKED/CAN_XEM are used on purpose, the lock is byte-compatible with rc-check, and the HTML is escaped consistently. The main risk is in the evidence → status step. Several checkers return PASS (or NA) when the evidence cannot support it, and an interrupted or partial run produces a report that looks clean.

---

## Critical (false PASS / hidden failure / money)

### C1. Real-money purchase not guarded: Subscribe is tapped without checking for a test card
`evidence_sub_purchase.py:87`. The code taps Subscribe on any Play sheet. The comment says "every account is a license tester". That is not enforced: if a phone has a different account signed in, this is a real charge. The sheet text is already captured (`billing_sheet_texts`; the real run shows "Test card, always approves").
Fix: before `_tap_label(..., PLAY_BUY_RE)`, require a test-card marker (`re.search(r"test card|thẻ thử nghiệm", " ".join(sheet), re.I)`). If it is missing, record `result="tài khoản không phải license tester"`, BACK, and do not buy.

### C2. A run that stopped early is graded mostly NA, and the report hides it
`policy_check_runner.py:29-57`, `policy_report.py:75-106`. No checker reads `meta.error` / `meta.reached_home`. If a run stopped at splash (ForeignDriverError, timeout, crash), it yields NA for banner/native/paywall/reward ("lượt này không gặp…"). NA is excluded from "Cần xử lý", and the template never shows `meta.error`. The result looks like a clean report.
Fix: in `grade()`, when `meta.error` or `not meta.reached_home`, convert NA→BLOCKED with the prefix "lượt dừng ở {stopped_at}: …". Also render `meta.error` / `reached_home` in the header.

### C3. Leftover active test subscription from the last run silently turns all ad checks into NA
`evidence_sub_purchase.py:62-122` together with the real run `261104-144915/purchase.json` ("trang Play không có nút Cancel subscription", so the sub was NOT cancelled). `pm clear` does not clear Play entitlements. The next run on that account starts as premium: no ads, no paywall, so every ad/sub checker returns NA "không gặp".
Fix: at collect start, detect premium (e.g. `dumpsys` of Play subscriptions via rc-check's `sub_play_store`, or the paywall/"Remove ads" state) and write `meta.sub_active`. Have the runner turn NA→BLOCKED when it is set. At minimum, print a loud warning when `cancelled` is false.

### C4. `sub_privacy_tos_in_app` returns PASS when the Privacy tap did nothing
`checkers_reward_app_sub.py:129-132`. The PASS path only checks `not tap["left_app"]`. A tap that opened nothing (`handled: false`, e.g. PRIVACY_RE matched a whole sentence "By continuing you agree to our Privacy Policy" and the centre is not the link) is reported as "Privacy mở trong app".
Fix: `if not tap["handled"]: return CAN_XEM/BLOCKED "bấm Privacy không mở gì"`. Also, Chrome Custom Tabs (`com.android.chrome/...CustomTabActivity`) currently count as FAIL. Decide whether that is intended (see questions).

### C5. `native_adchoices_inside` is always PASS when the container is inferred
`ui_nodes.py:85-89` together with `checkers_native_banner.py:77-84`. The inferred native box is the bounding box of media/cta/attribution/**adchoices**, so AdChoices is inside by construction. Verified: AdChoices at x=900-960 with all content at x≤500 gives an inferred box of (0,0,960,700), so 100% "inside". The same weakness lets `native_content_overlap` treat app content sitting between parts as "inside the ad".
Fix: skip frames where `p["native"].get("inferred")` and return CAN_XEM with a screenshot. Alternatively, infer the box from media+cta+attribution only and then measure AdChoices against it.

### C6. `native_placeholder_first` returns PASS from a dump taken about 2s after entry; rule is 0.5s
`checkers_native_banner.py:135-168` (branch at 159-164). `params.max_seconds` (0.5) is never read. The first UI dump of an activity is taken roughly 1-3s after entering. If the ad loaded by then, `first.native["native"]` is truthy and the result is PASS, even if nothing was shown during the first 0.5s. The trailing note does not change the status.
Fix: PASS only if `first.t - entry_t <= max_seconds`, with `entry_t` taken from activities.jsonl. Otherwise return CAN_XEM with `video_sheet(entry_t-500, entry_t+2000, fps=4)` and the question "ô 0.5s đầu có vùng ad/placeholder?".

### C7. Activity-name format mismatch makes native/banner taps read as "handled" even when nothing happened (false PASS)
`evidence_collector.py:105` and `evidence_click_probe.py:83`. walk_to's `chup(activity, …)` activity comes from `device_app.focus` (`dumpsys window`, `mCurrentFocus=…{pkg/full.class.Name}`, i.e. `ComponentName.flattenToString()`, the full form). `_tap_and_observe` compares that string with `adb_sync.top_activity` (`dumpsys activity`, `ActivityRecord` shortComponentName, `pkg/.ui.Main`). For any app whose activities live under its own package namespace, `after != before` on the first poll, so `handled=True` and `left_app=False`. The result is PASS for `native_cta_click_handled` / `banner_click_handled`. It did not bite the Hair run only because its activities are `com.vsl.*` / `com.visionlab.*`, which differ from the package `com.hairai.*`.
Fix: normalise both sides with one helper (expand `pkg/.X` to `pkg/pkg.X`) before comparing. Also make `handled` stricter, see H4.

### C8. `resume_not_after_utility` misses a resume ad because `back_to_app` presses BACK on it before the watch starts (false PASS)
`evidence_home_explorer.py:119-129`. In the left-app path, `back_to_app()` loops: BACK from Chrome, then sees `AdActivity` (in the app's package but full-screen), so it presses BACK again. That can close the app-open ad within 1.5s. Then `_watch_for_ad()` sees nothing and records `ad_after: null`, which the checker turns into PASS.
Fix: in `back_to_app`, stop and return the activity when `is_fullscreen_ad_activity(act)`, then record it as `ad_after`. In the checker, also cross-check activities.jsonl for any full-screen ad activity between `visit.t` and the next visit (cheap and independent of the explorer).

---

## High

### H1. `inter_changes_screen` gives a false FAIL on resume/app-open ads and on single-activity (fragment) apps
`checkers_fullscreen_resume.py:32-40`. `episodes()` includes every full-screen ad: the resume ad in `_resume_pass` and ads after utility return. Those return to the same activity by design, so `before == after` gives FAIL "tắt ad mà vẫn ở màn cũ". Apps navigating by fragments inside one `MainActivity` also always FAIL.
Fix: exclude episodes that start inside `run.resume_window()` or after a launcher entry. When `before == after`, compare frame texts before/after (`frame_near`). If they are the same activity but the content differs, return CAN_XEM with a sheet, not FAIL.

### H2. Screenrecord loop goes into an unbounded spawn loop when screenrecord fails at once
`evidence_screenrecord.py:39-50`. If `screenrecord` exits immediately (unsupported `--size 540x1200` on some encoders, device offline, `/sdcard` not writable), the outer loop re-spawns `adb shell screenrecord` with no delay. Each pass appends a segment. That means thousands of adb processes and segment entries over a 5-10 min run. `stop()` then tries to pull each one with a 120s timeout.
Fix: if a segment lived less than ~5s and `_stop` is not set, sleep and count failures. After 3 failures, stop recording and write `meta.video_error`. Checkers then return BLOCKED for video-based rules.

### H3. An exception in the collector's `finally` leaks logcat and leaves no `meta.json`; Ctrl+C also leaves no meta
`evidence_collector.py:187-209`. `recorder.stop()` can raise `TimeoutExpired` (pkill 15s, pull 120s). That skips `logcat.terminate()`, so `adb logcat` keeps running and holds `logcat.txt`, and skips the meta write. `except Exception` does not catch `CancelledError`/`KeyboardInterrupt`, so `meta.json` is never written there either. Both cases end with `load_run` raising FileNotFoundError and the run cannot be graded.
Fix: wrap each cleanup step in its own try. Write `walk.json` and `meta.json` inside `finally`, with `error="interrupted"` when cancelled. Make `recorder.stop()` swallow per-segment timeouts.

### H4. `handled = after != before` is too loose for every click probe
`evidence_click_probe.py:83`. Any foreground change counts as handled: the app's own navigation (onboarding auto-advance, a container click listener), a full-screen ad closing because the CTA-word tap hit "Skip"/"Close", or a permission dialog. Each of these gives PASS for click-handled.
Fix: for `native_cta` / `banner` / `fullscreen`, handled = `left_app` (browser/Play/YouTube/other app) or a new full-screen ad activity. A plain app-activity change → record `handled: "unclear"` and let the checker return CAN_XEM.

### H5. `purchased=True` is set without checking that the purchase succeeded
`evidence_sub_purchase.py:93-99`. After tapping Subscribe and sleeping 8s, it always sets purchased. If there was a Play error, "You already own this item", a pending auth/fingerprint prompt, or a decline, the app is not premium and shows no cancel option. `sub_cancel_option_after_purchase` then returns FAIL "đã mua sub nhưng không thấy…".
Fix: set purchased only if `after_buy_texts` contains a success marker ("Subscribed", "Payment successful", "Thanh toán thành công", "Đã đăng ký"), or the app shows a premium state. Otherwise record `result` and leave it unset, so the checker returns BLOCKED.

### H6. `reward_click_handled` is hard-coded to NA
`checkers_reward_app_sub.py:186-187`. It returns NA "không gặp reward ad" even when `reward_has_watch_ad_label` found reward entry points. No reward probe exists. NA means "not applicable" and drops the rule from attention.
Fix: return BLOCKED ("chưa bấm thử reward") when any `REWARD_RE` frame exists, NA only otherwise. The same pattern applies to `resume_click_handled`: no probe of kind `"resume"` is ever written (`evidence_click_probe.py`), and resume-ad taps are logged as `"fullscreen"`, so they get counted under the inter rule.

### H7. Stale UI dumps are saved as new evidence
`evidence_collector.py:79-81` (`_dump_ui`) and `evidence_home_explorer.py:62-64` (`_dump`). Neither removes the remote file nor checks the output. When `uiautomator dump` fails ("null root node", frequent during transitions according to `rcr/ui_dump.py`), `cat` returns the previous dump. It is saved under a new timestamp and attributed to the current activity, so a native from screen A is graded as screen B (overlap, webview, placeholder checks).
Fix: `rm -f` before dumping, check `"<hierarchy" in xml`, retry once, otherwise skip the frame. rcr's `ui_dump.dump` already does this; reuse it.

### H8. Missing/drifted rule warnings never reach results or the report
`policy_check_runner.py:31`. `build_registry` returns `missing` and `drifted`, and `grade()` drops both. A reworded sheet rule is still graded by the old checker with no flag, and a removed rule's checker still runs with `rules: []`.
Fix: add `out["registry_warnings"]`, render them in the report header, and mark results of drifted checkers as CAN_XEM ("rule đã đổi chữ").

---

## Medium

- **M1. Missing-element FAILs that are really detection misses.** `checkers_native_banner.py:58` (MediaView) and `:71` (Ad label). uiautomator reports custom views (GMS `MediaView`) as `FrameLayout`, so only the `ad_media`/`media_view` ids match. The label can also be "Sponsored", "Được tài trợ", or an image. "Not found" should be CAN_XEM with the screenshot, not FAIL.
- **M2. `banner_node` matches any id containing "banner".** `ui_nodes.py:93-95`. Home promo carousels (`iv_banner`, `layoutBanner`) count as ads. The prober taps them, and the result is a false PASS for `banner_click_handled` and spurious banner overlap/placeholder results. The reverse also happens: a banner AdView with an id like `adView`/`fl_ads` is not found, so its WebView counts as an "app WebView" and `no_ad_on_webview` returns a false FAIL (`checkers_native_banner.py:93-100, 184-193`). Fix: require an AdView/WebView child or AdChoices/"Ad" marker, or an id list `banner_ad|adView|ad_view_container`.
- **M3. XML entities are not unescaped.** `ui_nodes.py:29-46`. Texts keep `&#10;`, `&gt;`, `&amp;`, `&quot;` (verified: `"Cancel&#10;anytime"`; the real purchase.json also has `&#10;` / `&gt;`). Regexes such as `CANCEL_RE`, `PRICE_RE` and "Terms &amp; Conditions" can miss, giving a false FAIL for `sub_cancel_anytime_text`. The report shows `&amp;#10;`. Fix: `html.unescape()` in `_attr`.
- **M4. Visual-queue entries with no images.** `checkers_fullscreen_resume.py:48-82, 103-113`, `checkers_reward_app_sub.py:180-184`. When `video_sheet` returns None (no imageio_ffmpeg, no segment, ffmpeg failure), the checker still returns CAN_XEM with `visual.images=[]`, and `apply_visual` (`policy_check_runner.py:60-71`) accepts a PASS for it. Fix: no images → BLOCKED "không dựng được ảnh từ video". `apply_visual` should only accept verdicts for checkers that are in the visual queue with non-empty images (and should handle a missing `reason` key).
- **M5. Video sheets ignore segment boundaries.** `policy_evidence.py:129-145`. Only the segment covering `start_ms` is used. A window that crosses the ~170s boundary is truncated, so the tail tiles are black or missing. For `inter_close_within_15s`, Claude may then say "X never appears". If ffmpeg fails, a stale `sheets/<name>.png` from an earlier grade is returned (`out.exists()`). Fix: unlink `out` first. If `end_ms > seg.start_ms + seg_duration`, concat the next segment or mark the sheet partial.
- **M6. `inter_not_before_splash` counts the ad itself as the first app activity.** `checkers_fullscreen_resume.py:19-29`, `policy_evidence.py:82-84`. `app_activities()` includes `pkg/…AdActivity` (GMA's activity runs under the app package). If a short splash (<~1s) is never sampled, `first_app` is the AdActivity, `t == start`, and the result is a false FAIL. Fix: exclude `is_fullscreen_ad_activity` in `app_activities()`. If the first app sample is the ad, return CAN_XEM with the video, not FAIL.
- **M7. `resume_window()` is a heuristic.** `policy_evidence.py:109-119`. It takes the first launcher entry after index 2. Any earlier launcher visit (BACK overshoot after a Chrome trip, walk_to "mở lại app") is taken as the resume pass, and OEM launchers such as `com.miui.home` never match. `resume_window_ads` (`checkers_fullscreen_resume.py:99-100`) only checks `"AdActivity"`, so an AppLovin/other-network resume ad gives NA "đúng luật". Fix: have `_resume_pass` write `meta.resume_pass = {"home_t", "back_t"}` and use it; use `is_fullscreen_ad_activity`.
- **M8. A full-screen tap that leaves to an unlisted app ends the episode early.** `policy_evidence.py:14, 97`. `BROWSER_PACKAGES` is narrower than `device_guard.AD_DESTINATIONS` (missing GSA, webview, intent resolver, OEM browsers). A trip to one of those ends the episode, so the duration is wrong and `before != after` counts as a PASS for "changes screen". Reuse `AD_DESTINATIONS`.
- **M9. Stale dump after re-dump failure.** `evidence_collector.py:126-133`. If the re-dump after a full-screen tap raises, the broad `except` returns the **pre-tap** xml to walk_to. The driver then acts on a screen that no longer exists and may tap the old X coordinates on the app underneath. Fix: on re-dump failure, raise an AdbError-like error so walk_to's own retry path runs.
- **M10. `_paywall_frames` does not check the package.** `checkers_reward_app_sub.py:19-27`. Matching is on markers only, so a Play activity containing "Purchase"/"Billing" (e.g. older `…lightpurchase.PurchaseActivity`) would make Play's "Cancel anytime in Subscriptions on Google Play" satisfy `sub_cancel_anytime_text`. Fix: add `f.activity.startswith(pkg + "/")`.
- **M11. `ai_result_has_report_button` returns PASS/FAIL from loose regexes.** `checkers_reward_app_sub.py:197-211`. It is mapped as `kind: visual`, but "lưu" matches "lưu ý", the bare "report" alternative matches anything, and any save+share screen counts as a result screen. Return CAN_XEM with the screenshot unless the result screen was the one confirmed by `generate_ai_result`.
- **M12. `visit_utility` counts taps that opened nothing.** `evidence_home_explorer.py:114-142`. UTILITY_RE matches "Version 1.2.3" or "update" labels. When `where == home_activity`, it still does HOME + relaunch and records "mở trong app", which supports a PASS for the utility-return rule. Skip or flag visits where the screen did not change.
- **M13. Interrupted-write tolerance.** `policy_evidence.py:153-157`, `policy_report.py:94-95`. A truncated last line in a jsonl crashes `load_run`, and a missing `activities.jsonl` crashes `build`. Use per-line try/except and `exists()` checks.
- **M14. Duplicate N° in a tab drops a rule silently.** `policy_registry.py:44, 60`. `by_key` keeps only the last rule. The first rule is neither graded nor reported as unmapped, which matters because the sheet is hand-numbered with gaps. Detect duplicates and warn, or key them as `no#2`.

## Low
- **L1. Stop race in the recorder.** `evidence_screenrecord.py:39-72`. If `stop()` runs between the outer `_stop` check and `Popen`, a new device-side screenrecord starts after `pkill`. It keeps recording for up to 170s after the lock is released, and its file is pulled while incomplete and `rm`'d while open. Fix: run a second `pkill` after `join`, or guard Popen with a lock and re-check `_stop`.
- **L2. Screenshot taken after the dump.** `evidence_collector.py:90-95`. `Evidence.save` takes the screenshot about 0.5-1s after the dump but names both with the dump's `ms`. A native that loaded in between shows in the screenshot but not in the XML. Not fixable fully; note it in visual questions or take `screencap` first.
- **L3. Foreign-package guard has no IME/OEM allowance.** `device_guard.py` `ALWAYS_ALLOWED` lacks IME packages (`com.google.android.inputmethod.latin`, `com.samsung.android.honeyboard`), `com.android.intentresolver`, and OEM permission/security apps (OPPO `com.coloros.*` / `com.oplus.*`). If such a node appears in a dump during walk_to, the run aborts with ForeignDriverError. Consider checking only the focused-window package, not every node.
- **L4. Template placeholders can be re-expanded.** `policy_report.py:100-105`. Placeholders are replaced in sequence. Sheet text containing `{{GROUPS}}` / `{{JOURNEY}}` inside ATTENTION would be expanded. This is not XSS (only own HTML), but use a single-pass `re.sub` over `{{(\w+)}}`.
- **L5. Density read outside the try.** `evidence_collector.py:156`. `int(density)` is evaluated after the whole run (in meta). Odd `wm density` output loses meta at the end. Parse it early.
- **L6. Lock path depends on rc-check's cwd.** The lock path is compatible (same msvcrt 1-byte lock), but rc-check CLIs use `--out-dir default="out"`, which is relative to cwd. If rc-check is launched from another cwd, the locks differ.

## Edge cases from scouting
- rcr's `chup` is not called for `"AdActivity"` but is called for other networks' full-screen activities. This is handled by `maybe_probe`'s full-screen branch, so it is OK.
- Real run 261104-144915: the cancel on Play failed, so the account still has an active test sub (see C3).
- `results.json` in 261104-144915 has FAIL reasons for `sub_trial_*` that no code path produces, and they have no `judged_by`. It looks hand-edited. If edits are expected, add a `judged_by: "người"` field.

## Positive
- Pure checkers over saved runs, so they can be re-graded and unit-tested; one broken checker cannot hide others (runner try/except).
- The lock reuses rc-check's exact OS lock and frees itself on process death.
- Consistent `html.escape` on every sheet, reason and path string in the report; images are base64 data URIs.
- The "first full-screen ad is never tapped" rule keeps the X-timing measurement honest.
- The regex XML parser tolerates truncated dumps.

## Recommended order
1. C1 (real money), C2 + C3 (silent NA reports), C7 + H4 (click false PASS).
2. C4, C5, C6, C8, H1, H5, H6.
3. H2, H3, H7, H8, then the Medium items.
4. Add tests: inferred-box AdChoices, unhandled privacy tap, NA→BLOCKED on `meta.error`, short/full activity-name normalisation, resume-episode exclusion.

## Metrics
- Tests: 22/22 pass; no tests for collector/explorer/purchase (device-bound), report build, or interrupted runs.
- Lint/type: not run (no config in folder).

## Unresolved questions
1. Does a Privacy link opening in a Chrome Custom Tab count as "in app" for Sub rule? Currently FAIL.
2. Are the `results.json` hand edits (sub_trial_* FAIL) intentional? If so, they need a `judged_by` marker.
3. Is a NA for sub rules when no Pro entry is found on Home acceptable, or should it be BLOCKED (does every audited app have a sub)?

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
  line. CLI and GUI share one filter list (`DEFAULT_FILTERS` in `check_ads.py`:
  `FOR_TESTER`, `VslTemplate4FirstOpenSDK`, `UserMessagingPlatform`,
  `AdsConsentManager`, `RemoteConfigRepository`, `inter_ads`,
  `loadInterstitialAd`), which covers every area the Nexus app checklist needs.
  Passing `--filter` by hand *replaces* that list, so a run with only
  `FOR_TESTER` will show the App ID, Package name, and "ID ads inapp" rows as
  "Lệch" even when they are correct.
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
- The GUI cannot publish the report to a shareable claude.ai link by itself:
  creating an artifact is a Claude Code action inside a chat turn, and a
  headless `claude -p` run has no Artifact tool. What it does instead: the
  report is always written to one fixed path (`static/adcheck-report.html`), so
  publishing it once yields a URL that stays valid -- Claude republishing that
  same path refreshes the artifact in place. Record the URL with
  `python artifact_link.py <url>` and the "Mở report toàn màn hình" button
  opens the shareable artifact from then on, warning when the artifact is older
  than the run just finished. Note the report carries the Adjust token, the
  Facebook app id/client token and every ad unit ID, so publishing sends that
  to claude.ai (artifacts are private unless shared).

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

## Chạy nhiều app, chạy định kỳ

### 1. Capture tự động (1 device, 2 luồng user)

```
python device_driver.py --package <pkg> --out session.log
```

Tự mở app, spam logo splash (bắt buộc -- không tap thì `FOR_TESTER` ra 0 dòng),
đi qua onboarding tới Home, chạy **cả hai luồng vào chung một log**: new user
(`pm clear`, ra placement FO) rồi old user (cold start, ra placement
resume/in-app). `--pass new` / `--pass old` để chạy riêng một luồng.

Điều hướng bám theo tên activity đang focus, không bám pixel. Nút đóng ads nhận
theo nhãn đa ngôn ngữ và **thử lại** tới khi màn đổi, vì nút chỉ hiện sau
countdown. Nếu tap lỡ mở sang app khác, driver phát hiện sai package và mở lại
app thay vì tưởng đã tới Home.

### 2. Audit một app

```
python check_ads.py --sheet <url+gid> --log session.log --package <pkg> --json out.json
python check_ads.py --sheet <url+gid> --apk build.apk        # không cần device
```

`--json` cho script/agent đọc; exit code 2 khi còn dòng Lệch.

### 3. Audit toàn bộ registry

`apps.json` (xem `apps.example.json`) khai sheet gốc và map mỗi app tới tab của
nó trong sheet đó:

```json
{ "sheet": "https://docs.google.com/spreadsheets/d/<id>/edit",
  "apps": [ { "label": "AI Beauty", "package": "com.example.app", "gid": "53703266" } ] }
```

```
python audit_runner.py
```

`--sheet` chỉ cần khi muốn chạy với sheet khác cái registry khai. Dạng cũ (file
là list các app, không có `"sheet"`) vẫn đọc được, nhưng lúc đó `--sheet` là bắt
buộc.

App nào `versionCode` chưa đổi so với lần trước thì **bỏ qua** -- cùng build thì
cùng kết quả. `--force` để chạy lại bất chấp. Mỗi app sinh:

- `snapshots/<package>.json` -- baseline cho lần sau
- `out/<package>-triage.json` -- delta (dòng mới lệch / đã fix / ID lạ mới) và
  các dòng tool không tự kết luận được, chia theo loại

Phần audit từ APK không đụng device nên chạy song song giữa các app; phần
capture cần máy thì phải tuần tự vì chỉ có một máy:

```
python audit_runner.py --capture
```

`--capture` tự lái máy cho từng app (cả hai luồng user) rồi audit trên đúng log
vừa ghi, một app một lượt. Log để ở `out/<package>-capture.log`. Luồng nào
không tới được Home thì bản tóm tắt nói rõ -- các dòng "chưa thấy trong log"
của lượt đó không đáng tin.

Lưu ý: kể cả lượt APK-only vẫn cần máy cắm, vì `versionCode` đọc từ `dumpsys`
và base APK phải pull về. "Device-free" ở đây nghĩa là không lái UI, không phải
không cần máy.

### 3b. Chạy theo lịch

```
./scheduled-audit.sh
```

Wrapper cho cron: ghi mọi lượt vào `out/scheduled-audit.log`, nhưng **chỉ in ra
stdout khi có dòng mới lệch hoặc lỗi** -- cron gửi mail theo stdout, nên lượt
không có gì đổi thì im lặng. Không có máy cắm thì bỏ lượt và exit 0 thay vì báo
lỗi. Log tự cắt ở 5000 dòng.

Dòng crontab hàng ngày 9h:

```
0 9 * * * /path/to/tools/ad-checklist-diff/scheduled-audit.sh
```

URL sheet lấy từ registry, nên không phải khai lại ở đây -- đổi sheet là sửa
một chỗ. Env đổi được: `AD_AUDIT_SHEET` (chạy sheet khác), `AD_AUDIT_PYTHON`,
`AD_AUDIT_LOG`, `AD_AUDIT_LOG_LINES`, `AD_AUDIT_ADB_PATH`.

### 4. Lớp agent (tuỳ chọn)

`.claude/workflows/audit-fanout.mjs` -- một agent mỗi app, chỉ đọc các dòng
trong triage, kết luận (checklist sai / build thiếu / chưa capture đủ) rồi một
lượt phản biện từng kết luận. Phần diff vẫn là Python: agent không làm lại việc
mà `grep` đã làm đúng.

Chạy trong Claude Code, mở phiên **tại thư mục gốc repo** rồi gõ:

```
chạy workflow audit-fanout cho các app trong registry
```

Phải nói rõ chữ "workflow" -- đây là lớp multi-agent, tốn token, nên nó không tự
kích hoạt. Script không đọc được file (sandbox, không có filesystem), nên phiên
gọi phải đọc `apps.json` và truyền `args.apps`; không truyền thì workflow dừng
ngay với thông báo, thay vì trả report rỗng trông như "không có lỗi nào".

Chạy `audit_runner.py` **trước**: workflow chỉ đọc `out/<package>-triage.json`,
nó không tự audit. Triage sinh từ lượt APK-only có các dòng "chưa thấy trong
log" không có thật -- cho agent ăn triage đó là nó phán trên dữ liệu rác.

### 5. Báo cáo artifact

`artifact_report_builder.py` dựng trang HTML để gửi cho người giữ checklist --
khác `report_renderer.py` (trang cho người chạy tool): nó mở đầu bằng điểm số
(bao nhiêu dòng khớp / lệch), rồi mới tới bảng từng section.

```
.venv/bin/python tools/ad-checklist-diff/artifact_report_builder.py <package> \
  --findings out/<package>-findings.html \
  --notes    out/<package>-notes.html \
  --highlight 2733004612
```

Phần sinh từ snapshot: điểm số, chip từng section, bảng đầy đủ mọi dòng, danh
sách ID build dùng mà sheet không có. Phần `--findings` / `--notes` viết tay mỗi
lượt, vì thứ fan-out chứng minh được mỗi lần một khác -- generate nó ra thì
thành bịa. Không truyền cũng chạy, ra trang thuần cơ học.

`--highlight` nhận đuôi ID: ID nào phần điều tra đã giải thích thì được trỏ
ngược về đó trong danh sách leftover, phần còn lại để trống chứ không đoán.

Tên app lấy từ `label` trong `apps.json`; không có entry thì dùng package.

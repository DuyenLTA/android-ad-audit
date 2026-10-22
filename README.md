# android-ad-audit

Đối chiếu checklist quảng cáo (Google Sheet của ads team) với thứ app Android thật sự chạy:
ID ad unit, placement, cấu hình. Bằng chứng lấy từ logcat khi lái app trên máy thật và từ
chuỗi trong APK. Kết quả là một trang artifact cho ads team và một report markdown trong
`plans/reports/`.

## Cần gì trước khi chạy

1. **Python 3.12+**
2. **Android platform-tools** (`adb`) trong PATH, và **build-tools** (`aapt2`) để đọc App ID
   trong APK
3. **Điện thoại Android** bật USB debugging, đã cài **bản release** của app cần audit
   (bản dev bị chặn, exit 3)
4. **Claude Code** nếu chạy cả workflow `/audit-fanout` (lớp agent judge/verify)

## Cài đặt

```bash
git clone <repo> ~/android-ad-audit && cd ~/android-ad-audit
python -m venv .venv
# Windows: .venv/Scripts/python   ·   macOS/Linux: .venv/bin/python
.venv/Scripts/python -m pip install -r requirements.txt
cp tools/ad-checklist-diff/apps.example.json tools/ad-checklist-diff/apps.json
```

Sửa `apps.json`: `sheet` là link Google Sheet checklist. Danh sách `apps` có thể để trống,
`find_app.py` tự tìm tab theo dòng `Package name` trong sheet.

Cài lệnh cho Claude Code (mỗi máy một lần; lệnh mới hiện ở phiên mở sau đó):

```bash
cp .claude/commands/audit-fanout.md ~/.claude/commands/
```

Repo không nằm ở `~/android-ad-audit` thì đặt `AD_AUDIT_REPO=<đường dẫn repo>`.

## Chạy

```
/audit-fanout <package>            # capture trên máy + so checklist + agent kiểm
/audit-fanout <package> --apk      # chỉ quét APK, không lái máy
/audit-fanout <package> --force    # chạy lại dù build và checklist không đổi
```

Không có Claude Code thì chạy phần code trực tiếp:

```bash
.venv/Scripts/python tools/ad-checklist-diff/find_app.py --exact <package>
.venv/Scripts/python tools/ad-checklist-diff/audit_runner.py --capture --package <package>
```

## Thông báo Discord

Workflow báo lên Discord khi dừng giữa chừng (sai build, lỗi runner, thiếu tab, còn dòng cần người xem) và khi report được publish.

1. Tạo webhook: Discord, Server Settings, Integrations, Webhooks, New Webhook, chọn kênh, Copy Webhook URL.
2. Đặt biến môi trường (không commit URL vào repo):
   ```bash
   export DISCORD_WEBHOOK_URL='https://discord.com/api/webhooks/<id>/<token>'
   export DISCORD_ADS_TEAM_MENTION='<@&roleid>'   # tuỳ chọn: tag role ads team ở tin báo lỗi (hoặc <@userid>)
   ```
3. `DISCORD_NOTIFY=0` tắt hẳn việc gửi. Không đặt `DISCORD_WEBHOOK_URL` thì tool chỉ in một dòng cảnh báo rồi bỏ qua; gửi lỗi không bao giờ đổi exit code của lượt audit.

Gửi tay: `.venv/Scripts/python tools/ad-checklist-diff/discord_notify.py --kind stop --title "..." --line "..."`.

## Test

```bash
cd tools/ad-checklist-diff && ../../.venv/Scripts/python -m pytest -q
```

## Tài liệu

- `tools/ad-checklist-diff/README.md`: CLI, cách đọc kết quả, yêu cầu với sheet, chạy định kỳ
- `docs/audit-fanout-usage-guide.html`: hướng dẫn vận hành workflow
- `docs/kb-changelog.md`: lịch sử thay đổi quy tắc và bài học sau mỗi lỗi
- `docs/usage-log.md`: các lượt audit đã chạy
- `plans/reports/`: report từng lượt audit

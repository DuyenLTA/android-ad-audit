#!/usr/bin/env bash
# Một lượt audit định kỳ, device-free (APK-only), dành cho cron.
#
# Cron gửi mail mỗi khi job in ra stdout, nên script này im lặng khi không có
# gì đổi: mọi lượt đều ghi vào log, nhưng chỉ in ra khi audit_runner báo có
# dòng mới lệch (exit 2) hoặc lỗi (exit 1). Đúng tinh thần "chỉ báo thay đổi".
#
# Dùng:
#   AD_AUDIT_SHEET=<url sheet gốc> ./scheduled-audit.sh
#   ./scheduled-audit.sh <url sheet gốc>
set -uo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHEET="${1:-${AD_AUDIT_SHEET:-}}"
PYTHON="${AD_AUDIT_PYTHON:-$DIR/../../.venv/bin/python}"
LOG="${AD_AUDIT_LOG:-$DIR/out/scheduled-audit.log}"
MAX_LOG_LINES="${AD_AUDIT_LOG_LINES:-5000}"

if [ -z "$SHEET" ]; then
  echo "Thiếu URL sheet: đặt AD_AUDIT_SHEET hoặc truyền làm tham số đầu" >&2
  exit 64
fi
if [ ! -x "$PYTHON" ]; then
  echo "Không thấy python: $PYTHON (đặt AD_AUDIT_PYTHON)" >&2
  exit 64
fi

mkdir -p "$(dirname "$LOG")"

# adb chạy dưới cron không kế thừa PATH của shell đăng nhập; audit_runner cần
# nó để đọc versionCode và kéo APK về.
export PATH="${AD_AUDIT_ADB_PATH:-$HOME/Android/Sdk/platform-tools}:$PATH"

# Ngay cả lượt "APK-only" cũng cần máy cắm: versionCode đọc từ `dumpsys` và
# base APK phải pull về. Không có máy thì lượt này không làm được gì -- đó là
# chuyện bình thường của một cái máy để bàn, không phải lỗi đáng gửi mail.
if [ "$(adb get-state 2>/dev/null)" != "device" ]; then
  echo "=== $(date -Iseconds) (bỏ lượt: không có device) ===" >> "$LOG"
  exit 0
fi

output="$(cd "$DIR" && "$PYTHON" audit_runner.py --sheet "$SHEET" 2>&1)"
status=$?

{
  echo "=== $(date -Iseconds) (exit $status) ==="
  printf '%s\n' "$output"
} >> "$LOG"

# Giữ log khỏi phình vô hạn mà không cần logrotate.
if [ "$(wc -l < "$LOG")" -gt "$MAX_LOG_LINES" ]; then
  tail -n "$MAX_LOG_LINES" "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi

# Im lặng khi mọi thứ bình thường; cron chỉ gửi mail khi thực sự có chuyện.
if [ "$status" -ne 0 ]; then
  printf '%s\n' "$output"
fi
exit "$status"

# Phase 01 — Headless audit engine

## Context Links
- Code: `tools/ad-checklist-diff/check_ads.py`, `apk_verifier.py`, `apk_source.py`,
  `package_verifier.py`, `streamlit_app.py`
- Phase sau: [phase-02](phase-02-device-driver-automation.md)

## Overview
- Priority: P0 (chặn mọi phase sau)
- Status: Chưa bắt đầu
- Biến tool thành engine có đầu ra máy đọc được, chạy được không cần GUI và
  không cần device.

## Key Insights
- APK verify + package verify đang bị khoá trong GUI (`streamlit_app.py:198,202`),
  CLI không gọi được.
- CLI chỉ có `--sheet --log --filter --out`, không có đầu ra JSON → agent buộc
  phải parse HTML.
- Device chỉ cần cho: capture logcat, pull APK, `pm list packages`. Cho APK làm
  input thì nhánh ID rows chạy device-free, fan-out không giới hạn.
- Mỗi app = 1 tab trong cùng sheet (`gid`) → cần registry map package → gid.

## Requirements
Functional:
- `--json <path>`: dump nguyên `result` (sections/rows/found/note + leftover_ids).
- `--package <pkg>`: bật package verify + APK verify (pull/cache theo versionCode).
- `--apk <path>`: verify từ file APK có sẵn, **không gọi adb**.
- `--log` thành optional: không có log thì chỉ verify từ APK.
- Exit code: 0 = khớp hết, 2 = còn Lệch, 1 = lỗi thật (sheet/IO).
- `apps.json` registry: `{package, gid, label}` (+ field cho phase 02).
Non-functional:
- GUI và CLI dùng **chung một** đường pipeline (DRY), không copy logic.
- File < 200 dòng; tách module theo ranh giới rõ.

## Architecture
`audit_pipeline.py` (mới) — `run_audit(sheet_url, filters, log_path=None,
package=None, apk_path=None, use_device=True) -> (result, empty_filters)`.
Cả `check_ads.py` (CLI) và `streamlit_app.py` (GUI) gọi hàm này.
`app_registry.py` (mới) — load/validate `apps.json`.

## Related Code Files
Sửa: `check_ads.py` (argparse + main), `streamlit_app.py` (gọi pipeline chung).
Tạo: `audit_pipeline.py`, `app_registry.py`, `apps.example.json`,
`test_audit_pipeline.py`, `test_app_registry.py`.
Xoá: không.

## Implementation Steps
1. Tách `audit_pipeline.run_audit()` từ logic đang nằm trong `streamlit_app.py`.
2. `check_ads.py`: thêm `--json/--package/--apk`, `--log` optional, exit code.
3. `streamlit_app.py` gọi `run_audit()` thay vì tự compose.
4. `app_registry.py` + `apps.example.json`.
5. Tests cho pipeline (log-only / apk-only / cả hai) và registry.

## Todo List
- [ ] `audit_pipeline.run_audit()`
- [ ] CLI flags + exit code
- [ ] GUI chuyển sang pipeline chung
- [ ] registry + example
- [ ] tests xanh

## Success Criteria
- `python check_ads.py --sheet <url> --apk <file> --json out.json` chạy xong
  **không cắm máy**, exit code đúng, JSON đọc được.
- GUI giữ nguyên hành vi (suite hiện tại vẫn xanh).

## Risk Assessment
- Regression ở GUI khi refactor → giữ test `test_streamlit_app.py` làm chốt.
- `--apk` trỏ file sai build → note đã ghi rõ nguồn xác nhận, không im lặng.

## Security Considerations
- JSON chứa Adjust token / FB token như report → không commit (gitignore).

## Next Steps
Phase 02 dùng chung registry; phase 03 tiêu thụ JSON.

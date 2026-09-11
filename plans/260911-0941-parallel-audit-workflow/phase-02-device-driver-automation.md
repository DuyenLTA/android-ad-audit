# Phase 02 — Device driver automation

## Context Links
- Phase trước: [phase-01](phase-01-headless-audit-engine.md)
- Code hiện có: `tools/ad-checklist-diff/streamlit_app.py` (capture thủ công)

## Overview
- Priority: P1
- Status: Chưa bắt đầu
- Tự mở app, spam logo lấy log tester, đi qua onboarding tới Home, dừng capture
  — không cần người bấm.

## Key Insights (đo thực tế)
- Không tap gì: `FOR_TESTER = 0`. Spam tap `540,1000`: `FOR_TESTER 53`,
  `_CONFIG 8`, `_LOAD_AD 23` → **spam logo là bắt buộc**, không phải tuỳ chọn.
- `dumpsys window | grep mCurrentFocus` cho tên activity → tín hiệu tin cậy để
  biết đang ở màn nào và khi nào tới Home (không đoán theo pixel).
- `uiautomator dump` + `input tap` đều có trên device thật → tap theo element
  (`resource-id`, `text`, `content-desc`), không tap mù.
- Chuỗi màn thật: Splash → Onboarding (`id/btnNextOnboarding`) → Question →
  `gms.ads.AdActivity` → Billing ("Continue with ads") → MainActivity.
- Splash ~5s, `uiautomator dump` ~1s → giai đoạn splash phải tap theo toạ độ,
  qua splash rồi mới element-based.
- 2 luồng: **new user** cần `pm clear` (ra ads FO), **old user** launch thường.

## Requirements
Functional:
- `device_driver.py --package <pkg> [--serial S] [--fresh] [--out log] [--timeout N]`
- `--fresh`: `pm clear` trước khi mở (luồng new user). Không có = old user.
- Spam logo theo toạ độ cấu hình được (mặc định tâm màn theo `wm size`).
- Điều hướng theo activity: onboarding → next; billing → continue with ads;
  AdActivity → **không tap**, chờ; Home → dwell rồi dừng.
- Xuất log capture + summary các activity đã đi qua.
Non-functional:
- Không hardcode app; cấu hình per-app trong `apps.json`.
- Phần thuần logic phải test được không cần device (inject shell fn).

## Architecture
`device_ui.py` — primitive: `focused_activity()`, `ui_dump()`, `find_node()`,
`tap_node()`, `tap_xy()`, `screen_size()`; nhận `run` (shell fn) để test.
`device_driver.py` — vòng lặp: poll activity → chọn action theo bảng rule →
dừng khi tới `home_activity` hoặc hết timeout.

## Related Code Files
Tạo: `device_ui.py`, `device_driver.py`, `test_device_ui.py`,
`test_device_driver.py`. Sửa: `apps.example.json` (thêm `splash_tap`,
`home_activity`, `flow_rules`).

## Implementation Steps
1. `device_ui.py` + test parse bounds/node (fixture XML thật).
2. `device_driver.py`: fresh/returning, spam logo, loop điều hướng, dwell, stop.
3. Rule table nạp từ registry, mặc định theo template VSL.
4. Chạy thật trên `99261FFAZ0077C`, đối chiếu `FOR_TESTER` > 0 và tới được Home.

## Todo List
- [ ] `device_ui.py` + tests
- [ ] `device_driver.py` + tests
- [ ] registry fields cho flow
- [ ] verify thật 2 luồng (fresh / returning)

## Success Criteria
- Một lệnh, không người can thiệp → log có `FOR_TESTER` > 0 và focus cuối là
  `home_activity`.
- `--fresh` cho ra được các dòng section "ID ads FO".

## Risk Assessment
- Toạ độ logo khác nhau giữa app → để trong registry, mặc định tâm màn.
- Onboarding đổi theo version → điều hướng theo activity + element, không pixel;
  không match được thì log rõ "không nhận ra màn X", không tap bừa.
- `pm clear` **xoá dữ liệu app** (logout, mất state) → chỉ khi có `--fresh`.

## Security Considerations
- `pm clear` là phá dữ liệu → bắt buộc flag tường minh, in cảnh báo.

## Next Steps
Phase 03: agent fan-out gọi driver (queue) + engine (device-free).

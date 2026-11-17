# Audit-fanout — fitness.workout.aitraining.abs.exercises (261117)

- Run: wf_bf9d0e06-b98 · mode: capture (--force) · serial 99261FFAZ0077C (Pixel 4) · app 1.1.0 (vc 2)
- Checklist: tab gid=422709729 (từ sheet, chưa có trong apps.json)
- Kết quả runner: 65/66 khớp, 1 lệch.
- confirmed 1 · disputed 0 · unresolved 0.

## Confirmed
**App ID (1. Thông số kỹ thuật)**: verdict checklist-sai, đã qua phản biện.
- Sheet: `ca-app-pub-4973559944609228~9567330377`
- Build: `ca-app-pub-4584260126367940~5371562314`
- Bằng chứng: manifest APK (note triage) ghi ID của build. Runtime PID 19817 (SplashActivity), UMP `Received app ID: ca-app-pub-4584260126367940~5371562314` ở capture.log:832; lượt mở lại PID 23845 ra cùng ID (17170/17172). Chuỗi publisher 4973559944609228 xuất hiện 0 lần trong log. Mọi ad unit của build đều thuộc publisher 4584260126367940.
- UMP `no form(s) configured` là cấu hình tài khoản/PO, không tính.

## Ghi chú lượt chạy
- missed_home=["new"]: lượt user mới không tới Home. empty_filters: RemoteConfigRepository, inter_ads. Không ảnh hưởng dòng App ID (UMP đọc ở Splash).
- Delta so lượt trước: sheet thêm 12 dòng, bớt 4 dòng; broke 1 (App ID).

## Tool gap
- build_ad_ids chỉ chứa App ID giữ chỗ `ca-app-pub-0000000000000000~0000000000`, không có App ID thật → delta xếp ID thật vào new_leftover_ids. Nghi bộ quét ID không phân giải APPLICATION_ID trỏ @string trong resources.arsc. Chưa xác nhận.
- Lệnh `/audit-fanout` chưa nói tới `args.python` (bắt buộc) và `args.serial` (cần khi cắm 2 máy). Lượt đầu wf_db5b48c6-6b1 hỏng vì thiếu python.

## Unresolved questions
- Có cần sửa bộ quét build_ad_ids để đọc App ID qua @string không?

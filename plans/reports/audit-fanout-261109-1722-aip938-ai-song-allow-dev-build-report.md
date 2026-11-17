# Audit ID ads — aisong.generator.creatsong.music (AIP938 AI Song 2.3.0)

- Lệnh: audit_runner.py --capture --serial 3454184009000HI --allow-dev-build --force (chạy tay, không qua workflow vì workflow chưa có cờ allow-dev-build) · 2026-11-09 17:25 · versionCode 14 · tab gid=1748014371 · vivo V2143
- Lý do: lượt Next-Gen của bot (16:04) dừng audit vì build in `Config variant dev: true` (lần mở lại) dù lần mở đầu in `dev: false`. Lượt này dev_build_signals rỗng.
- New + old user đều tới Home (có paywall VslBillingActivity, đóng X).

## Kết quả
- 54/54 khớp. App ID ca-app-pub-4973559944609228~1585158338 khớp.
- leftover 4 ID in-app, đều có "starting load ad" thật; sheet mục 3 trống:
  - Interstitial 7591275435, 7891648013; Banner 6006731028 (Home, mới so với lượt trước), 7923437602.

## Câu hỏi chưa giải quyết
- Build có phải bản release thật (log mâu thuẫn dev true/false)? Cần dev xác nhận.
- Danh sách in-app chính thức để điền mục 3.

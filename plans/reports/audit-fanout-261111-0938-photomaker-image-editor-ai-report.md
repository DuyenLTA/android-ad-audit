# Audit fanout — photomaker.image.editor.ai (versionCode 5)

Run: wf_440bdb90-811 · mode capture (pm clear, capture mới 11/11/2026, lượt new + old đều tới Home) · tab sheet gid=337152191 (chưa có trong registry)

## Thống kê
- 56/56 dòng sheet khớp build · lệch 0 · chưa kết luận 0
- confirmed 0 · disputed 0 · unresolved 0 → **sạch**
- missed_home 0, dev_build_signals 0, apk_scan_applicable=true
- Lần audit đầu của app (delta: 56 dòng mới, broke 0, fixed 0)

## Ngoài checklist (chiều build → sheet)
- 20 ID 4973559944609228 có trong build (APK + log) mà sheet không ghi; 2 ID trong đó thấy nạp lúc chạy (delta 'ID lạ mới'):
  - ca-app-pub-4973559944609228/9289184690 — AppResumeManager load inter (capture.log ~09:39:19.961), load fail
  - ca-app-pub-4973559944609228/5022636622 — AppResumeManager load inter (capture.log ~09:39:21.917), load fail
- Cả 2 đều do AppResumeManager gọi → nhiều khả năng ID inter resume / dự phòng. Cần ads-team xác nhận có thuộc checklist không.

## Cảnh báo capture
- Filter RemoteConfigRepository, inter_ads không khớp dòng log nào → vùng đó chưa capture (không ảnh hưởng 56/56)

## Câu hỏi chưa giải quyết
- 18 ID còn lại chỉ thấy trong APK: có thuộc placement cần checklist không?
- 2 ID inter AppResumeManager (9289184690, 5022636622) có phải ID hợp lệ cần bổ sung vào sheet không?

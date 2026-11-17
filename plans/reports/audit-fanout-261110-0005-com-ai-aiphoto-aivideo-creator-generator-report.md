# Audit ID ads — com.ai.aiphoto.aivideo.creator.generator (Gravida 1.3.0, versionCode 6) — lượt rc-check 10/11 00:05

- Chế độ: capture, serial 3454184009000HI, run `wf_60739474-8b9`. Runner báo "build và checklist đều chưa đổi" → dùng
  lại triage + capture lúc 09/11 22:58 (cùng build, cùng sheet; capture tới Home, missed_home rỗng).
- empty_filters: RemoteConfigRepository (không ảnh hưởng dòng lệch)
- Kết quả: **53/54 khớp**, 1 lệch. confirmed 0 · disputed 1 · unresolved 0 (y như lượt 22:54)

## Dòng lệch: 502_native (4. ID ads resume)

- Sheet: `ca-app-pub-4973559944609228/2199612256` — không có trong APK (71 ad unit ID quét được).
- Build: log `FO_VslTemplate4FirstOpenSDK` in `AppResume native high` và `AppResume native` cùng là
  `ca-app-pub-4973559944609228/8349253480` (= ID 502_native_high).
- Judge: checklist-sai. Verify: không đứng — các cặp AOA/inter đều có 2 ID riêng; chỉ native trùng ID high → nghiêng về
  build gán nhầm. Cần dev / ads-team xác nhận.

## Ghi chú

- Phiên bot không có công cụ publish artifact → trang audit chỉ dựng file local, chưa đè link cũ
  https://claude.ai/artifact/8Bop5rhuJ5y1W3KypLFXzY.

## Câu hỏi còn lại

- ID đúng của 502_native?

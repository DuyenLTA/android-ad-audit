# Audit ID ads — com.ai.aiphoto.aivideo.creator.generator (1.3.0, versionCode 6)

- Chế độ: capture (pm clear, lái máy 99261FFAZ0077C — Pixel 4), run `wf_958e1a9a-44a`
- Tới Home: có (missed_home rỗng). empty_filters: RemoteConfigRepository (không ảnh hưởng dòng lệch)
- Kết quả: **53/54 khớp**, 1 lệch. confirmed 0 · disputed 1 · unresolved 0

## Dòng lệch: 502_native (4. ID ads resume)

- Sheet: `ca-app-pub-4973559944609228/2199612256` — không có trong APK (71 ad unit ID quét được).
- Build: log app (`FO_VslTemplate4FirstOpenSDK`, 2 lần mở) in `AppResume native high` **và** `AppResume native` cùng là
  `ca-app-pub-4973559944609228/8349253480` (= ID của dòng 502_native_high, khớp sheet).
- Judge: nhãn checklist-sai. Verify: **không đứng** — mọi cặp high/thường khác (aoa 6375101928/7363468701, inter
  8246145851/8786211068) dùng 2 ID riêng; chỉ native trùng ID high → nghiêng về build gán nhầm ID high cho slot thường.
- Việc cần làm: dev / ads-team xác nhận ID đúng cho 502_native (2199612256 theo sheet hay 8349253480 như build).

## Ghi chú

- Phiên chạy bot không có công cụ publish artifact → chưa cập nhật trang audit cũ
  (https://claude.ai/artifact/8Bop5rhuJ5y1W3KypLFXzY).

## Câu hỏi còn lại

- ID đúng của 502_native?

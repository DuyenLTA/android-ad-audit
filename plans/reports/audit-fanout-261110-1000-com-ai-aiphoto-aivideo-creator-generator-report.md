# Audit fanout — com.ai.aiphoto.aivideo.creator.generator (Gravida 1.3.0, vc 6)

- Run: wf_9dae0b98-802 · mode capture · máy 99261FFAZ0077C (pm clear, tới Home đủ luồng)
- Khớp 53/54, lệch 1 · confirmed 0 · disputed 1 · unresolved 0

## 502_native (4. ID ads resume) — disputed
- Sheet: ca-app-pub-4973559944609228/2199612256 — không có trong 71 ID quét từ APK.
- App: log FO_VslTemplate4FirstOpenSDK "AppResume native high" và "AppResume native" đều = …/8349253480 (capture.log 18521/18523, lặp 27358/27359).
- Agent điều tra gắn "checklist-sai"; phản biện bác: mọi cặp high/thường khác tách ID (aoa 6375101928/7363468701, inter 8246145851/8786211068), chỉ native trùng → nghi app gán nhầm. Cần dev/ads-team xác nhận.

## Tool gap
- Phép "ID không có trong APK" mặc định note "nghi checklist sai"; thiếu phép so ID runtime với slot anh em để gắn cờ "trùng ID giữa 2 slot".

## Câu hỏi còn lại
- ID đúng của 502_native là 2199612256 hay 8349253480?

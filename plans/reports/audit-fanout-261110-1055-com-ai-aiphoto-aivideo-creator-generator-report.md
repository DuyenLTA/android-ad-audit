# Audit fanout — com.ai.aiphoto.aivideo.creator.generator (Gravida 1.3.0, vc 6)

- Run: wf_385ce3a5-1cd · mode capture (runner bỏ capture: build + checklist chưa đổi từ 09/11, dùng capture 09/11 22:58) · máy 3454184009000HI
- Khớp 53/54, lệch 1 · confirmed 1 · disputed 0 · unresolved 0 · gọi từ /rc-check (bot)

## 502_native (4. ID ads resume) — confirmed (checklist-sai theo agent)
- Sheet: ca-app-pub-4973559944609228/2199612256 — không có trong 71 ID quét từ APK, 0 dòng trong capture.log.
- Build: log FO_VslTemplate4FirstOpenSDK (pid app) "AppResume native high" và "AppResume native" đều = …/8349253480 (capture.log 18521/18523, lặp 27358/27359).
- Lượt 09/11 (wf_9dae0b98-802) cùng dòng này ra disputed (mọi cặp high/thường khác tách ID). Lượt này verify giữ luận điểm. Cần dev/ads-team xác nhận ID đúng.

## Câu hỏi còn lại
- ID đúng của 502_native: 2199612256 (sheet) hay 8349253480 (build, trùng ID high)?

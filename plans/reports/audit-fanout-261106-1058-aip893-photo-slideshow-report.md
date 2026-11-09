# Audit fan-out — com.aiphotogenerator.aivideomaker.photoslideshow (AIP893)

- Run: wf_5fd9f1f6-990 · mode: capture, nhưng runner bỏ recapture vì versionCode 15 + checklist chưa đổi → dùng capture 2026-11-04 15:48
- Tab sheet gid=1025167497 (chưa có trong registry) · v2.5.0 · old user không tới Home ở lượt capture đó (missed_home=['old'])

## Kết quả
- 53/54 khớp, 1 lệch: App ID.
- confirmed 1 · disputed 0 · unresolved 0.

## Confirmed — App ID
- Sheet: ca-app-pub-4973559944609228~6208580384. APK v15 không có chuỗi này, không có cả publisher 4973559944609228.
- Build: ca-app-pub-4584260126367940~8521911202 trong AndroidManifest.xml; UMP lúc chạy dùng ID này (6 lần trong capture.log, 0 lần publisher 4973…). Mọi ad unit trong checklist thuộc publisher 4584260126367940.
- Phát biểu: cần ads-team xác nhận App ID nào đúng.
- UMP "no form(s) configured" = cấu hình tài khoản, không chấm.

## leftover_ids (build có, sheet không khai) — 15
- App ID ~8521911202 + 14 ad unit in-app. Grep capture.log: cả 14 đều có dòng FOR_TESTER_LOAD_AD "starting load ad" thật (không phải chỉ dump cấu hình).
- Sheet mục "3. ID ads inapp" trống → không có dòng nào để đối chiếu.
- Interstitial: 4712346794, 6359027428 (cặp double-id), 2753217739, 3055378098, 3611323665, 4725506819, 5379381072, 5577847735, 6064684815, 7251696528, 7550568673, 9549852848. Native: 1962820838, 6098147590. Banner: 6389210412.
- Phụ: 4712346794 trả "Publisher data not found" lúc load (15:46:52). Không chấm, chỉ ghi lại.

## Câu hỏi chưa giải quyết
- App ID nào đúng (ads-team/AdMob).
- Danh sách in-app chính thức để điền mục 3.
- Muốn capture mới thì chạy lại với --force (lượt này dùng lại capture 04/11).

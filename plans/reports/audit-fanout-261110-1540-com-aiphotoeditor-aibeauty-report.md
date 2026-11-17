# Audit ID ads · com.aiphotoeditor.aiphotogenerator.aivideogenerator.aibeauty (Lynix 4.5.0 (42))

Run wf_285ae1b3-c27 · mode capture (runner dùng lại capture 14:45 cùng build + sheet, triage audited_at 07:45:46Z) · máy 3454184009000HI.

## Kết quả
- Khớp 71/76.
- confirmed (2) — slot 306 inter OB4 → Question:
  - 306_onb4_n_inter_high: sheet 6463782247 (không có trong APK) → build 6620824217. Bằng chứng capture.log dòng 13613 `loadInterstitialAd: …/6620824217 - …/5307742543` (DoubleIds, pid app, VslTemplate4QuestionActivity); 14638 load OK; 16226 FOR_TESTER_SHOW_AD INTERSTITIAL 6620824217.
  - 306_onb4_n_inter: sheet 2221284903 (không có trong APK) → build 5307742543 (nửa normal của cặp, chưa load riêng vì high đã fill).
- disputed: 0.
- unresolved (1 nhóm, 3 dòng in-app): inter_feature_high 3076727342, inter_result_high 9669665559, inter_result 3169954399 — không có trong APK, build không còn ID dư để thay; luồng capture chưa tới Home/Result; không lấy được APK cho apk_strings.py. Cần ads-team/dev xác nhận placement có cần nhúng không.

## Việc cần làm
- ads-team xác nhận cặp ID inter OB4 (sheet 6463782247/2221284903 vs build 6620824217/5307742543).
- dev/ads-team xác nhận 3 ID inter in-app.

## Câu hỏi chưa giải quyết
- 3 ID in-app: sheet sai hay build thiếu placement.

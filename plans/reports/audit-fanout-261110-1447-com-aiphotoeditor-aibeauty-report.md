# Audit fanout — com.aiphotoeditor.aiphotogenerator.aivideogenerator.aibeauty (Lynix 4.5.0, vc 42)

Run: wf_832ef189-2ed · mode capture (pm clear app) · máy 3454184009000HI · 10/11/2026 14:42

## Confirmed (checklist-sai)
- 306_onb4_n_inter_high: sheet .../6463782247 → build .../6620824217
- 306_onb4_n_inter: sheet .../2221284903 → build .../5307742543
- Bằng chứng: capture.log pid 8150 dòng 13613–13615 (`loadInterstitialAd: 6620824217 - 5307742543`, `loadInterstitialAdDoubleIds`) ngay sau rời VslTemplate4Onboarding42Fragment; 14638 load OK; 16226 FOR_TESTER_SHOW_AD. 2 ID sheet không có trong build_ad_ids (80 ID, apk_scan_applicable=true).

## Disputed (cần người xem)
- inapp inter_feature_high (3076727342), inter_result_high (9669665559), inter_result (3169954399): không có trong APK. Agent gán "chưa capture đủ"; verify bác: vắng trong APK là quyết định → "không có trong build" (checklist-sai hoặc build-thiếu). Tách được bằng apk_strings tìm tên placement (lượt audit không lấy được APK).

## Ghi chú
- Capture chưa tới Home (missed_home new/old), filter inter_ads rỗng.
- delta: fixed Adjust env + App ID; new_leftover 5307742543, 6620824217.

## Câu hỏi chưa giải quyết
- 3 ID inapp: sheet sai hay build thiếu placement?

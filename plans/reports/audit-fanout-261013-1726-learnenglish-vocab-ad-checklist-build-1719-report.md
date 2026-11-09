# Audit checklist ads — learnenglish.language.learningvocabulary.practice (bản cài 17:19)

- Run: `wf_50488f81-9f5` · mode `capture` (`--force`) · 2026-10-13
- Build: version_code `2` (cài 17:19:41) · audited_at `2026-10-13T10:24:36+00:00`
- Sheet tab: gid `1919567600` · `missed_home=[]` · `empty_filters`: `RemoteConfigRepository`, `inter_ads`
- So với lượt 17:07 (`wf_0ad473e7-920`, 48/56): fixed 5, broke 0, new_leftover_ids 4

## Thống kê

Tool: 53/56 (lệch 3, đều mục 2 FO). **Thực tế 48/56**: 5 dòng `102-spl-*-inter` khớp giả.

## Khớp giả: 5 dòng inter splash (tự kiểm lại trên log)

ID sheet chỉ có trong dump cấu hình FO in sau onboarding: capture.log:14262, 21091 `FO_VslTemplate4FirstOpenSDK: Inter splash: [2572755573, 7633510569, 5711332497, 8890751911, 1068102219]` (mỗi ID đúng 2 lần trong log, chỉ ở 2 dòng dump).
Splash request/show thật:
- New user pid 23204: :1025 `loadInterstitialAd: …/8784891502 - …/8792630363`; :1893 `FOR_TESTER_SHOW_AD: INTERSTITIAL - …/8792630363`.
- Old user pid 24920: :15463 `loadInterstitialAd: …/6158728160 - …/7479548695`; :16323 show `…/6158728160`.
4 ID này = `new_leftover_ids`. Agent ghi vào unresolved (không qua phản biện). Tôi xác nhận bằng grep: đúng.
Lượt 17:07 rất có thể cũng khớp giả theo cùng cơ chế (dump FO), báo cáo 17:07 nói "inter splash đã chạy đúng ID sheet" khả năng sai; log lượt đó đã bị ghi đè, không kiểm lại được.

## confirmed (1): 3 dòng ID thường chưa capture đủ

`305_onb5_n_native` (…/9365073832), `301_onb1_o_native` (…/2381786526), `301_onb1_o_inter` (…/4724114496).
ID high anh em fill ngay: 4903084642 load :10120 show :10758; 5098525763 loaded :16187 show :18000; 7350277832 loaded :16152 show :19773. Cơ chế fallback thấy ở cặp 306: :10530 load high-normal, high fail eCPM floor (:11291), show thường …/1295935564 (:12794).
APK vắng ID không phải bằng chứng (ID runtime đã khớp cũng vắng APK). Cần ép no-fill ID high (Ad Inspector) để chấm.

## disputed (0)

## unresolved (1)

Inter splash runtime khác checklist, xem mục khớp giả ở trên.

## Lỗ tool

- Khớp tính theo "ID có xuất hiện trong log", không theo request/show của đúng vị trí → dump cấu hình làm khớp giả. Nên chỉ tính khớp khi có load/show (FOR_TESTER_*/loadInterstitialAd) từ pid app.
- Dòng đã "khớp" không được đưa cho judge, nên khớp giả không bao giờ được phản biện.
- `apk_scan_applicable=true` sai cho app nạp ID lúc chạy.
- Cổng "build chưa đổi" chỉ dựa versionCode, phải `--force`.

## Câu hỏi chưa giải quyết

- Inter splash dùng ID nào là đúng: ID sheet (trong cấu hình FO) hay 4 ID splash đang request?
- Có cần chấm 3 dòng ID thường không? Có thì cần ép no-fill ID high.

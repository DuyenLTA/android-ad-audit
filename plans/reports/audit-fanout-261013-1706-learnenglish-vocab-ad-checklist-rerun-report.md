# Audit checklist ads — learnenglish.language.learningvocabulary.practice (bản mới)

- Run: `wf_0ad473e7-920` · mode `capture` (`--force`) · 2026-10-13
- Build: version_code `2` (bản cài lại 16:19, cùng versionCode) · audited_at `2026-10-13T10:07:40+00:00`
- Sheet tab: gid `1919567600`
- Capture: `missed_home=[]`, `capture_reused_from=null`
- `empty_filters`: `RemoteConfigRepository`, `inter_ads`, `loadInterstitialAd`
- Lượt trước: `wf_20d8ac0a-7cb`, 10/56

## Thống kê

48/56 khớp (10 cũ + 38 fixed). broke 0, new_leftover_ids 0, rows added/removed 0.
Còn lệch 8 dòng, đều mục 2. ID ads FO.

## confirmed (1): 8 dòng onb5 / onb1_o, chưa capture đủ

Dòng: `305_onb5_n_native_high/_native`, `306_onb5_n_inter_high/_inter`, `301_onb1_o_native_high/_native`, `301_onb1_o_inter_high/_inter`.
- ID vắng APK không phải bằng chứng: 38 ID khớp runtime cũng vắng APK (vd `9872661095` LFO2, `4482845454` OB1, in ở dump FO_VslTemplate4FirstOpenSDK capture.log:5537-5552, pid 20249).
- Placement có trong build: apk_strings CÓ `305_onb5`, `306_onb5`, `301_onb1_o`, `Onboarding5` (classes4.dex + Manifest), `enable_onb5_screen`, `onboarding_old_config`.
- Màn không bật: `No value of type String exists for parameter key enable_onb5_screen` (capture.log:1089, 6742); `onboarding_old_config` không giá trị (6759); UiConfig (3074) chỉ ONB1/ONB2/ONB4; dump slot không có OB5/onb1 old.
- Không ID lạ chiếm chỗ → không phải checklist sai, không phải build thiếu. Nhãn đúng: chưa capture đủ.

## disputed (0) · unresolved (0)

Inter splash lượt trước (disputed) nay khớp: build load/show đúng ID sheet.

## Lỗ tool

- `apk_scan_applicable=true` sai cho app nạp ID lúc chạy (0/38 ID khớp runtime có trong APK) → 8 dòng bị gắn "không có trong build" + note "nghi checklist ghi ID không tồn tại". Nên tính cờ theo tỉ lệ ID runtime có trong APK.
- Cổng "build chưa đổi" chỉ dựa versionCode: bản cài lại cùng versionCode 2 bị bỏ qua capture, phải `--force`.

## Câu hỏi chưa giải quyết

- ONB5 và onboarding old user có trong phạm vi bản này không? Có thì cần bật RC rồi capture lại.

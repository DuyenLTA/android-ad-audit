# Audit fanout — aitutor.grammar.languagetutor.iletslesson.learninglanguage (versionCode 1)

- Run: wf_adea1a0b-ac8 · mode capture --force · gid 877288820 (từ sheet, chưa có trong registry)
- Kết quả: 6/56 khớp, 50 lệch (triage: 44 "không có trong build", 6 "khác"). Capture new + old đều tới Home.
- Nhóm: confirmed 3 nhóm/10 dòng · disputed 3 nhóm/27 dòng · unresolved 2 nhóm/13 dòng.
- Không commit.

## Bối cảnh chung
- Sheet: publisher 4584260126367940, App ID ~2789752111.
- Build: manifest App ID ca-app-pub-4973559944609228~1208093315; FO native/inter Question preload ID 4973 (có trong APK).
- Inter splash runtime nạp 4584/1654644744 + /6715399734 (new), /1137759093 + /8357773563 (old) — không có trong APK → cấp từ ngoài APK (RC/server). Cả 4 trùng sheet (show_102_spl_n_inter_high/inter, spl_o_inter_high/inter) = 4 trong 6 dòng khớp. Phản biện của agent nói "không ID nào có trong sheet" là sai; kết luận "publisher 4584 đang chạy thật" vẫn đứng, càng chắc hơn.
- UMP: "no form(s) configured for the input app ID" với App ID 4973. Build còn dấu vết cấu hình dự án khác (package com.nxl.aienglishtutor, SKU creatorhub.vip.*, RevenueCat ConfigurationError).
- empty_filters chứa RemoteConfigRepository → không thấy giá trị RC.

## Confirmed
1. 306_onb4_n_inter_high (4584/5118181372), 306_onb4_n_inter (4584/6718203505) — build-thiếu. APK không có 306_onb4 / onb4_n_inter / onb4_inter / onb_inter; có 304_onb4, onb4_n_native. Runtime: màn Onboarding không có loadInterstitialAd trước Question.
2. reward_chat_high / reward_chat — chưa capture đủ (placement có trong classes4.dex, log không có load Reward).
3. Resume 501_aoa/502_native/503_inter (6 dòng) — chưa capture đủ (có aoa_high, resume_native trong APK; lượt capture không có ẩn/mở lại app).

## Disputed (cần người xem)
Agent đề xuất "checklist-sai", phản biện bác: checklist là chuẩn + publisher 4584 đang chạy thật qua ID runtime → nhãn đúng là build-sai hoặc cần PM xác nhận.
1. LFO1/LFO2/OB1 native + Question native/inter (16 dòng). Build dùng 4973: LFO1 1220446466/8907364797/7613719562/7594283125; LFO2 7812715482/4968119781/6300637890/3655038118; OB1 2341956440/1196008695/1168088533/8855006863; native Question 5862362032/6584955769; inter Question 7833919257/6506993744.
2. Native onb2–onb5 (10 dòng). Màn onboarding nạp 4973 (3738411558, 5779311020, 4943682014, 4257286304, 5051493226, 2944204636…); log không gắn key theo onbN.
3. App ID — sheet 4584~2789752111 vs manifest 4973~1208093315.

## Unresolved
1. Splash banner ×2, native ×5, inter_high1 (8 dòng): placement có trong APK, log không load; app nạp ID ngoài APK nên vắng APK không đủ kết luận.
2. Adjust token + 2 event, FB App ID, FB Client Token (5 dòng): giá trị sheet vắng APK; build có cấu hình riêng nhưng log không in giá trị.

## Tool gap (agent nêu)
- apk_scan_applicable=true dù runtime có ID publisher 4584 không nằm trong APK → nên hạ cờ cho publisher đó, chuyển dòng sang "APK không kiểm được".
- Lệch toàn bộ publisher thì tool mặc định ghi "nghi checklist sai" — ngược quy ước checklist là chuẩn.

## Unresolved questions
- App chạy tài khoản AdMob nào (4584 hay 4973)? Cần ads-team/PM chốt.
- Cần đọc giá trị RC để biết ID 4584 nào đang được cấp lúc chạy.
- Cần lượt capture thêm: ẩn/mở lại app (resume) + luồng chat reward.

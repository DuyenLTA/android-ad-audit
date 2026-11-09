# Audit fanout — aitutor.grammar.languagetutor.iletslesson.learninglanguage (versionCode 2)

- Run: wf_e4f2bb11-577 · mode capture --force · gid 877288820 (từ sheet, chưa có trong registry)
- Kết quả: 7/56 khớp, 49 lệch. Capture new + old đều tới Home (missed_home rỗng).
- Delta so với lượt trước: fixed App ID (ca-app-pub-4584260126367940~2789752111), không broke; ID dư mới 4973559944609228/5689300747. 46 ID dư trong build không có trên sheet.
- Nhóm: confirmed 2 nhóm/8 dòng · disputed 3 nhóm/29 dòng · unresolved 3 nhóm/12 dòng.
- empty_filters: RemoteConfigRepository, inter_ads → không thấy giá trị RC.
- Không commit.

## Bối cảnh chung
- Inter splash runtime nạp 4584/1654644744 - /6715399734 (cặp high/thường), đều Khớp sheet; apk_strings 'KHÔNG 1654644744' → ID 4584 tới từ RC/server, không nằm trong APK. build_ad_ids không có ID 4584 nào → phép "vắng APK" vô hiệu với app này.
- Placement SDK quản lý (LFO/OB/Question) nạp đúng config line FO_VslTemplate4FirstOpenSDK = ID 4973.

## Confirmed (chưa capture đủ)
1. reward_chat_high / reward_chat — placement có trong classes4.dex; log không có request reward (luồng không mở chat sau Home).
2. Resume 501_aoa/502_native/503_inter (6 dòng) — không có FOR_TESTER_LOAD_AD resume; config SDK khai resume 4973 (aoa high /9471747632, aoa /2962179601, native high /6845584292, native /2565908028, inter high /1252826356, inter /1457526246) → nhiều khả năng lệch, cần chạy Home → chờ → mở icon.

## Disputed (cần người xem)
Agent gắn "checklist-sai"; phản biện bác: dữ kiện lệch đúng, nhưng sheet đúng publisher 4584 (App ID + splash inter khớp) → nhãn đúng là build-sai / cần ads-team xác nhận.
1. Native FO 20 dòng (LFO1 ×4, LFO2 ×4, OB1 ×4, OB2 ×2, OB3 ×4, OB4 ×2): build load 4973 — LFO1 1220446466/8907364797/7613719562/7594283125; LFO2 7812715482/4968119781/6300637890/3655038118; OB1 2341956440/1196008695/1168088533/8855006863; OB2 8990738235/5051493226; OB3 3738411558/5779311020/4943682014/4257286304; OB4 3320668649/2944204636.
2. Question 4 dòng (301_onb1_o_native ×2, show_301_onb1_o_inter ×2): native 4973/9211119109 (No fill) → /6584955769 loaded+show; inter 4973/7833919257 - /6506993744; lượt old 7119603381, 3010677842, 9174921088.
3. Adjust token/2 event + FB App ID + FB Client Token (5 dòng): build hardcode prcsifab394w, dq5is9, 69milv, 1278806620578469, e8f7008fae10d079ad8d55191feded41 (có trong APK + FOR_TESTER_CONFIG); giá trị sheet vắng APK.

## Unresolved
1. Splash banner ×2, native ×2, native full ×3 (7 dòng): log chỉ có config line 4973, không load.
2. show_102_spl_n_inter_high1 (4584/9341563075): splash chỉ load cặp high/thường.
3. 305_onb5_n_native ×2, 306_onb4_n_inter ×2: không thấy load OB5 / inter sau OB4; apk 'CÓ onb5', 'KHÔNG 306_onb4'. Lượt trước 306_onb4 được chốt build-thiếu ở versionCode 1; lượt này agent hạ xuống unresolved vì tên placement sheet chưa chắc trùng code.

## Tool gap (agent nêu)
- apk_scan_applicable=true dù runtime có ID 4584 không nằm trong APK → nên tự tắt phép kiểm APK, phán từ FOR_TESTER_LOAD_AD/SHOW.
- Lệch toàn bộ publisher vẫn ghi "nghi checklist ghi ID không tồn tại" — ngược quy ước checklist là chuẩn.

## Unresolved questions
- Native FO / Question / Adjust / FB: ads-team xác nhận build hay sheet đúng.
- Cần đọc giá trị RC để chốt splash banner/native, high1, OB5, inter OB4.
- Cần capture thêm resume + luồng chat reward.

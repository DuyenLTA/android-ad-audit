# Audit fanout — aitutor.grammar.languagetutor.iletslesson.learninglanguage (v2) — 12/56 khớp

- Run: `wf_a3bb3933-9a8` · mode `capture` (force) · tab gid 877288820
- Capture: 2 cold start (PID 25837 lúc 22:20:36, PID 27684 lúc 22:22:17), cả 2 tới MainActivity. missed_home = []
- Lượt trước (`wf_7260d768-b3d`) bị runner bỏ capture vì "build và checklist đều chưa đổi" → đã dừng, chạy lại với `--force`

## Thống kê
| Section | Dòng | Khớp |
|---|---|---|
| 1. Thông số kỹ thuật | 8 | 8 |
| 2. ID ads FO | 40 | 4 |
| 3. ID ads inapp | 2 | 0 |
| 4. ID ads resume | 6 | 0 |
| **Tổng** | **56** | **12** |

Delta so với lượt 18:53: fixed 5 (Adjust token, event purchase, event ad impression, FB App ID, FB Client Token). Không có dòng nào broke. versionCode vẫn là 2.

## Confirmed (chưa capture đủ, đã qua verify)
- reward_chat_high / reward_chat: capture.log không có dòng FOR_TESTER nào chứa reward. Sau MainActivity không có START nào khác, tức chưa vào chat. APK có `reward_chat` (classes4.dex)
- 501/502/503 resume (6 dòng): chỉ có cold start, không có lượt Home rồi mở lại. Lúc vào Home, FO_VslTemplate4FirstOpenSDK có in "AppResume …" kèm ID, nhưng không có load/show nào

## Disputed
Không có.

## Unresolved (4 nhóm)
1. Cả rổ: tiền đề "vắng APK ⇒ checklist sai" không đứng được. Các ID 4584 ĐÃ KHỚP (.../1654644744, .../1137759093) cũng vắng APK, nhưng có xuất hiện trong FOR_TESTER_SHOW_AD, nghĩa là app nạp ID lúc chạy. build_ad_ids chỉ chứa ID 4973559944609228 (leftover). Cờ apk_scan_applicable=true là sai với app này
2. FO native/inter trên các màn đã capture (33 dòng): runtime chỉ thấy ID 4973559944609228 (native /4668736885, /7594283125, /3655038118, /8855006863, /8990738235, /4943682014, /2944204636, /6584955769, /7119603381; inter /6506993744, /3010677842). Không thấy ID nào của sheet. Không xếp checklist-sai vì publisher 4584 trùng App ID trong manifest và trùng inter splash. Nhiều khả năng build đang chạy bộ ID mặc định khác publisher, hoặc RC không trả ID (filter RemoteConfigRepository rỗng)
3. show_102_spl_n_inter_high1: `loadInterstitialAdDoubleIds` chỉ nạp cặp high + normal, cả 2 khớp sheet. Không có tầng high1
4. Banner splash ×2: không có dòng FOR_TESTER nào cho banner

## Tool gap
- Kịch bản capture chỉ chạy First Open cold start tới Home, không có bước sau Home: (1) ẩn bằng Home rồi mở lại bằng icon, để bắt resume; (2) vào chat, để bắt rewarded. Nhãn missed_home=[] chỉ có nghĩa là tới được Home
- empty_filters: RemoteConfigRepository, inter_ads, nên không đọc được giá trị RC
- Runner skip khi versionCode và digest không đổi, kể cả khi user muốn lái lại máy. Cần `--force`

## Câu hỏi chưa giải quyết
- Bộ ID 4973 là ID mặc định trong code hay do RC trả về? Cần ads-team/dev xác nhận
- Adjust/FB đổi từ lệch sang khớp mà versionCode không đổi: dev đã đẩy lại cùng version, hay lượt 18:53 đọc thiếu?

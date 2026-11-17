# Audit fanout — ai.photogenerator.aivideo.aivideogenerator.aiart (Nexus AI, versionCode 32)

Run: wf_22b179d7-621 · mode capture (pm clear, capture mới 11/11/2026) · registry có sẵn

## Thống kê
- 69/72 dòng khớp · lệch 3 (đều mục 3. ID ads inapp)
- confirmed 3 · disputed 0 · unresolved 0
- delta: không đổi so với lượt trước (broke 0, fixed 0, ID lạ mới 0), leftover 0
- missed_home=[new, old]: cả 2 luồng kẹt RevenueCatPaywallActivity (driver hết cách thử). empty_filters=[inter_ads]

## Confirmed — build-thiếu (3 dòng, chung nguyên nhân)
| Dòng | ID sheet | Build |
|---|---|---|
| reward_img_vid_high (Generate Image/ Video) | 8037302182 | vắng ID + tên placement trong APK |
| reward_img_vid | 5411138843 | vắng ID + tên placement |
| inter_feature_high (Home) | 4070123043 | vắng ID + tên placement; chỉ có inter_feature (4098057173, khớp) |

Bằng chứng: apk_strings trên ai.photogenerator...-32.apk (UTF-8+UTF-16LE): KHÔNG reward_img_vid(_high), KHÔNG inter_feature_high/show_inter_feature_high; CÓ inter_feature, show_inter_feature, result_img_vid_high. 3 ID alt_values không có trong build_ad_ids, APK, log. ID dòng anh em đều có trong build_ad_ids → app hardcode ID trong APK, phép kiểm APK có hiệu lực.
Log RemoteConfigRepository: key=show_inter_feature (không _high); reward tách show_reward_img_template/t2i/i2i, show_reward_vid_template/i2v kèm _high.
Verifier chạy lại độc lập → holds.

Lưu ý: có thể checklist dùng tên placement gộp cũ, build đã tách theo tính năng → cần ads-team/PM chốt.

## Tool gap
- Dòng "không thấy ID" không ghi rõ đã đối chiếu alt_values (ID thật) với build_ad_ids; nên in kèm.
- Driver không qua được RevenueCatPaywallActivity của app này → chưa tới Home.

## Câu hỏi chưa giải quyết
- Sheet ghi tên cũ hay build v32 thiếu 3 placement?
- Cần ghi luồng đóng paywall RevenueCat cho app này để lượt sau tới Home?

# Audit ID ads · Nexus AI (ai.photogenerator.aivideo.aivideogenerator.aiart) vc30 · 28/10/2026

Lượt gọi từ /rc-check (bot Discord), máy 18311FDF60085N (Pixel 6), mode capture, run wf_9593a554-bd9.

## Kết quả
- 72 dòng checklist, 69 khớp, 3 lệch (cả 3 ở mục "3. ID ads inapp").
- confirmed 1 nhóm (3 dòng), disputed 0, unresolved 0. delta so lượt trước: không đổi.
- Capture: missed_home = [new, old] (chưa tới Home), empty_filters = [inter_ads]. Kết luận dựa trên APK nên không bị ảnh hưởng.

## 3 dòng lệch (build-thieu: tên placement không có trong APK)
| Vị trí | Placement sheet | ID sheet | Build |
|---|---|---|---|
| Generate Image/ Video | reward_img_vid_high | ca-app-pub-4973559944609228/8037302182 | không có; build có reward_img_template/t2i/i2i(_high), reward_vid_template/i2v(_high), result_img_vid(_high) |
| Generate Image/ Video | reward_img_vid | ca-app-pub-4973559944609228/5411138843 | như trên |
| Home | inter_feature_high | ca-app-pub-4973559944609228/4070123043 | chỉ có inter_feature (…4098057173, khớp) |

Bằng chứng: apk_strings.py trên aiart-30.apk không thấy reward_img_vid*, inter_feature_high, show_inter_feature_high; RC trong capture (lô FA-SVC đúng app_id) chỉ có các key đã tách nêu trên.

## Việc cần làm
- Cần ads-team xác nhận: checklist cập nhật theo placement đã tách, hay build sót inter_feature_high / reward_img_vid.
- Tool chỉ đối chiếu chiều sheet → build.

## Unresolved questions
- Không có.

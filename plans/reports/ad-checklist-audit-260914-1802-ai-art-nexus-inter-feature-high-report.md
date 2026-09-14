# Ad checklist audit — AI Art (Nexus AI - AI Video Generator)

- Package: `ai.photogenerator.aivideo.aivideogenerator.aiart`
- Version code: 24 · audited_at 2026-09-14T10:59:26+00:00
- Chế độ: `capture` (lái máy thật, log mới) · run `wf_5185b435-021`
- Capture hợp lệ: `apk_scan_applicable=true`, `build_ad_ids=78`, `missed_home=[]`, `empty_filters=[]`, `dev_build_signals=0`

## Thống kê

| | |
|---|---|
| Khớp | **71 / 72** |
| Lệch | **1** |
| Delta so lần trước | không đổi (`broke`/`fixed`/`rows_added`/`rows_removed`/`new_leftover_ids` đều rỗng) |
| Leftover ID (chạy trong build, không có trên sheet) | 1 — `ca-app-pub-4973559944609228/2733004612` |

Theo mục: 1. Thông số kỹ thuật 8/8 · 2. ID ads FO 40/40 · 3. ID ads inapp 17/18 · 4. ID ads resume 6/6.

## Kết quả điều tra

### confirmed (1) — luận điểm đứng sau phản biện

**`inter_feature_high` — màn Home — checklist-sai**

- Sheet ghi `ca-app-pub-4973559944609228/4070123043`; build thực chạy `ca-app-pub-4973559944609228/2733004612`.
- Bằng chứng cứng: `apk_strings.py` trên APK v24 — chuỗi `4070123043` **không có** (cả UTF-8 lẫn UTF-16LE, mọi entry). `2733004612` và `4098057173` **có** trong `classes.dex`. Khớp `build_ad_ids` (78 ID) của triage.
- Vai trò high xác nhận từ cặp twin: `capture.log:14591`, `:28888` — `inter_ads: canRequestAd: key=…/2733004612_…/4098057173` (dạng `high_normal`); `:15018`, `:29376` — `loadDoubleIds: highPriorityAd=NULL for id=…2733004612`; đối xứng `:15590` — `loadDoubleIds: normalAd=… for id=…4098057173`. Nửa normal `4098057173` chính là ID của dòng twin `inter_feature` (snapshot dòng 510-513, `found=true`) → nửa high là `2733004612`.
- Attribution tiến trình: `capture.log:224` `Start proc 20070:ai.photogenerator…`, `:15960` `Start proc 22357:…` — mọi dòng `inter_ads`/`FOR_TESTER_*` trích dẫn đều từ 20070/22357, đúng app. Log có lô `FA-SVC` lạ (`app_id: aisong.generator.creatsong.music`) nhưng **không** dòng bằng chứng nào lấy từ FA-SVC.
- Màn khớp label: `ga_screen_class=AIP922AIPhotoVideoMakerMainActivity` = Home.
- Phản-giả thuyết đã loại: (a) `2733004612` không phải ID của dòng checklist khác — chỉ xuất hiện trong khối bằng chứng runtime/leftover, không nằm trong `alt_values` của row nào; (b) `4070123043` chỉ xuất hiện đúng 1 lần trong snapshot, tại chính row này (dòng 502); (c) không phải ID nạp từ remote-config — cả hai nửa cặp đều nằm trong APK nên phép kiểm APK còn hiệu lực.
- Phụ trợ: `grep 4070123043 capture.log` = 0 hit.

### disputed (0)

Không có.

### unresolved (0)

Không có. Mọi dòng đều đã kết luận.

## Diễn giải

Bằng chứng chỉ chứng minh **sheet và bản cài lệch nhau** — tự nó không nói bên nào sai. Hướng hợp lý nhất: ID `4070123043` trên sheet không tồn tại trong build v24, build đang chạy `2733004612` cho `inter_feature_high` ở Home. **Cần ads-team xác nhận** ID nào là ID đúng, rồi sửa sheet hoặc sửa build cho khớp.

## Câu hỏi chưa giải quyết

- `4070123043` là ID cũ đã thay, hay ID mới chưa kịp lên build? Ads-team xác nhận.
- Log có lô `FA-SVC` khai `app_id: aisong.generator.creatsong.music` trong lượt capture app này — không ảnh hưởng chuỗi bằng chứng, nhưng chưa rõ vì sao xuất hiện (app khác còn chạy nền?).

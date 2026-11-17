# Audit fan-out: fitness.workout.aitraining.abs.exercises (AIP921 fitness)

- Run: wf_aacf4e31-727 · mode capture (--force) · máy Pixel 4 99261FFAZ0077C · version_code 1 · pm clear app
- Tab sheet: gid=422709729 (chưa có trong apps.json)

## Thống kê
- 46/46 ad unit ID FO+resume của build khớp checklist; leftover_ids rỗng.
- Adjust/Facebook/App ID khớp.
- Còn 6 dòng "chưa thấy trong log", đều ở mục 3 "ID ads inapp".

## Kết quả fan-out
- confirmed: 0 · disputed: 0
- unresolved: 2 nhóm
  1. 5 dòng inapp (banner_home_high, inter_home_high, reward_scan_nutrition_high, inter_back_high, native_reason_uninstall_high). Sheet không có ca-app-pub, value là cột Screen, nên tool so tên màn với log. Không phải lệch ID.
  2. Dòng "No./Screen" là tiêu đề bảng, parser đọc nhầm.

## Bổ sung sau workflow
Agent không quét được APK vì có 2 máy cắm mà apk_strings không có --serial. Tôi chạy lại với ANDROID_SERIAL=99261FFAZ0077C:
- CÓ: banner_home, inter_home, inter_back (classes.dex)
- KHÔNG: reward_scan_nutrition, native_reason_uninstall, reward_scan, native_reason, scan_nutrition, reason_uninstall
- CÓ chuỗi chung: nutrition, uninstall

Lượt capture tới MainActivity ~10s, không đi AI Scan / back / Uninstall. empty_filters: inter_ads, RemoteConfigRepository.

## Việc cần làm
- ads-team bổ sung cột ID inapp mục 3; xác nhận reward AI Scan / native Uninstall có trong build không, hay tên placement khác.
- Tool: parser mục 3 đọc dòng tiêu đề thành dữ liệu; apk_strings cần --serial khi nhiều máy.

## Câu hỏi chưa giải quyết
- ID inapp nạp qua RC hay build chưa gắn?

## Cập nhật 20:25: user báo cột Ad ID có đủ
- Parser `checklist_source.parse_checklist_csv` chỉ đọc cột A/B/C. Mục 3 là bảng nhiều cột (No./Screen/Ad Name/Priority/Ad description/Ad Type/**Ad ID (cột G)**/Key remote) nên lấy nhầm Screen làm value và bỏ dòng ID thường (cột A, B trống). **Lỗi tool, không phải sheet.**
- Đối chiếu tay 12 ID cột G: 0/12 có trong APK (`apk_ad_ids` + `apk_strings` UTF-8/16), 0/12 trong log capture.
- RC qua REST (rcr `rc_firebase_app.gia_tri_that`): chỉ có `splash_inter_*_id`, không có ID inapp. Có show_banner_home/inter_home/inter_back/reward_nutrition (+_high).
- APK có key show_banner_home/show_inter_home/show_inter_back; KHÔNG có show_reward_nutrition, show_native_reason_uninstall, show_inter_uninstall.
- Ngoài FO/resume, build chỉ có 10 ID mẫu Google 3940256099942544 (mặc định lib), log không dùng.
- Kết luận: bản cài chưa mang 12 ID inapp. Cần dev/ads-team xác nhận.
- Việc cho tool: parser cần nhận bảng có header "Ad ID" (đọc theo tên cột).

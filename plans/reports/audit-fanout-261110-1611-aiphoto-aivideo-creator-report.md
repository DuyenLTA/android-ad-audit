# Audit fanout — com.ai.aiphoto.aivideo.creator.generator (versionCode 6)

Run: wf_1c0849b3-9cd · mode capture (dùng lại capture 10/11/2026 15:28, Pixel 6, đã tới Home) · tab sheet gid=1171872315 (chưa có trong registry)

## Thống kê
- build_ad_ids 71, apk_scan_applicable=true, missed_home 0, dev_build_signals 0
- Lệch cần phán: 1 dòng (502_native). confirmed 0 · disputed 1 · unresolved 0

## Disputed — 502_native (4. ID ads resume)
- Sheet: ca-app-pub-4973559944609228/2199612256 — không có trong APK, không thấy nạp lúc chạy
- Build: SDK log `AppResume native high` và `AppResume native :` cùng ID 8349253480 (cả 2 lượt mở app: capture.log dòng 11773-11774, 16744-16745) = ID dòng 502_native_high (đang khớp)
- Agent phán checklist-sai; verifier bác: placement khác đều có ID high/normal riêng (aoa 6375101928/7363468701, inter 8246145851/8786211068) → nhiều khả năng build copy nhầm ID high vào ô normal (build-sai). Cần ads-team/dev xác nhận

## Ngoài lề
- 4 ID inter inapp không có trong sheet (5003074841, 5135111792, 5537602329, 6448193469) — FOR_TESTER_LOAD_AD, sheet chưa có mục ID inapp
- Vùng log RemoteConfigRepository rỗng (không ảnh hưởng kết luận)

## Tool gap
- Khi ID sheet vắng APK và runtime dùng ID khác, tool xếp checklist-sai mà không kiểm ID runtime có trùng ô anh em (high/normal) không → nên thêm rule: trùng ID ô anh em = build-sai (copy-paste)

## Câu hỏi chưa giải quyết
- ID đúng của 502_native là 2199612256 (sheet) hay build cố ý dùng chung 8349253480?

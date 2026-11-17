# Audit ID ads — AI Art (Nexus AI) 3.9.0 (vc 32) · ai.photogenerator.aivideo.aivideogenerator.aiart

- Run: wf_b3bed909-3a3 · mode capture · máy 3454184009000HI · 10/11/2026 17:02
- Tab sheet: AIP922. Kết quả: 69/72 khớp; confirmed 0, disputed 0, unresolved 1 (gồm 3 dòng).
- Capture: user mới + user cũ đều dừng ở RevenueCatPaywallActivity, chưa tới Home (missed_home = new, old). Filter rỗng: inter_ads.

## Unresolved — 3 dòng mục "3. ID ads inapp" không có trong APK
| Vị trí | ID sheet | APK |
|---|---|---|
| inter_feature_high (Home) | …4070123043 | không có; APK có …2733004612 sheet không ghi |
| reward_img_vid_high | …8037302182 | không có |
| reward_img_vid | …5411138843 | không có |

Bằng chứng: build_ad_ids triage (86 ID, vc 32). RC key trong log của app (cùng PID FOR_TESTER_*): show_reward_img_t2i/_i2i/_template, show_reward_vid_i2v/_template, show_reward_song (+_high); show_inter_feature nhưng không có show_inter_feature_high. Log không chứng minh được ID thay thế (chưa tới Home) → cần ads-team xác nhận.

## Lỗi tool đã sửa trong lượt (chưa commit)
- Hai lượt đầu dừng "Sai build" nhầm: logcat cả máy lẫn dòng của app khác (com.sonydroids…nolastseen, bản dev Apero lib: `Config variant dev: true`, `setupAdjust: sandbox`). App AIP922 tự ghi `dev: false`, Adjust `production`.
- build_identity.py: log_watcher nhận `pids` (chỉ tính marker của PID app); thêm app_lines() lấy PID app qua tag ART (15 ký tự cuối tên process); dev_build_signals chỉ tính bằng chứng trong dòng của app. device_driver.py truyền pidof; audit_runner.py truyền dòng của app. Test: test_build_identity.py (+5 test), test_audit_runner.py — 48 pass.

## Câu hỏi chưa giải quyết
- ID thật của inter_feature_high và reward theo tính năng mới — ads-team cập nhật sheet.

## Lượt lại 17:2x (run wf_a9e394f4-cf2, rc-check bot --bo-qua-plan, máy 3454184009000HI)
- Cùng build 3.9.0 vc 32 (sha256 0a1b0ac50e23…, APK kéo từ máy = bản cache). Triage giữ nguyên: 3 dòng in-app "không có trong build".
- Đã chạy apk_strings.py --apk trên APK cài: KHÔNG có reward_img_vid_high / reward_img_vid / inter_feature_high, KHÔNG có 8037302182 / 5411138843 / 4070123043; CÓ inter_feature + 4098057173. → nghiêng build tách reward theo tính năng, sheet cần cập nhật; vẫn cần ads-team xác nhận.

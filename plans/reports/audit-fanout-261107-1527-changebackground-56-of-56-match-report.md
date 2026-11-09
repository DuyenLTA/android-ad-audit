# Audit fanout — aiphoto.changebackground.photogenerator.aiimage (versionCode 1)

- Run: wf_a2ba2fb9-82e · mode capture --force · gid 760419019 (từ sheet, chưa có trong registry)
- Kết quả: 56/56 khớp, chưa kết luận 0 → clean. confirmed 0 / disputed 0 / unresolved 0.
- Lượt đầu của app → delta ghi 56 dòng "mới thêm", không broke/fixed.
- Capture: new (pm clear) Splash → inter → Language 1.1/2.1 → Onboarding → Question → inter → Billing → Main; old Splash → inter → Question → inter → Billing → Main. Cả 2 tới Home.
- empty_filters: RemoteConfigRepository, inter_ads — vùng log đó không có dòng nào.
- 3 dòng khớp chỉ nhờ APK (log chưa thấy load): show_301_onb1_o_inter, reward_img_vid_high, reward_img_vid — chưa chứng minh placement đang bật.
- 22 ID 4584260126367940/* trong build không có trên sheet (tool chỉ đối chiếu sheet → build, không tính lệch). Danh sách đầy đủ trên trang artifact.
- Không commit.

## Unresolved questions
- 22 ID ngoài checklist: ads-team xác nhận là ID dự phòng/cũ hay cần bổ sung sheet.

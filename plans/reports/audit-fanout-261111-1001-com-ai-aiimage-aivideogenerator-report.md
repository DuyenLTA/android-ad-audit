# Audit fanout — com.ai.aiimage.aivideogenerator (versionCode 16)

Run: wf_9537e1f8-15d · mode capture (pm clear, capture mới 11/11/2026) · tab sheet gid=2043759657 (chưa có trong registry)

## Thống kê
- 72/72 dòng sheet khớp build · lệch 0 · chưa kết luận 0
- confirmed 0 · disputed 0 · unresolved 0 → **sạch**
- Lần audit đầu của app (delta: 72 dòng mới, broke 0, fixed 0, ID lạ mới 0)
- dev_build_signals 0

## Cảnh báo capture
- Luồng new chưa tới Home: kẹt ở VslTemplate4QuestionActivity sau khi đóng AdActivity (hết giờ). Luồng old tới Home (qua VslBillingActivity → close → AIP885AIPhotoVideoMakerMainActivity)
- Filter RemoteConfigRepository không khớp dòng log nào
- Không ảnh hưởng 72/72 (mọi dòng đã khớp)

## Câu hỏi chưa giải quyết
- Driver luồng new kẹt ở màn Question sau inter → cần ghi lại flow nếu muốn lượt sau tới Home ở user mới

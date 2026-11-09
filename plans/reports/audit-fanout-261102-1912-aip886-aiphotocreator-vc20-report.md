# Audit ID ads — com.nxl.aiphotocreator.aivideogenerator.texttoimage (AIP886 2.7.0, vc20)

Lượt: workflow wf_29400a75-38e, mode capture (runner dùng lại capture 2026-11-02 16:31, build + sheet chưa đổi). Chạy trước rc-check tab 3.6.1 trên Pixel 6 18311FDF60085N.

## Kết quả
- Triage 4 rổ rỗng: mọi dòng checklist khớp, 0 dòng lệch. confirmed 0 · disputed 0.
- missed_home = [] — mọi luồng capture tới Home.
- 54/54 khớp. Build có 10 ID thật không có trong sheet; unresolved 2 ID MỚI so với lượt trước:
  - `ca-app-pub-4973559944609228/6107009235` — Banner, AIP886AIPhotoVideoMakerMainActivity (capture.log:18429 load, :18793 Loaded)
  - `ca-app-pub-4973559944609228/7939538105` — Native, preload key `native_ad_library_preload_key` (capture.log:18347, :18564)
  PID 4472 = chính app. Không phải lỗi; cần ads-team xác nhận checklist thiếu dòng hay ID không nên có.

## Lưu ý
- build_ad_ids = null, apk_scan_applicable = null: lượt không quét APK, chỉ đối chiếu chiều sheet → log runtime.
- empty_filters = [RemoteConfigRepository]: vùng log RC rỗng.

## Câu hỏi chưa giải quyết
- 2 ID ngoài checklist ở trên: placement mới chưa ghi sheet hay không nên xuất hiện?

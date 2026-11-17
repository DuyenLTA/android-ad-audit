# Audit ID ads — com.aiphotogenerator.aivideomaker.photoslideshow 2.6.0 (vc 16)
- Run: wf_e8f8eaf3-a70 · mode capture · máy 18311FDF60085N · tới Home: có
- confirmed 0 · disputed 0 · unresolved 9
- Mục 1–2 (FO): không dòng lệch ("không có trong build" = 0).
- Mục 3 "ID ads inapp" 9 dòng: parser đọc nhầm cột (tên màn/placement thay vì ID) → không đối chiếu được. Build có 6 ID ngoài checklist (banner 5660837352, 4347755685; inter 9445390883, 5470486859, 5278915165, 6591996835), khả năng là ID IAA.
- apk_strings không lấy được APK trong phiên agent.

## Câu hỏi chưa giải quyết
- Sửa parser mục 3 để đọc cột ID.

# Audit ID ads — com.aiphotogenerator.aivideomaker.photoslideshow 2.6.0 (vc 16) · máy R58TB198BNN
- Run: wf_fb98b9d0-0de · mode capture (runner bỏ capture mới: build + checklist chưa đổi từ lượt 16/11 19:50, dùng snapshot cùng ngày)
- confirmed 0 · disputed 0 · unresolved 9
- Mục 1–2 (FO): không dòng lệch.
- Mục 3 "ID ads inapp" 9 dòng: parser đọc nhầm cột (tên màn / tên placement thay vì ad unit ID) → chưa đối chiếu được, không phải lệch thật. Build có 6 ID ngoài checklist (banner 5660837352, 4347755685; inter 9445390883, 5470486859, 5278915165, 6591996835), khả năng là ID IAA.
- rc-check chấm ads IAA theo unit thật trong log.

## Câu hỏi chưa giải quyết
- Sửa parser mục 3 để đọc cột ID rồi audit lại.

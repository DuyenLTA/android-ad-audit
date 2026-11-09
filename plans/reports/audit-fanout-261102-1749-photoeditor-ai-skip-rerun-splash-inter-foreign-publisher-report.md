# Audit fan-out: photoeditor.ai.generator.photovideo.image (vc1) — chạy lại ở chế độ skip

- Run: `wf_49872ba9-b5e` · mode: skip (không lái máy, không `pm clear`, dùng lại capture ngày 2026-10-28T08:07Z)
- Checklist: tab gid=268751493 (lấy từ sheet, chưa có trong `apps.json`)
- Ngày: 2026-11-02
- Lượt trước: `audit-fanout-261028-1503-photoeditor-ai-51-rows-match-splash-inter-foreign-publisher-report.md`

## Kết quả
| Section | Khớp |
|---|---|
| 1. Thông số kỹ thuật | 4/4 |
| Facebook Client Token | 1/1 |
| 2. ID ads FO | 40/40 |
| 4. ID ads resume | 6/6 |
| **Tổng** | **51/51** |

- Triage: 4 rổ đều rỗng, `missed_home` = [], `apk_scan_applicable` = true
- `empty_filters`: `RemoteConfigRepository` và `inter_ads` → không xem được giá trị RC
- Workflow trả về: confirmed 0 · disputed 0 · **unresolved 1** · clean 0

## Unresolved → chốt là lệch
Agent nêu 5 ID của publisher `4973559944609228` nằm ngoài sheet (`new_leftover_ids`). Đó chính là các ID mà inter splash load và hiện thật:
- Luồng new: `…/8784891502` (dự phòng `…/1492724849`, `…/8792630363`) → load rồi show (capture.log:4602, 6462)
- Luồng old: `…/6158728160` (dự phòng `…/7479548695`) → load rồi show (capture.log:45295, 47751)
- Các ID `102-spl-n/o-inter*` trong sheet (publisher `4584260126367940`) chỉ xuất hiện trong dòng config `FO_VslTemplate4FirstOpenSDK: Inter splash: [...]` (capture.log:40413, 57183). Không có lần load hay show nào dùng chúng
- `apk_strings`: chuỗi `4973559944609228` không có trong APK → ID được nạp lúc chạy, nhiều khả năng từ RC. Không kiểm được vì filter RC rỗng

Agent không kết luận vì không biết nguồn ID. Theo quy tắc người dùng đã chốt ("checklist là chuẩn, build điền thừa là sai"), dòng này được tính là **lệch (confirmed)**. Lượt 2026-10-28 cũng đã chốt như vậy.

## Ô trống trong sheet nhưng build có giá trị (kết quả lượt trước, capture không đổi)
| Dòng sheet | Sheet | Build |
|---|---|---|
| Facebook App ID | trống | `3292610564230452` |
| Facebook Client Token | trống | `7e2c…2358 (đã che)` |
| App ID | trống | `ca-app-pub-4584260126367940~3637357986` |

## Ghi chú
- Chế độ skip dùng lại capture ngày 10-28, nên kết quả không phản ánh build mới hơn (nếu có). Muốn kiểm lại build sau khi sửa thì phải chạy ở chế độ capture

## Câu hỏi chưa giải quyết
- 5 ID inter splash đến từ RC hay được gắn cứng (mặc định ngoài APK strings)? Cần dev/ads-team xác nhận

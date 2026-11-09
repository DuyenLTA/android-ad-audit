# Audit fan-out: photoeditor.ai.generator.photovideo.image (vc1), chạy lại sau khi sheet được cập nhật

- Run: `wf_425fb4a2-eec` · mode: capture. Build không đổi nên tool so lại log capture ngày 2026-10-28; không lái máy, không `pm clear`
- Checklist: tab gid=268751493, audited_at 2026-11-02T10:55Z
- Ngày: 2026-11-02 · Lượt trước: `audit-fanout-261102-1749-photoeditor-ai-skip-rerun-splash-inter-foreign-publisher-report.md`

## Kết quả
| Section | Khớp |
|---|---|
| 1. Thông số kỹ thuật | 5/8 |
| 2. ID ads FO | 40/40 |
| 4. ID ads resume | 6/6 |
| **Tổng** | **51/54** |

- Delta: sheet có thêm 3 dòng đã điền giá trị, cả 3 lệch build (`broke`). `fixed` = [], `new_leftover_ids` = []
- Workflow trả về: confirmed 3 · disputed 0 · unresolved 0. Phản biện giữ nguyên cả 3

## 3 dòng lệch (confirmed)
| Dòng | Sheet | Build | Bằng chứng |
|---|---|---|---|
| Facebook App ID | 1146260951208629 | 3292610564230452 | APK không có giá trị sheet; log `FOR_TESTER_CONFIG: Facebook App ID: 3292610564230452` (capture.log:6429, 48095) |
| Facebook Client Token | 6e83a01f…2dc8 | 7e2c3956…2358 | APK không có giá trị sheet; log capture.log:6430, 48096 |
| App ID | ~3745316577 | ~3637357986 | Manifest APK (`APPLICATION_ID`) |

Agent gắn nhãn `checklist-sai`. Theo quy tắc "checklist là chuẩn", trang báo cáo trình bày đây là chỗ lệch cần ads-team xác nhận, không nói sheet sai. Cả 3 giá trị của sheet đều không có trong APK, nên có thể sheet đang chép ID của app khác, hoặc build cần sửa.

## Inter splash: giữ kết luận cũ
Sheet không đổi các dòng `102-spl-*-inter*`. Build vẫn load và hiện ID của publisher `4973559944609228` (`/8784891502` ở luồng new, `/6158728160` ở luồng old, kèm 3 ID dự phòng). Đây vẫn là lệch (confirmed) như lượt trước.

## Cảnh báo
- APK cache và capture log đều từ 28/10, versionCode 1. Team hay đẩy lại build cùng version, nên nếu đã có build mới thì cần chạy capture với `--force`

## Câu hỏi chưa giải quyết
- 3 giá trị FB/App ID vừa điền vào sheet có đúng của app này không?
- 5 ID inter splash đến từ Remote Config hay được gắn cứng trong code?

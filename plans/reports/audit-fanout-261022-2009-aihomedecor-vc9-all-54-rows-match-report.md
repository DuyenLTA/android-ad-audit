# Audit fan-out — com.aihomedesign.aihomedecor.designidea.aiinterior (vc9)

- Run: `wf_92d09c2e-36d` · mode: capture (`pm clear`, chạy lại luồng new + old)
- Checklist: tab gid=1680075647 (từ sheet, chưa có trong `apps.json`)
- Ngày: 2026-10-22

## Kết quả
| Section | Khớp |
|---|---|
| 1. Thông số kỹ thuật | 8/8 |
| 2. ID ads FO | 40/40 |
| 4. ID ads resume | 6/6 |
| **Tổng** | **54/54** |

- Triage: 0 dòng chưa kết luận → không cần agent điều tra. confirmed 0 · disputed 0 · unresolved 0 → **clean**
- Delta so với lượt trước: không có dòng hỏng/sửa; checklist có thêm dòng (lượt đầu với digest checklist này), không có ID mới ngoài sheet

## Cảnh báo capture
- Cả 2 luồng (new, old) **không tới Home**: kẹt ở SplashActivity, "hết cách thử, dừng sớm"
- Vẫn khớp đủ 54 dòng vì ID thấy được từ log init/APK. Nhưng placement chỉ load sau Home thì chưa được quan sát lúc chạy → khớp ở đây nghĩa là "ID có trong bản cài", chưa phải "đã load đúng vị trí"
- `build_ad_ids` có 11 ID test Google (`ca-app-pub-3940256099942544/*`) + `ca-app-pub-0000000000000000~0000000000`; không xuất hiện trong capture log → nhiều khả năng là hằng số SDK trong APK, `dev_build_signals` = 0

## Ghi chú
- Tool chỉ đối chiếu chiều sheet → build; khớp hết không có nghĩa bản cài không còn ID ngoài checklist (snapshot ghi 8 mục `extra`)

## Câu hỏi chưa giải quyết
- Vì sao driver kẹt ở SplashActivity với app này — cần `/record-flow` để lượt sau tới được Home?

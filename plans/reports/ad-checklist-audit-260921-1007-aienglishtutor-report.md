# Audit checklist ads — com.nxl.aienglishtutor.ailearnlanguage.aichatbot

- Ngày chạy: 2026-09-21 10:10 (+07)
- Chế độ: `capture` (lái máy thật, `pm clear` trước khi chạy)
- Run workflow: `wf_34567418-bb6`
- versionCode build: 19
- Checklist: tab sheet `gid=1899009360` (chưa có trong `apps.json`, phân giải trực tiếp từ sheet)
- Log capture: `tools/ad-checklist-diff/out/com.nxl.aienglishtutor.ailearnlanguage.aichatbot-capture.log`
- Snapshot: `tools/ad-checklist-diff/snapshots/com.nxl.aienglishtutor.ailearnlanguage.aichatbot.json`

## Kết quả

**54/54 dòng khớp. 0 dòng lệch.** Không có leftover ID (ID xuất hiện trong log mà checklist không khai) nào chưa quy được về dòng checklist.

| Mục checklist | Số dòng | Khớp | Lệch |
|---|---|---|---|
| 1. Thông số kỹ thuật | 8 | 8 | 0 |
| 2. ID ads FO | 40 | 40 | 0 |
| 4. ID ads resume | 6 | 6 | 0 |

Triage 4 nhóm đều rỗng: `không có trong build`, `chưa thấy trong log`, `APK không kiểm được (ID nạp lúc chạy)`, `khác`.

## Fan-out

Không có dòng nào cần agent phán xử → không sinh luận điểm nào.

- `confirmed`: 0
- `disputed`: 0
- `unresolved`: 0
- App nằm trong nhóm `clean`.

## So với lượt trước

Đây là lượt đầu cho app này — snapshot mới tạo. `delta.rows_added = 54`, `broke = 0`, `fixed = 0`, `rows_removed = 0`. Lượt sau mới có cơ sở so sánh.

## Cảnh báo lượt chạy

- `missed_home: ["new", "old"]` — capture không chạm tới màn Home ở cả hai biến thể. ID nào chỉ load tại Home sẽ không nằm trong log; các dòng checklist khai Home (nếu có) vẫn khớp là nhờ ID được nạp sớm ở luồng khác, không phải nhờ đã đi qua màn đó.
- `empty_filters: ["RemoteConfigRepository", "inter_ads"]` — hai bộ lọc log này không bắt được dòng nào. Không chặn việc đối chiếu ID ads, nhưng flag remote-config (nếu checklist có) không có bằng chứng từ lượt này.
- Tool chỉ đối chiếu một chiều sheet → build. Khớp hết **không** đồng nghĩa build không còn ID ads nào ngoài checklist.

## Việc cần làm

Không có gì cần ads-team xác nhận về sai lệch. Nếu muốn lượt sau phủ Home, cần bổ sung bước điều hướng tới Home trong flow capture.

## Câu hỏi chưa giải quyết

- Checklist có dòng nào chỉ quan sát được ở màn Home không? Nếu có, lượt này chưa thật sự chứng minh chúng (dù đang tính là khớp).
- App chưa có trong `apps.json` — có muốn ghi vào registry để lượt sau khỏi tra sheet?

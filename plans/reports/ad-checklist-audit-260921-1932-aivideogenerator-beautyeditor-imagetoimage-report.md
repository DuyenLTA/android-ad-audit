# Ad checklist audit — com.aivideogenerator.aiphotoeditor.beautyeditor.imagetoimage

- Chế độ: `capture` (lái máy thật, `pm clear` rồi chạy flow)
- Run ID: `wf_7f20703f-592`
- Audited at: 2026-09-21T12:32:03+00:00 (UTC)
- versionCode: 37 · checklist digest: `b87772ca08abcbee`
- Sheet tab: gid=1633675332 — phân giải từ sheet, chưa có trong `apps.json`

## Kết quả

**54/54 dòng khớp. 0 lệch.** App sạch.

| Mục sheet | Khớp / Tổng |
|---|---|
| 1. Thông số kỹ thuật | 8/8 |
| 2. ID ads FO | 40/40 |
| 4. ID ads resume | 6/6 |

- `leftover_ids`: rỗng — mọi ID sheet khai đều tìm được.
- Triage buckets (`không có trong build`, `chưa thấy trong log`, `APK không kiểm được`, `khác`): tất cả rỗng → không có dòng nào cần agent phán.
- Fan-out: `confirmed` 0 · `disputed` 0 · `unresolved` 0 · `clean` 1.

## Ghi chú lượt chạy

1. **3 dòng khớp bằng đường APK, không bằng log:** `305_onb5_n_native`,
   `301_onb1_o_native`, `301_onb1_o_inter`. ID nằm trong build nên không lệch
   sheet, nhưng lượt capture chưa chạm màn onboarding tương ứng nên chưa chứng
   minh placement đó đang bật hay màn đó gọi đúng ID. Muốn chắc thì cần lượt
   capture đi qua onboarding.
2. **`missed_home`: `new`, `old`** — flow không chạm được home ở cả hai biến thể
   trong lượt này.
3. **`empty_filters`: `RemoteConfigRepository`, `inter_ads`** — hai filter log
   không ra dòng nào. Không làm hỏng đối chiếu ID (ID lấy từ filter khác), nhưng
   phần remote-config đọc từ log thì mỏng hơn bình thường.
4. **Snapshot đầu tiên của app này** — `delta.rows_added` = 54, `rows_removed` =
   0, `broke`/`fixed` rỗng. Không có mốc trước để so, nên lượt sau mới có delta
   thật.

## Diện kiểm

Tool chỉ đối chiếu một chiều **sheet → build**: mọi ID sheet khai đều có trong
build. Chiều ngược lại không kiểm — build chứa 82 ID (gồm cả ID test
`ca-app-pub-3940256099942544/*`), nhiều hơn 46 ID sheet khai. Khớp hết **không**
đồng nghĩa "không còn ID nào ngoài checklist".

## Câu hỏi chưa giải quyết

1. 3 ID onboarding chỉ xác nhận qua APK — ads-team có cần lượt capture đi qua
   onboarding để chốt placement không?
2. `empty_filters` có `RemoteConfigRepository` — build này có thật sự log remote
   config không, hay filter cần đổi cho SDK version đang dùng?
3. App chưa có trong `apps.json` — có muốn ghi entry `gid=1633675332` để lượt
   sau khỏi quét sheet (~4 phút) không?

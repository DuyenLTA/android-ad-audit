# Audit checklist ads — photomaker.image.editor.ai

- Run: `wf_be59c249-bf6` · mode `capture` · 2026-10-02
- Build: version_code `1` · audited_at `2026-10-02T06:49:34+00:00` (snapshot trùng, không phán trên ảnh chụp cũ)
- Sheet tab: gid `337152191` (từ sheet, chưa có trong `apps.json`)
- Capture: `missed_home=[]` (tới được Home), `capture_reused_from=null`, `dev_build_signals=[]`
- `apk_scan_applicable=true` · `build_ad_ids` 78
- `empty_filters`: `RemoteConfigRepository`, `inter_ads` (hai vùng log rỗng)

## Thống kê

| Mục | Khớp / Tổng |
|---|---|
| 1. Thông số kỹ thuật | 8 / 8 |
| 2. ID ads FO | 40 / 40 |
| 3. ID ads inapp | 2 / 2 |
| 4. ID ads resume | 6 / 6 |
| **Tổng** | **56 / 56** |

`extra` 117 · `leftover_ids` 4.

Triage: cả bốn rổ rỗng — không dòng nào cần phán.

## Kết quả điều tra

- **confirmed** 0
- **disputed** 0
- **unresolved** 0
- App nằm trong `clean`: **sạch**, không còn dòng nào chưa kết luận.

Không có luận điểm nào để phản biện vì không có dòng lệch.

## Delta

Lượt audit **đầu tiên** của app này: `rows_added` 56 (toàn bộ checklist), `rows_removed` 0,
`broke` 0, `fixed` 0. Không có mốc trước để so, nên "4 ID lạ mới" chỉ nghĩa là
lần đầu nhìn thấy, không phải mới phát sinh.

## ID chạy trong build nhưng không có trên sheet (4)

- `ca-app-pub-4973559944609228/6158728160`
- `ca-app-pub-4973559944609228/7479548695`
- `ca-app-pub-4973559944609228/8784891502`
- `ca-app-pub-4973559944609228/8792630363`

Không làm dòng nào fail — tool chỉ đối chiếu chiều sheet → build. Cần ads-team xác nhận:
placement chưa kịp ghi vào sheet, hay ID không nên xuất hiện?

## Lưu ý đọc kết quả

- Tool chỉ đối chiếu chiều sheet → build. 56/56 **không** có nghĩa là không còn ID ngoài
  checklist đang chạy — hiện có 4.
- `empty_filters = [RemoteConfigRepository, inter_ads]`: hai vùng log rỗng, nên lượt này
  không đối chiếu được giá trị remote config.

## Câu hỏi chưa giải quyết

- 4 ID leftover thuộc placement nào? App mới (vc1) nên nhiều khả năng sheet chưa kịp khai
  đủ, nhưng cần ads-team xác nhận thay vì suy đoán.
- Vì sao `RemoteConfigRepository` rỗng ở lượt capture này? Lặp lại ở cả ba app chạy gần
  đây — có thể là vấn đề của filter chứ không phải của app.

# Audit checklist ads — aisong.generator.creatsong.music

- Run: `wf_98f2bcf4-b71` · mode `capture` · 2026-10-01
- Build: version_code `10` · audited_at `2026-10-01T07:57:57+00:00` (snapshot trùng, không phán trên ảnh chụp cũ)
- Sheet tab: gid `1748014371` (từ sheet, chưa có trong `apps.json`)
- Capture: `missed_home=[]` (tới được Home), `capture_reused_from=null`, `dev_build_signals=[]`
- `apk_scan_applicable=null` — lượt này **không quét APK**; toàn bộ bằng chứng từ log runtime
- `empty_filters`: `RemoteConfigRepository`, `inter_ads` (hai vùng log rỗng)

## Thống kê

| Mục | Khớp / Tổng |
|---|---|
| 1. Thông số kỹ thuật | 8 / 8 |
| 2. ID ads FO | 40 / 40 |
| 4. ID ads resume | 6 / 6 |
| **Tổng** | **54 / 54** |

`extra` 128 · `leftover_ids` 3.

Triage: cả bốn rổ rỗng — không dòng nào cần phán.

## Kết quả điều tra

- **confirmed** 0
- **disputed** 0
- **unresolved** 0
- App nằm trong `clean`: **sạch**, không còn dòng nào chưa kết luận.

Không có luận điểm nào để phản biện vì không có dòng lệch.

## Delta so lượt trước

- `broke` 0 · `fixed` 0 · `rows_added` 0 · `rows_removed` 0
- `new_leftover_ids`: `ca-app-pub-4973559944609228/7891648013` — ID mới xuất hiện trong build, chưa có trên checklist.

## ID chạy trong build nhưng không có trên sheet (3)

- `ca-app-pub-4973559944609228/7591275435`
- `ca-app-pub-4973559944609228/7891648013` *(mới ở lượt này)*
- `ca-app-pub-4973559944609228/7923437602`

Không phải lỗi — tool chỉ đối chiếu chiều sheet → build, nên ID ngoài checklist
không làm dòng nào fail. Nhưng cần ads-team xác nhận: placement mới chưa kịp ghi
vào sheet, hay ID không nên xuất hiện?

So lượt audit trước của app: `6006731028` không còn trong rổ leftover, `7891648013`
mới vào. Hai ID `7591275435` và `7923437602` vẫn giữ nguyên.

## Lưu ý đọc kết quả

- Tool chỉ đối chiếu chiều sheet → build. 54/54 **không** có nghĩa là không còn
  ID ngoài checklist đang chạy — xem mục trên, hiện có 3.
- Lượt này không quét APK (`apk_scan_applicable=null`). Mọi dòng khớp là khớp qua
  log runtime, không có lớp xác nhận thứ hai từ APK.

## Câu hỏi chưa giải quyết

- 3 ID leftover ở trên thuộc placement nào? Cần ads-team đối chiếu, đặc biệt
  `7891648013` vì mới xuất hiện ở lượt này.
- Vì sao lượt này `apk_scan_applicable=null` (chưa có bản APK cache cho vc10)?
  Nếu muốn lớp xác nhận APK thì cần kéo APK rồi chạy lại.

## Ghi chú về trang artifact

- Trang cũ của app (vc6, run `wf_a4e3ca2d-394`) có mục điều tra "3 ID chạy ở màn Home mà
  sheet không có dòng nào". Lượt này **không mang nội dung đó sang**: tập ID leftover đã
  đổi (`6006731028` ra, `7891648013` vào) và lượt này không điều tra placement, nên chép
  lại kết luận cũ là phát biểu vượt quá bằng chứng đang có.
- Wart của template: khi không có dòng lệch, dòng tóm tắt vẫn ghi "đã điều tra tới cùng ở
  dưới" trong khi khối `.probe` rỗng. Không sai dữ liệu, nhưng đọc hụt.

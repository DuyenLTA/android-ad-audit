# Audit ID ads — aisong.generator.creatsong.music (2.2.0, vc 13)

- Ngày: 28/10/2026 · máy 18311FDF60085N (Pixel 6) · chế độ capture (gọi từ /rc-check, lượt bot)
- Capture: user mới (pm clear) + user cũ, cả hai tới Home (missed_home rỗng)
- Kết quả: 54/54 dòng khớp, 0 lệch, 0 chưa kết luận → clean (không mở agent phán)
- delta: sheet mới thêm 54 dòng (lần đầu audit app này); 2 ID có trong APK nhưng không có trong sheet:
  `…/7591275435`, `…/7923437602` (tool chỉ đối chiếu sheet → build, không phải lệch)
- empty_filters: RemoteConfigRepository, inter_ads (không có dòng log nào khớp bộ lọc đó)
- ad_click trong capture: 0

## Câu hỏi chưa giải quyết
- 2 ID ngoài checklist ở trên: cần ads-team xác nhận có dùng hay là ID thừa.

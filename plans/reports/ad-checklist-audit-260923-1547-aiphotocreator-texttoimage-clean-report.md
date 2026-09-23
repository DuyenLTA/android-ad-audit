# Audit checklist ads — com.nxl.aiphotocreator.aivideogenerator.texttoimage

- Ngày chạy: 2026-09-23 15:49 (+07) · `audited_at` 2026-09-23T08:49:35Z
- Chế độ: `capture` (lái máy thật, `pm clear` trước lượt [new])
- Run workflow: `wf_290405f1-729`
- versionCode build: **17**
- Checklist: tab sheet `gid=2107085721` (chưa có trong `apps.json`, phân giải trực tiếp từ sheet)
- Digest checklist: `cf9a0059d206f253`
- Log capture: `tools/ad-checklist-diff/out/com.nxl.aiphotocreator.aivideogenerator.texttoimage-capture.log`
- Snapshot: `tools/ad-checklist-diff/snapshots/com.nxl.aiphotocreator.aivideogenerator.texttoimage.json`

## Kết quả

**54/54 dòng khớp. 0 dòng lệch.**

Mục checklist: `1. Thông số kỹ thuật` · `2. ID ads FO` · `4. ID ads resume`.

Triage 4 nhóm đều rỗng: `không có trong build` 0 · `chưa thấy trong log` 0 ·
`APK không kiểm được (ID nạp lúc chạy)` 0 · `khác` 0.

## Fan-out

Không có dòng nào chưa kết luận, nên agent không có gì để phán xử.
`confirmed` 0 · `disputed` 0 · `unresolved` 0 → app nằm nhóm `clean`.

## Đường capture

- `[new]` (sau `pm clear`): GrantPermissions → Language14 → Language24 → Onboarding
  (next ×2, wait, swipe, next) → Question → **Main**
- `[old]` (mở lại, không xoá dữ liệu): Splash → Question → **Main**
- Cả hai lượt đều tới Home, đợi thêm 4.0s tới khi log ads im. `missed_home` rỗng,
  `dev_build_signals` rỗng. Log không có tham chiếu nào tới ID mẫu `3940256099942544`.

## Delta so với snapshot trước

`changed: false`: `broke` 0 · `fixed` 0 · `rows_added` 0 · `rows_removed` 0 ·
`new_leftover_ids` 0.

## ID ngoài checklist (leftover, không mới)

Có 8 ID thật chạy trong build mà checklist không khai (chiều build → sheet). Lượt 14/09
đã thấy các ID này, nên delta không tính là mới:

`/1248152962` `/1374129757` `/2752806321` `/2836738907` `/6585375592` `/8175553853`
`/8434357894` `/8869476395` (tiền tố `ca-app-pub-4973559944609228`).

Không phải lệch trên dòng checklist. Cần ads-team xác nhận: đây là placement chưa ghi
vào sheet, hay ID không nên xuất hiện?

## Cảnh báo lượt chạy

Hai bộ lọc log không bắt được dòng nào: `RemoteConfigRepository`, `loadInterstitialAd`.
54 dòng ở trên không bị ảnh hưởng vì đều khớp qua đường khác.

## Câu hỏi chưa giải quyết

1. 8 leftover ID ở trên: ads-team cần xác nhận có nên thêm vào checklist không.

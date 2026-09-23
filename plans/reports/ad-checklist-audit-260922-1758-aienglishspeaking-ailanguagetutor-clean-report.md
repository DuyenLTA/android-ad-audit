# Audit checklist ads — com.aienglishspeaking.ailanguagetutor.aienglishlearning.aitutor

- Ngày chạy: 2026-09-22 18:00 (+07) · `audited_at` 2026-09-22T11:00:36Z
- Chế độ: `capture` (lái máy thật, `pm clear` trước lượt [new])
- Run workflow: `wf_472717f4-3a8`
- Máy: `99261FFAZ0077C` · versionCode build: **6**
- Checklist: tab sheet `gid=837344454` (chưa có trong `apps.json`, phân giải trực tiếp từ sheet)
- Digest checklist: `cba80895967112a8`
- Log capture: `tools/ad-checklist-diff/out/com.aienglishspeaking.ailanguagetutor.aienglishlearning.aitutor-capture.log`
- Snapshot: `tools/ad-checklist-diff/snapshots/com.aienglishspeaking.ailanguagetutor.aienglishlearning.aitutor.json`

## Kết quả

**54/54 dòng khớp. 0 dòng lệch.** Không có leftover ID (ID chạy trong build mà
checklist không khai).

| Mục checklist | Số dòng | Khớp | Lệch |
|---|---|---|---|
| 1. Thông số kỹ thuật | 8 | 8 | 0 |
| 2. ID ads FO | 40 | 40 | 0 |
| 4. ID ads resume | 6 | 6 | 0 |

Triage 4 nhóm đều rỗng: `không có trong build` 0 · `chưa thấy trong log` 0 ·
`APK không kiểm được (ID nạp lúc chạy)` 0 · `khác` 0.

## Fan-out

Không dòng nào chưa kết luận → không có gì để agent phán xử.
`confirmed` 0 · `disputed` 0 · `unresolved` 0 → app nằm nhóm `clean`.

## Đường capture

- `[new]` (sau `pm clear`): Splash → Language14 → Language24 → (rớt ra
  NotificationShade + NexusLauncher, mở lại app) → Language24 → Onboarding
  (next ×2, wait, swipe, next) → Question → Billing (close) → **Main**
- `[old]` (mở lại, không xoá dữ liệu): Splash → Question → Billing (close) → **Main**
- Cả hai lượt đều tới Home, đợi thêm 4.0s tới khi log ads im. Không có
  `missed_home`, không có dấu hiệu dev build.

## Delta

Lượt audit **đầu tiên** của package này — repo chưa có snapshot trước đó.
`rows_added` 54 · `rows_removed` 0 · `broke` 0 · `fixed` 0. Chưa có baseline để
so; delta có nghĩa từ lượt sau.

## Cảnh báo lượt chạy

Hai bộ lọc log không bắt được dòng nào: `RemoteConfigRepository`, `inter_ads`.
Không ảnh hưởng 54 dòng ở trên (đều khớp qua đường khác), nhưng nghĩa là lượt
này không có log remote-config thô để đối chiếu thêm.

Tool chỉ đối chiếu chiều **sheet → build**: khớp hết không đồng nghĩa build
không còn ID nào ngoài checklist ở các màn capture chưa đi qua.

## Câu hỏi chưa giải quyết

Không có. Không dòng nào cần ads-team xác nhận trong lượt này.

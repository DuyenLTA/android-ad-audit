# Audit checklist ads — lingospeak.english.learnlanguage.speak

- Run: `wf_9942d0e0-4d8` · mode `capture` · 2026-09-30
- Build: version_code `8` · audited_at `2026-09-30T03:24:56+00:00` (snapshot trùng, không phán trên ảnh chụp cũ)
- Sheet tab: gid `1547158364` (từ sheet, chưa có trong `apps.json`)
- Capture: `missed_home=[]` (tới được Home), `capture_reused_from=null`, `dev_build_signals=[]`, `apk_scan_applicable=true`
- `empty_filters`: `RemoteConfigRepository`, `inter_ads` (hai vùng log rỗng)

## Thống kê

| Mục | Khớp / Tổng |
|---|---|
| 1. Thông số kỹ thuật | 7 / 8 |
| 2. ID ads FO | 40 / 40 |
| 4. ID ads resume | 6 / 6 |
| **Tổng** | **53 / 54** |

`extra` 157 · `leftover_ids` 1.

Triage: `không có trong build` 0 · `chưa thấy trong log` 0 · `APK không kiểm được` 0 · `khác` 1.

## Kết quả điều tra

### confirmed (1) — App ID, mục 1. Thông số kỹ thuật

Sheet ghi: `APP ID:ca-app-pub-4973559944609228~1032914015`
Verdict: **checklist-sai** (định dạng ô), **không phải bug build**.

Bằng chứng:

- `apk_strings.py --package lingospeak.english.learnlanguage.speak`:
  - `KHÔNG  APP ID:ca-app-pub-4973559944609228~1032914015` (nguyên cụm, kèm tiền tố)
  - `CÓ  ca-app-pub-4973559944609228~1032914015  (AndroidManifest.xml)`
  - `CÓ  1032914015  (AndroidManifest.xml)`
- Runtime: `capture.log:877` — UserMessagingPlatform, PID 17312 (trùng PID các dòng `FOR_TESTER_*`, tức process của chính app, không phải lô FA-SVC app khác) in `Received app ID: ca-app-pub-4973559944609228~1032914015`.

Tức App ID trong build **đúng** như checklist. Dòng rơi vào rổ `khác` là artefact của phép so chuỗi nguyên ô: ô sheet thừa tiền tố `APP ID:`.

Giới hạn: phần "prefix đến từ ô sheet" là suy ra từ chuỗi `value`, không xem được ô gốc. Dù prefix đến từ sheet hay từ bước parse, kết luận "không phải bug build" vẫn đứng.

### disputed (0) — không có

### unresolved (0) — không có

## Lỗ tool phát hiện được

Một dòng, nhưng lộ đúng một lỗ. Phép kiểm "có trong APK không" chạy trên chuỗi ô **thô**, không chuẩn hoá:

1. Normalizer thiếu bước bóc tiền tố nhãn. Ô ghi `APP ID:<id>` → tool tìm nguyên cụm, tất nhiên không thấy. Tách token ad-ID (`ca-app-pub-\d+[~/]\d+`) rồi tìm lại là ra ngay ở `AndroidManifest.xml`.
2. `build_ad_ids` chỉ bắt unit ID dạng `/`, bỏ App ID dạng `~`. Bằng chứng: 67 phần tử, phần tử `~` duy nhất là placeholder `ca-app-pub-0000000000000000~0000000000`. Nên fallback tra mảng cũng không cứu được row App ID.

Hệ quả: mọi ô checklist có chữ mô tả dính kèm giá trị sẽ bị đẩy vào rổ `khác` với note "nghi checklist ghi giá trị không tồn tại trong build" — note sai hướng, dễ dẫn người đọc đi mở bug build.

Đề xuất: trước khi so, strip `^\s*[A-Za-z ]+:\s*` và retry bằng token ad-ID trích được; đồng thời mở regex `build_ad_ids` cho cả dạng `~`.

## Lưu ý đọc kết quả

Tool chỉ đối chiếu chiều sheet → build. Khớp hết **không** có nghĩa là không còn ID ngoài checklist đang chạy trong build.

## Câu hỏi chưa giải quyết

- Ô `App ID` trên sheet (tab gid 1547158364) có thật sự chứa tiền tố `APP ID:` không, hay prefix sinh ra ở bước parse? Cần ads-team mở ô gốc xác nhận.

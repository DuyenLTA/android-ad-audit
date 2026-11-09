# Audit checklist ads — com.ai.aiphoto.aivideo.creator.generator

- Run: wf_ee297737-245 · mode: capture (máy thật, pm clear) · version_code 5 · audited_at 2026-10-20T05:03Z
- Sheet tab gid=443872257 (từ sheet, chưa có trong apps.json)

## Kết quả
- Khớp 52/54, lệch 2
  - 1. Thông số kỹ thuật 8/8
  - 2. ID ads FO 40/40
  - 4. ID ads resume 4/6
- confirmed: 0 · disputed: 0 · unresolved: 1 (2 dòng)

## Unresolved — 501_aoa_high, 501_aoa (4. ID ads resume)
- Snapshot: label rỗng, value = tên placement, alt_values rỗng → ô ID trên sheet trống, tên placement bị đọc sang cột value.
- Các dòng cùng mục (502_native_high, 503_inter…) có ID đầy đủ, found=true.
- APK: không có chuỗi `501_aoa_high`/`501_aoa`/`aoa_high`; có `501`, `resume` → không kết luận được là build thiếu.
- capture.log:333-334 AppOpenManager disableAppResumeWithActivity (Splash, Uninstall); không có FOR_TESTER_LOAD_AD/SHOW_AD AppOpen nào → lượt capture không đi luồng background→foreground, chưa biết ID AOA resume runtime.
- Việc cần làm: ads-team điền ID AOA resume vào sheet; capture thêm luồng resume (HOME rồi mở lại app).

## Cảnh báo lượt chạy
- missed_home = ["old"]: lượt user cũ không tới được Home.
- empty_filters = ["RemoteConfigRepository"]: không có log RC từ filter này.
- leftover_ids (build request, sheet không có): 4842186845, 5003074841, 5135111792, 5537602329, 5675233856, 6448193469, 9655529824. Trong đó 5003074841/6448193469, 5537602329/5135111792 là cặp inter (inter_ads canRequestAd) → nghi inter in-app ngoài phạm vi checklist.
- Delta: lần đầu snapshot đủ dòng; 2 dòng 501 "broke" (mới thêm vào sheet nhưng không có ID).

## Câu hỏi chưa giải quyết
- ID AOA resume thực tế của build là gì? Cần sheet điền ID + capture luồng resume.
- 7 leftover IDs có cần đưa vào checklist không?

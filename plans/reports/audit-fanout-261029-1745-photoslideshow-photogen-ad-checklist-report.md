# Audit checklist ads — photoslideshow.videoslideshow.addimage.photogen

- Run: wf_a60eca8d-1d9 · mode: capture (máy thật, pm clear) · version_code 1 · audited_at 2026-10-29T10:45Z
- Sheet tab gid=1816202499 (từ sheet, chưa có trong apps.json)

## Kết quả
- Khớp 52/52, lệch 0 → clean
  - 1. Thông số kỹ thuật 4/4
  - Facebook Client Token 2/2
  - 2. ID ads FO 40/40
  - 4. ID ads resume 6/6
- confirmed: 0 · disputed: 0 · unresolved: 0

## Lượt capture
- new: GrantPermissions → Splash → AdActivity → Language11 → Language21 → Onboarding → Question → AdActivity → Main (tới Home).
- old: Splash → AdActivity → Question → AdActivity → Main (tới Home).
- missed_home: [] · leftover_ids: [] · new_leftover_ids: []
- empty_filters: RemoteConfigRepository, inter_ads (không có log từ 2 filter này).
- Delta: lần đầu snapshot, 52 dòng mới, không broke/fixed.

## Ghi chú cách đọc
- Tool chấm khớp khi ID có trong capture.log bất kể dòng nào. 29/46 ID FO+resume chỉ xuất hiện trong dòng dump cấu hình `FO_VslTemplate4FirstOpenSDK` (vd `Banner splash: [...]`, `LFO1: [...]`), không có dòng load/show — chủ yếu tier thấp (không request vì tier cao đã xử lý xong).
- leftover rỗng → build không request ID nào ngoài sheet, nên không có dấu hiệu ID bị thay như ca learnenglish 13/10. Dump là cấu hình chính build nạp, vẫn là bằng chứng build mang đúng ID sheet; chỉ chưa chứng minh runtime từng request từng tier.
- Resume (501–503): lượt capture không đi luồng HOME→mở lại; 6/6 khớp có thể từ dump/khai báo.

## Câu hỏi chưa giải quyết
- Không có.

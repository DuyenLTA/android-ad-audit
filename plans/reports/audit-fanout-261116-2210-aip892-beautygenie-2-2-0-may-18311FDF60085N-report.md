# Audit ID ads — com.aimakeup.aifaceeditor.facemakeup.faceswap (AIP892 BeautyGenie 2.2.0, vc 16) — máy 18311FDF60085N

Run: wf_e8875060-60a · mode capture (pm clear app) · 16/11/2026

## Kết quả
- 1. Thông số KT: 8/8 khớp
- 2. ID ads FO: 40/40 khớp
- 4. ID ads resume: 6/6 khớp
- 3. ID ads inapp: 2/17 "thấy" — 15 dòng không phải lệch: sheet mục 3 chỉ ghi tên placement + độ ưu tiên (inter_back(_high), reward_img_vid(_high), inter_style(_high), native_result_img_vid(_high), native_loading(_high), native_reason_uninstall(_high), inter_uninstall(_high)) + 1 dòng header "Ad Name"; log chỉ in unit ID nên không đối chiếu được theo tên.
- confirmed 0 · disputed 0 · unresolved 2 nhóm (14 dòng placement không có ID; 1 dòng header bị parse nhầm).

## Việc cần làm
- Ads-team: mục 3 sheet chưa có ad unit ID cho các placement inapp → bổ sung ID nếu muốn đối chiếu.

## Câu hỏi chưa giải quyết
- Không.

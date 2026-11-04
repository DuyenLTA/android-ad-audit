# Phase 1: Map rule → checker

## Overview
Ưu tiên: cao · Status: Done · Đọc sheet policy live, gắn từng rule với một checker và loại bằng chứng.

## Key insights
- Số N° trong sheet bị nhảy (1,3,12,14...) → key theo (tab, N°), không theo thứ tự dòng
- Cột B (loại ad) chỉ ghi ở dòng đầu nhóm → phải điền xuôi xuống (forward-fill)
- Sub_VN có cột C = nhóm rule, cột D = chi tiết; Ads có cột C = rule, cột D trống

## Bảng map (tab Đối tác, bao trùm Ad_VN)
| N° | Rule | Checker | Loại |
|---|---|---|---|
| 1 | Inter chỉ đặt khi có action chuyển màn | `inter_changes_screen`: activity/màn trước click ≠ sau khi tắt | auto |
| 2 | Inter hiện ngay sau click (hoặc sau loading) | `inter_latency`: click → AdActivity ≤ ngưỡng, nếu chậm thì phải có loading trong UI dump | auto |
| (Ad_VN 1) | Loading ad trước inter | `inter_loading_before`: chụp UI dump liên tục từ click đến AdActivity | auto |
| 3 | Không show inter video trước splash | `inter_not_before_splash`: thứ tự trong logcat AdActivity vs splash activity | auto |
| 4,9,17,31 | Click ad có xử lý | `ad_click_handled`: bấm ad → foreground đổi sang browser/Play | auto |
| 29 | Click CTA native có xử lý | `ad_click_handled` (bấm vào CTA) | auto |
| 5 | Nút tắt ad trước 15s | `close_button_within_15s`: poll UI, dùng `device_close_button` | auto |
| 6 | Nền resume không trong suốt | screenshot lúc resume → Claude | visual |
| 7,8 | Không show resume sau permission/rate/privacy/update... | `resume_blocked_after_utility`: đi flow → quay về app → logcat không có app open show | auto (cần flow) |
| 10,14,21 | Không ad trên màn webview | `no_ad_on_webview`: UI dump có WebView + ad view cùng lúc → FAIL | auto |
| 11,18 | Loading trước banner/native | `placeholder_first`: dump đầu tiên khi vào màn phải có shimmer/loading | auto |
| 12,19 | Kích thước loading ≥3/4 ad | `placeholder_size_ratio`: bounds loading vs ad | auto |
| 13,20 | Không bất thình lình xuất hiện | gộp vào `placeholder_first` | auto |
| 15,22 | Content không đè ad | `ad_content_overlap`: giao bounds ad với node clickable khác | auto |
| 16,23 | Không đặt ad khi không có data | screenshot + UI dump → Claude | visual |
| 24 | Bố cục native không cắt/đè | screenshot crop vùng ad → Claude | visual |
| 25 | Nền ad khác nền app | crop + màu trung bình viền → gợi ý, Claude kết luận | visual |
| 26 | AdChoices nằm trong khung | `adchoices_inside`: ≥50% bounds trong khung native | auto (chỉ ad thật) |
| (Ad_VN 38) | Attribution ≥15px | `attribution_min_size` | auto |
| (Ad_VN 41) | MediaView ≥120x120dp | `mediaview_min_size` (px → dp theo density) | auto |
| 30 | Reward có "Watch an ad" | text UI dump quanh nút reward, không thấy → Claude nhìn icon | auto + visual |
| 32 | Nút link app/web khác có "AD" | Claude | visual |
| 33 | App AI có nút report | Claude trên màn result | visual |

## Requirements
- `policy-checkers.yaml`: `{tab, no, checker, kind: auto|visual|manual, placements: [inter|native|banner|resume|reward|sub]}`
- `policy_source.py`: tải tab qua CSV (dùng lại `checklist_source.sheet_get`), forward-fill cột B, trả list rule
- Rule có trong sheet mà không có trong yaml → kết quả `CHƯA CÓ CHECKER`

## Files
Tạo: `tools/ad-policy-check/policy_source.py`, `tools/ad-policy-check/policy-checkers.yaml`, `tools/ad-policy-check/tests/test_policy_source.py`

## Todo
- [ ] Parse 3 tab (Ad_VN, Đối tác, Sub_VN), forward-fill
- [ ] Viết yaml map theo bảng trên
- [ ] Test: N° nhảy, ô gộp, rule chưa map

## Success criteria
In ra danh sách rule kèm checker; rule chưa map được liệt kê riêng.

## Risks
Sheet bị sửa nội dung nhưng giữ N° → map sai. Lưu hash text rule trong yaml, lệch thì cảnh báo.

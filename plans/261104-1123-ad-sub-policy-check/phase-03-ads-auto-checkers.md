# Phase 3: Checker tự động cho Ads

## Overview
Ưu tiên: cao · Status: Todo · Mỗi checker là một hàm thuần: nhận gói bằng chứng, trả `{status, reason, evidence_refs}`. Không đụng tới máy → test được bằng gói mẫu.

## Checker + ngưỡng
| Checker | Cách chấm | Ngưỡng |
|---|---|---|
| `inter_loading_before` | Có frame nào giữa click và show mà UI có loading/progress (hoặc khác before.png) | ≥1 frame |
| `inter_latency` | show - click; nếu > ngưỡng mà không có loading → FAIL | 1.0s (chỉnh được) |
| `inter_changes_screen` | activity/màn chính của after ≠ before | |
| `inter_not_before_splash` | AdActivity đầu tiên phải sau splash activity | |
| `close_button_within_15s` | giây nút tắt xuất hiện | ≤15s |
| `ad_click_handled` | foreground sau khi bấm ≠ app, hoặc có intent VIEW trong log | trong 3s |
| `no_ad_on_webview` | ad view và WebView của app cùng hiện | 0 lần |
| `placeholder_first` | frame đầu khi vào màn đã có vùng ad (loading hoặc ad) | frame ≤500ms |
| `placeholder_size_ratio` | diện tích loading / diện tích ad | ≥0.75 |
| `ad_content_overlap` | giao bounds ad với node của app | 0px |
| `adchoices_inside` | % diện tích AdChoices nằm trong khung native | ≥50% |
| `attribution_min_size` | w,h của nhãn "Ad"/"Quảng cáo" | ≥15px |
| `mediaview_min_size` | MediaView theo dp | ≥120x120dp |
| `resume_blocked_after_utility` | không có app open show sau khi quay về từ màn tiện ích | 0 lần |

Không chắc chắn (không tìm được node, thiếu frame) → `CẦN XEM` và chuyển sang Claude ở phase 4, không đoán PASS.

## Files
Tạo: `tools/ad-policy-check/checkers/` (mỗi nhóm một file: `interstitial_checkers.py`, `native_banner_layout_checkers.py`, `ad_click_checkers.py`, `resume_checkers.py`), `checker_registry.py`, `tests/fixtures/` (gói bằng chứng mẫu đúng/sai)

## Todo
- [ ] Nhận diện ad view trong UI dump (AdView, NativeAdView, id/desc của GMS, cấu hình id riêng theo app nếu cần)
- [ ] Từng checker + test với fixture đúng/sai
- [ ] Ngưỡng để trong yaml, không viết cứng

## Success criteria
Mọi checker có test đúng/sai; chạy trên gói bằng chứng thật không crash; trạng thái không chắc → CẦN XEM.

## Risks
Native custom layout của từng app khác id → nhận diện sai. Fallback: tìm theo class `NativeAdView` cha + AdChoices; nếu vẫn không thấy thì CẦN XEM.

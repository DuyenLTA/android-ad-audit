# Phase 5: Sub / paywall

## Overview
Ưu tiên: trung bình (sau MVP Ads) · Status: Todo · Chủ yếu đọc text + nhìn ảnh paywall, ít đo thời gian.

## Map rule Sub_VN
| N° | Rule | Cách chấm | Loại |
|---|---|---|---|
| 1 | Hiện giá, quyền lợi, thời hạn, số ngày trial | text UI dump của từng gói → Claude xác nhận đủ 4 ý | auto + visual |
| 2 | Có trial thì "start with X days trial then <giá>" | regex trên text, Claude xác nhận câu tương đương | auto + visual |
| 3 | Text trial không là button riêng | node chứa "trial" có clickable riêng mà không chứa giá → FAIL | auto |
| 4 | Text trial nhỏ hơn giá/thời hạn | so chiều cao bounds text (UI dump không có font size) → Claude xác nhận trên ảnh | visual |
| 5 | Popup thanh toán Play: ngày bắt đầu trial / trừ tiền, tên gói không chứa "trial" | bấm gói → chụp sheet billing của Play → đọc text | auto + visual |
| 6 | Sale hiện giá trước và sau | 2 giá trong cùng gói | auto + visual |
| 7 | "Cancel anytime" | text tương đương (đa ngôn ngữ) | auto |
| 8 | Link Privacy & ToS, mở in-app | bấm → foreground vẫn là app (WebView) | auto |
| 9 | Sau khi mua có "Cancel sub" → mở trang subscriptions của Play | tool tự mua (mọi tài khoản là license test) rồi bấm Cancel sub | auto |
| 10 | Restore (iOS) | không áp dụng Android | N/A |

## Vào paywall
Dùng flow (splash paywall / nút premium); thêm bước `paywall` trong flow nếu chưa có. Mỗi lần vào paywall: ảnh + UI dump + text từng gói.

## Files
Tạo: `tools/ad-policy-check/checkers/subscription_paywall_checkers.py`, `evidence_paywall.py`

## Todo
- [ ] Gói bằng chứng paywall
- [ ] Checker 3,6,7,8 tự động
- [ ] Lượt mua thật: chụp sheet billing, mua, kiểm "Cancel sub", huỷ sub

## Risks
- Mua bằng tài khoản license test (mọi tài khoản của user), sau đó huỷ sub để lượt sau còn thấy paywall
- Paywall nhiều ngôn ngữ: dùng Claude xác nhận thay vì chỉ regex tiếng Anh

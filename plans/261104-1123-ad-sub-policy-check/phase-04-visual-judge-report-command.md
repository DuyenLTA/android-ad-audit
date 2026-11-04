# Phase 4: Claude chấm visual + report + command

## Overview
Ưu tiên: cao · Status: Todo · Gộp kết quả auto, cho Claude chấm các rule visual/CẦN XEM, xuất artifact, thêm `/policy-check`.

## Luồng `/policy-check <package> [--ads|--sub|--tab "Đối tác"]`
1. Kiểm bản đang cài là release (dùng lại `build_identity`, sai thì dừng + báo Discord)
2. `policy_runner.py --capture` → gói bằng chứng + `auto-results.json`
3. Claude đọc `visual-queue.json` (rule visual + CẦN XEM, mỗi mục có: text rule, ví dụ đúng/sai trong sheet, ảnh cần nhìn) → ghi `visual-results.json` với lý do ngắn
4. `policy_report.py` gộp → artifact (template giống audit-fanout) + `plans/reports/`
5. Publish artifact, đưa link, báo qa-auto/Discord

## Prompt chấm visual (cố định trong command)
- Chỉ chấm theo text rule + ví dụ trong sheet, không tự thêm luật
- Mỗi kết luận phải chỉ ra vùng trên ảnh; không chắc → CẦN XEM, không đoán
- Link ví dụ streamable/drive trong sheet: chỉ đưa vào report để người xem, Claude không xem video

## Report
- Đầu trang: số FAIL / CẦN XEM / BLOCKED, danh sách FAIL kèm ảnh
- Theo nhóm (Inter / Resume / Banner / Native / Reward / Sub), mỗi rule: trạng thái, lý do, ảnh, đoạn log
- Rule chưa có checker → mục riêng "chấm tay"

## Files
Tạo: `tools/ad-policy-check/policy_runner.py`, `policy_report.py`, `.claude/commands/policy-check.md`. Sửa: dùng lại `artifact_report_builder.py`/template (thêm block policy, không copy file).

## Todo
- [ ] Runner gộp phase 2+3
- [ ] Hàng đợi visual + format kết quả
- [ ] Report + artifact
- [ ] Command + hướng dẫn trong README
- [ ] Chạy thật 1 app, so với kết quả QA chấm tay

## Success criteria
1 lệnh ra artifact có đủ mọi rule của tab đã chọn; kết quả khớp QA chấm tay trên app mẫu (lệch thì ghi lý do).

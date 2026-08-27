# Brainstorm summary: android ad-config checklist diff tool

## Problem
QA cần đối chiếu thông số kỹ thuật (Adjust config, Facebook App ID/Client Token) và ID quảng cáo AdMob trong 1 app Android với checklist Google Sheet. Đã làm thủ công 1 lần thành công cho app "Nexus - AI Video Generator" (xem artifact: https://claude.ai/code/artifact/afe8d193-8bd7-4839-9d29-7acacb3e6641). User muốn tái sử dụng quy trình này cho nhiều app khác.

## Approach đã thử & bài học (quan trọng cho plan)
- Capture bằng `adb logcat` trên máy thật, KHÔNG dùng `adb logcat -s TAG:*` (exact-match) vì tag thật là các biến thể có prefix (vd `FOR_TESTER_CONFIG`, `FOR_TESTER_LOAD_AD`, `FOR_TESTER_PRELOAD`, `FO_VslTemplate4FirstOpenSDK`). User gọi các tên này là "filter" kiểu Android Studio Logcat (substring match), không phải tag chính xác — phải capture full log rồi grep substring.
- Auto-tap qua adb để trigger debug dump KHÔNG đáng tin cậy: màn splash chỉ hiện ~1-2s (ngắn hơn round-trip của tool call), từng tap lạc sang Chrome và gõ nhầm text vào 1 form web lạ (không submit, không hại gì nhưng là bài học rủi ro). Quyết định: KHÔNG tự động hoá phần trigger/tap — user tự capture logcat bằng tay, đưa file/text log cho tool.
- Matching nên làm theo **giá trị**, không theo tên label/placement key — vì tên đặt khác nhau tuỳ dev/app, nhưng giá trị (token, ID) là duy nhất nên so theo giá trị generalize tốt hơn qua nhiều app.
- Checklist sheet format: 2 cột (A=label, B=giá trị), có dòng section header (cột B trống), ví dụ sheet mẫu: https://docs.google.com/spreadsheets/d/14XivZl9VPAnyf8hYICgRh-TOUmkGTZDCqoyWmPM57hM

## Giải pháp đồng ý
Script Python độc lập `check_ads.py`, không tích hợp vào project nào có sẵn (user chọn "đứng độc lập" thay vì tích hợp android-qa-agent).

**Input:**
- `--sheet <google sheet url>` — checklist
- `--log <file>` — logcat đã capture sẵn (không tự trigger)
- `--filter <substring>` — lặp lại nhiều lần, mỗi filter = 1 nhóm cần check (vd `--filter FOR_TESTER --filter VslTemplate4FirstOpenSDK`)
- `--out <html path>` — output report (optional, default report.html)

**Xử lý:**
1. Tải sheet qua CSV export URL (theo redirect tự động).
2. Parse thành list (section, label, giá trị mong đợi); dòng cột B trống = section header.
3. Với mỗi `--filter`, lọc log lines chứa substring đó (case-insensitive).
4. Trích giá trị ứng viên từ các dòng đã lọc: pattern `ca-app-pub-\d+[/~]\d+`, giá trị sau dấu `:`, phần tử trong `[...]`.
5. Đối chiếu theo giá trị: sheet có, log không thấy → MISSING; log có, sheet không có → EXTRA; cả 2 → MATCH.
6. Xuất HTML report (tái dùng visual style của artifact hôm nay — dashboard/QA report, mono cho ID, semantic color pass/fail) + tóm tắt ra terminal.

**Ngoài phạm vi (explicit, tránh scope creep):**
- Không tự động trigger debug dump (tap logo, navigate tutorial) — đã chứng minh không an toàn/tin cậy.
- Không tích hợp UI/Streamlit, không tích hợp android-qa-agent.
- Không cần fuzzy-match label — chỉ match giá trị.

## Vị trí
Đặt ở đâu do planner/user quyết — gợi ý: thư mục tool cá nhân độc lập (không thuộc project cụ thể), có thể chạy `python check_ads.py ...` từ bất kỳ đâu.

## Unresolved questions
- Sheet của các app khác có chắc cùng format 2 cột A/B không, hay khác cấu trúc? (Chưa kiểm chứng ngoài 1 sheet mẫu.)
- 6 ID "AppResume" thấy trong log nhưng không có trong sheet ở lần check đầu — chưa rõ có nên coi extra-not-in-checklist là lỗi cứng hay chỉ cảnh báo (hiện đề xuất: cảnh báo, không fail).

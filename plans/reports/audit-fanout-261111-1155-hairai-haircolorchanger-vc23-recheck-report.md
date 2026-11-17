# Audit fan-out — com.hairai.hairstyletryon.haircolorchanger (lượt rc-check 11/11/2026)

- Run: wf_a394d39e-a3d · mode: capture · v3.0.0 (versionCode 23) · tab gid=1210594131 · máy 3454184009000HI
- versionCode 23 trùng snapshot 09/11/2026 (checklist digest không đổi) → runner dùng lại capture/triage của lượt wf_34166607-821, không capture lại, không `pm clear`.

## Kết quả
- 54/54 khớp. confirmed 0 · disputed 0 · 4 rổ triage rỗng.
- Agent ghi 2 mục unresolved chỉ mang tính ghi nhận: (1) không còn dòng nào cần phán; (2) leftover ID inter 5186081670 có load thật (No fill) nhưng không gắn dòng checklist.

## leftover_ids — 6 (build load, sheet mục "3. ID ads inapp" trống)
- Interstitial: 4031770345, 4087610665, 5186081670, 6466361999. Native: 2910260367, 6136841893.

## Cảnh báo
- missed_home=['new'] (như 09/11): luồng new user của runner không tới Home.

## Câu hỏi chưa giải quyết
- Danh sách in-app chính thức để điền mục 3.

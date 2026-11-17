# Audit fan-out — com.nxl.aienglishtutor.ailearnlanguage.aichatbot (lượt rc-check 11/11/2026)

- Run: wf_f620d3a8-37c · mode: capture · v2.5.0 (versionCode 23) · tab gid=1899009360 (từ sheet, chưa có trong registry) · máy 99261FFAZ0077C
- Capture mới: `pm clear` app, luồng new user Splash → LFO1 → LFO2 → OB → Question → inter → RevenueCatPaywall.

## Kết quả
- 54/54 khớp (Thông số KT 8/8 · ID ads FO 40/40 · ID ads resume 6/6). confirmed 0 · disputed 0 · unresolved 0 → clean.
- leftover_ids: 0.

## Cảnh báo
- Capture dừng ở RevenueCatPaywallActivity, không tới Home (runner hết cách thử ở paywall). Tool chỉ đối chiếu chiều sheet → build, ID ngoài checklist ở Home không được soi.

## Câu hỏi chưa giải quyết
- Không.

# audit-fanout · com.nxl.aiphotocreator.aivideogenerator.texttoimage · 09/11/2026 16:30

- Máy: Pixel 4 `99261FFAZ0077C` · bản cài 2.8.0 (release) · SDK FO 3.7.1 (Next-Gen, theo tin build)
- Chế độ: `capture` (pm clear app, lái lượt new + old) · run `wf_8e25c6f8-acf`
- Kết quả: **54/54 khớp** · confirmed 0 · disputed 0 · unresolved 0 → `clean`
- Capture: cả hai lượt (new, old) dừng ở Onboarding, chưa tới Home (lái hết cách thử ở OB). Các vị trí sau Onboarding
  (Question, paywall, Home) không có request trong log capture → chỉ đối chiếu chiều sheet → build cho các dòng đã thấy.
- Lượt capture có `KEYCODE_BACK` trên AdActivity (inter splash) sau 9s chờ.

## Unresolved questions
- Không.

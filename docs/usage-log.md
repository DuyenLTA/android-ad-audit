# Log sử dụng — audit-fanout

Mỗi lượt chạy thật thêm một dòng. Cột "Test tay" là thời gian tester ước tính nếu làm cùng việc bằng tay; điền cột này thì tính được thời gian tiết kiệm. Dấu `?` là chưa điền.

Thời gian tool đo được (`plans/reports/perf-260911-1750-…`): capture trên máy ~120 giây,
so checklist ~0,4 giây, lớp agent 7–13 phút mỗi app khi còn dòng chưa chốt.

| Ngày | App | vc | Kết quả | Lỗi checklist xác nhận | Report | Test tay |
|---|---|---|---|---|---|---|
| 11/09, 14/09/2026 | ai.photogenerator…aiart | 24 | 71/72 khớp | 1 | [artifact](https://claude.ai/code/artifact/bd4b9714-a489-4dfa-80b0-a1c6fe1b721b) | ? |
| 13/09/2026 | com.remote.casttotv.screenmirroring | 11 | 57/58 (1 dòng do tool) | 0 | `plans/reports/audit-fanout-260913-0937-…` | ? |
| 13/09/2026 | com.aiphotoeditor…aibeauty | 33 | 71/76, 3 dòng tranh chấp | 2 | `plans/reports/audit-fanout-260913-1240-…` | ? |
| 14/09/2026 | com.nxl.aiphotocreator…texttoimage | 12 | 9/54, bản dev, dừng | 0 | `plans/reports/audit-fanout-260914-1143-…` | ? |
| 14/09/2026 | com.nxl.aiphotocreator…texttoimage | 14 | 54/54 | 0 | `plans/reports/audit-fanout-260914-1343-…` | ? |
| 14/09/2026 | aisong.generator.creatsong.music | 6 | 54/54, 3 ID không có trên sheet | 3 | `plans/reports/ad-audit-fanout-260914-1720-…` | ? |
| 21/09/2026 | com.hairai.hairstyletryon.haircolorchanger | 19 | Sạch | 0 | `plans/reports/audit-260921-1903-…` | ? |
| 21/09/2026 | com.nxl.aienglishtutor…aichatbot | 19 | Sạch | 0 | `plans/reports/ad-checklist-audit-260921-1007-…` | ? |
| 21/09/2026 | com.aivideogenerator…imagetoimage | 37 | Sạch | 0 | `plans/reports/ad-checklist-audit-260921-1932-…` | ? |
| 22/09/2026 | com.aienglishspeaking…aitutor | 6 | Sạch | 0 | `plans/reports/ad-checklist-audit-260922-1758-…` | ? |
| 23/09/2026 | com.nxl.aiphotocreator…texttoimage | 17 | 54/54 | 0 | `plans/reports/ad-checklist-audit-260923-1547-…` | ? |
| 10/10/2026 | com.hairai.hairstyletryon.haircolorchanger | 21 | Sạch | 0 | [artifact](https://claude.ai/artifact/6ZFRdCkvAj9meWqyrqP2Wn) | ? |

Tổng: 12 lượt, 9 app, 6 lỗi checklist xác nhận. Chưa có ticket Jira.

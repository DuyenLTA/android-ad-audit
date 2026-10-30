# Log sử dụng — audit-fanout

Mỗi lượt chạy thật thêm một dòng. "Test tay (TB)" là thời gian tester ước tính nếu làm cùng việc bằng tay, lấy trung bình; spec dài hay ngắn thì lệch lên xuống. "Tiết kiệm" = Test tay − Thời gian tool. Thời gian tool là thời gian máy chạy; trong lúc đó tester làm việc khác được, nên con số tiết kiệm là mức thấp nhất.

Test tay (TB): **30 phút** cho một lần đối chiếu checklist quảng cáo của một app (tester ước tính 22/10/2026).
Thời gian tool: **ước tính** từ `plans/reports/perf-260911-1750-…`: capture trên máy ~2 phút, so checklist
~0,4 giây; khi còn dòng chưa chốt thì thêm lớp agent ~13 phút (judge + verify), chạy lại ~7 phút.
Lượt không còn dòng chưa chốt thì không mở agent nào, tính ~3 phút.

| Ngày | App | vc | Kết quả | Lỗi checklist xác nhận | Report | Thời gian tool | Test tay (TB) | Tiết kiệm |
|---|---|---|---|---|---|---|---|---|
| 11/09, 14/09/2026 | ai.photogenerator…aiart (2 lượt) | 24 | 71/72 khớp | 1 | [artifact](https://claude.ai/code/artifact/bd4b9714-a489-4dfa-80b0-a1c6fe1b721b) | ~20 phút (13 + 7) | 60 phút | 40 phút |
| 13/09/2026 | com.remote.casttotv.screenmirroring | 11 | 57/58 (1 dòng do tool) | 0 | `plans/reports/audit-fanout-260913-0937-…` | ~15 phút | 30 phút | 15 phút |
| 13/09/2026 | com.aiphotoeditor…aibeauty | 33 | 71/76, 3 dòng tranh chấp | 2 | `plans/reports/audit-fanout-260913-1240-…` | ~15 phút | 30 phút | 15 phút |
| 14/09/2026 | com.nxl.aiphotocreator…texttoimage | 12 | 9/54, bản dev, dừng | 0 | `plans/reports/audit-fanout-260914-1143-…` | ~2 phút | 30 phút | 28 phút |
| 14/09/2026 | com.nxl.aiphotocreator…texttoimage | 14 | 54/54 | 0 | `plans/reports/audit-fanout-260914-1343-…` | ~3 phút | 30 phút | 27 phút |
| 14/09/2026 | aisong.generator.creatsong.music | 6 | 54/54, 3 ID không có trên sheet | 3 | `plans/reports/ad-audit-fanout-260914-1720-…` | ~15 phút | 30 phút | 15 phút |
| 21/09/2026 | com.hairai.hairstyletryon.haircolorchanger | 19 | Sạch | 0 | `plans/reports/audit-260921-1903-…` | ~3 phút | 30 phút | 27 phút |
| 21/09/2026 | com.nxl.aienglishtutor…aichatbot | 19 | Sạch | 0 | `plans/reports/ad-checklist-audit-260921-1007-…` | ~3 phút | 30 phút | 27 phút |
| 21/09/2026 | com.aivideogenerator…imagetoimage | 37 | Sạch | 0 | `plans/reports/ad-checklist-audit-260921-1932-…` | ~3 phút | 30 phút | 27 phút |
| 22/09/2026 | com.aienglishspeaking…aitutor | 6 | Sạch | 0 | `plans/reports/ad-checklist-audit-260922-1758-…` | ~3 phút | 30 phút | 27 phút |
| 23/09/2026 | com.nxl.aiphotocreator…texttoimage | 17 | 54/54 | 0 | `plans/reports/ad-checklist-audit-260923-1547-…` | ~3 phút | 30 phút | 27 phút |
| 10/10/2026 | com.hairai.hairstyletryon.haircolorchanger | 21 | 54/54, 5 ID ngoài checklist chờ ads team | 0 | [artifact](https://claude.ai/artifact/6ZFRdCkvAj9meWqyrqP2Wn) | ~3 phút | 30 phút | 27 phút |
| 22/10/2026 | ai.photogenerator.aivideo.aivideogenerator.aiart | 29 | 1 xác nhận, 1 tranh chấp, 0 chưa chốt | 1 | [artifact](https://claude.ai/artifact/JiwHbfA3WgYGGB5673aS4y) | ? | 30 phút | ? |
| 22/10/2026 | com.aihomedesign.aihomedecor.designidea.aiinterior | 9 | 0 xác nhận, 0 tranh chấp, 0 chưa chốt | 0 | [artifact](https://claude.ai/artifact/KjJD7WWUgUEpJ7GBR3Zjtd) | ? | 30 phút | ? |
| 22/10/2026 | com.aienglishspeaking.ailanguagetutor.aienglishlearning.aitutor | 6 | 0 xác nhận, 0 tranh chấp, 0 chưa chốt | 0 | [artifact](https://claude.ai/artifact/7EZWFPHFGPMevFt5KrrUXy) | ? | 30 phút | ? |
| 22/10/2026 | learnenglish.language.learningvocabulary.practice | 2 | 0 xác nhận, 0 tranh chấp, 0 chưa chốt | 0 | [artifact](https://claude.ai/artifact/LdVQX2zv8cTsMCwbHMKKMM) | ? | 30 phút | ? |
| 23/10/2026 | fitness.workout.aitraining.abs.exercises | 1 | 0 xác nhận, 0 tranh chấp, 0 chưa chốt | 0 | [artifact](https://claude.ai/artifact/XFC1UfgkBYBjYbwoDUfjxs) | ? | 30 phút | ? |
| 28/10/2026 | photoeditor.ai.generator.photovideo.image | 1 | 0 xác nhận, 0 tranh chấp, 1 chưa chốt | 0 | [artifact](https://claude.ai/artifact/PyaeK1CoEwfgjuiGRBkyXj) | ? | 30 phút | ? |

**Tổng:** 13 lần audit trên 9 app, test tay 390 phút, tool ~88 phút, tiết kiệm **~302 phút (~5 giờ)**.
6 lỗi checklist xác nhận. Chưa có ticket Jira.

# Audit checklist ads — lingospeak.english.learnlanguage.speak 2.0.0

- Run: `wf_dbfccb77-133` · mode `capture` · 2026-10-20
- Build: versionName `2.0.0` · version_code `10` · cài 2026-10-20 09:35 · audited_at `2026-10-20T03:26:42+00:00`
- Máy: Pixel 4 (99261FFAZ0077C)
- Sheet tab: gid `1547158364` (từ sheet, chưa có trong `apps.json`)
- Capture: `missed_home=[]`
  - new: Splash → inter → Language14/24 → Onboarding → Question → inter → Billing → Main
  - old: Splash → inter → Question → inter → Billing → Main
- `empty_filters`: `RemoteConfigRepository`, `inter_ads`
- `leftover_ids`: [] (không có ID runtime ngoài sheet)

## Thống kê

| Mục | Khớp / Tổng |
|---|---|
| 1. Thông số kỹ thuật | 8 / 8 |
| 2. ID ads FO | 40 / 40 |
| 4. ID ads resume | 6 / 6 |
| **Tổng** | **54 / 54** |

So với lượt 2026-09-30 (vc 8): 53/54 → 54/54. Dòng App ID lệch lượt trước giờ khớp.

Workflow: confirmed 0 · disputed 0 · unresolved 0 · clean.

## Kiểm khớp giả (dump cấu hình FO)

Grep từng ID sheet trong capture.log, tách dòng dump `FO_VslTemplate4FirstOpenSDK: …: [...]` khỏi dòng request (`FOR_TESTER_LOAD_AD`, `FOR_TESTER_SHOW_AD`, `TAG loadInterstitialAd`, `FO_loadInterstitial`).

| Độ mạnh bằng chứng | Số dòng | Dòng |
|---|---|---|
| App request thật | 33 | inter splash 102 (n/o, cả 3 tier), native splash 105, LFO1/LFO2, OB1–OB4 (trừ 303 thường), OB5 native 305, inter OB5 306, old OB1 native + inter high |
| Chỉ có trong cấu hình FO app in ra | 12 | 101 banner splash ×2, 106 native splash full screen ×3, 303-onb3 thường, resume 501/502/503 ×6 |
| Chỉ có trong APK | 1 | 301_onb1_o_inter (…6272988203) |

Không phải khớp giả kiểu learnenglish: `leftover_ids` rỗng, tức không vị trí nào request ID ngoài sheet. 13 dòng yếu là vị trí lượt này không chạm tới:
- splash chọn inter, không chọn banner/native full screen
- tier high fill nên tier thường không request (303, 301_o_inter)
- capture không chạy luồng resume

## Câu hỏi chưa giải quyết

- 13 dòng trên muốn chấm bằng request thật cần ép điều kiện: tắt inter splash qua RC để rơi xuống banner/native, ép high no-fill, và chạy background→resume.

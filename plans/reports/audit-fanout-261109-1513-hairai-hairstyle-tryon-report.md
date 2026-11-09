# Audit fan-out — com.hairai.hairstyletryon.haircolorchanger

- Run: wf_34166607-821 · mode: capture (capture mới do versionCode 19 → 23) · 2026-11-09 15:16 · v3.0.0 · tab gid=1210594131 · máy 99261FFAZ0077C
- New user: Splash → Language14 → Language24 → Onboarding → KHÔNG tới Home (runner hết cách thử). Old user: Splash → Language14 → Language24 → Onboarding → Question → Home.
- Cả hai luồng không có AdActivity (không thấy inter splash full màn).

## Kết quả
- 54/54 khớp. confirmed 0 · disputed 0 · unresolved 0 · clean.
- App ID sheet ca-app-pub-4584260126367940~2278375981 khớp (không có App ID nào trong log, runner chấm qua APK).

## leftover_ids — 6 (build load, sheet không khai)
- Sheet mục "3. ID ads inapp" trống.
- Cả 6 có dòng FOR_TESTER_LOAD_AD "starting load ad" thật lúc 15:16:15–17.
- Interstitial: 4031770345, 4087610665, 5186081670 (mới so với lượt 2026-09-21), 6466361999. Native: 2910260367, 6136841893.

## Cảnh báo
- missed_home=['new']: luồng new user không tới Home. 54/54 vẫn khớp nhờ lượt old; ID chỉ load ở Home của new user (nếu có) có thể bị sót.

## Câu hỏi chưa giải quyết
- Danh sách in-app chính thức để điền mục 3.
- Vì sao new user kẹt ở Onboarding (flow runner hay app) — chưa xem.

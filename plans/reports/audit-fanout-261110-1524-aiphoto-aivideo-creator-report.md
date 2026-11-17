# Audit fan-out — com.ai.aiphoto.aivideo.creator.generator

- Run: wf_831ee8bf-df4 · mode: capture · 2026-11-10 · versionCode 6 · tab gid=1171872315 (từ sheet, chưa có trong apps.json)
- Cả luồng new và old đều tới Home (missed_home=[]). apk_scan_applicable=true.

## Kết quả
- 53/54 khớp (Thông số 8/8, FO 40/40, Resume 5/6). confirmed 0 · disputed 1 · unresolved 0.

## Disputed — 502_native (4. ID ads resume)
- Sheet: ca-app-pub-4973559944609228/2199612256. Không có trong build_ad_ids (71 ID) của APK.
- capture.log 11773-11774 (pid 24664) và 16744-16745 (pid 26115), tag FO_VslTemplate4FirstOpenSDK: "AppResume native high" và "AppResume native :" đều là 8349253480 (= 502_native_high trên sheet).
- Tool gắn nhãn "checklist-sai"; bước phản biện bác nhãn đó: theo luật checklist là chuẩn, khả năng cao là build gán normal = high. Cần ads-team/dev xác nhận.
- empty_filters=['RemoteConfigRepository']: không loại trừ được RC ghi đè lúc chạy.

## leftover_ids — 4 (build load, sheet không khai)
- 4973559944609228/5003074841, /5135111792, /5537602329, /6448193469.

## Tool gap
- Phân loại "không có trong build" thẳng sang checklist-sai, chưa đối chiếu log runtime: khi log in ID của placement trùng ID placement anh em (normal == high) thì nên xếp "build sai ID".

## Câu hỏi chưa giải quyết
- ID 502_native đúng là 2199612256 hay 8349253480?
- 4 leftover ID thuộc placement nào (inapp)?

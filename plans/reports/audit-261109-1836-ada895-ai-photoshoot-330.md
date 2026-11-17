# Audit ID ads · ADA895 AI Photoshoot 3.3.0 (25) · aiphotogenerator.photoshoot.aiart.aiimagegenerator

- Máy: Pixel 4 `99261FFAZ0077C`, chế độ capture (`pm clear` + new user đi hết FO tới Home, rồi old user mở lại tới Home).
- Lệnh: `audit_runner.py --package <pkg> --capture --serial 99261FFAZ0077C --force` (không chạy Workflow tool: phiên agent không có tool này; triage rỗng nên không có dòng nào cần judge).
- Kết quả: **54/54 khớp**, 0 lệch, 0 dev-build signal, 9 ID ngoài sheet (mới).

## Ghi chú đọc kết quả
- ID có request thật trong capture: 102 n/o inter (high/high1/normal), 201/202/301/302/303/304 native (high + normal), 305 native, 306 inter high, 301_o native high, 301_o inter high.
- ID chỉ thấy trong dump cấu hình FO (`FO_VslTemplate4FirstOpenSDK`) + có trong APK, không có request trong lượt capture: 101 banner splash, 105 native splash, 106 native splash old, các tầng high1/high2 của 201/202/301/303 (tầng dự phòng 2FLOOR), 501/502/503 resume (capture không ẩn-mở app). 301_o native / 301_o inter normal và 306 inter normal chỉ có trong APK / dòng cấu hình `loadInterstitialAd` (tầng sau không cần vì high fill hoặc chưa tới lượt).
- 9 ID ngoài sheet: toàn bộ request ở MainActivity (Home, in-app): inter 4525873527, 2861319864, 4174401535, 3354704499, 6116599208; banner 1101129256, 7946243787; native 2885488792, 7307949536. Ngoài phạm vi checklist FO.

## Unresolved
- Không.

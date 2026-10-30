# Audit fan-out: photoeditor.ai.generator.photovideo.image (vc1)

- Run: `wf_57c0c0b8-1a0` · mode: capture (`pm clear`, chạy lại cả luồng new và old)
- Checklist: tab gid=268751493 (lấy từ sheet, chưa có trong `apps.json`)
- Ngày: 2026-10-28

## Kết quả
| Section | Khớp |
|---|---|
| 1. Thông số kỹ thuật | 4/4 |
| Facebook Client Token | 1/1 |
| 2. ID ads FO | 40/40 |
| 4. ID ads resume | 6/6 |
| **Tổng** | **51/51** |

- Triage: không còn dòng nào chưa kết luận, nên workflow không gọi agent điều tra. confirmed 0 · disputed 0 · unresolved 0 → workflow trả về **clean**
- Delta: đây là lượt đầu (51 dòng mới thêm), không có dòng hỏng hay dòng được sửa. Có 5 ID mới không nằm trong sheet (`new_leftover_ids`)
- Capture: cả hai luồng new và old đều tới `AiPhotoVideoMainActivity`, `missed_home` rỗng. `dev_build_signals` = 0

## Quan sát thêm (đọc capture log tay, ngoài workflow)
Workflow ghi clean, nhưng 5 ID ngoài sheet là ID mà inter splash dùng thật lúc chạy:

- Luồng new: `loadInterstitialAd` với `ca-app-pub-4973559944609228/8784891502` (dự phòng: `/1492724849`, `/8792630363`) → load thành công → `FOR_TESTER_SHOW_AD: INTERSTITIAL - …/8784891502` → có `paid_ad_impression` (capture.log:4602, 5329, 6462, 6680)
- Luồng old: `…/6158728160` (dự phòng: `/7479548695`) → hiện (capture.log:45295, 47751)
- Các ID `102-spl-n-inter*` / `102-spl-o-inter*` trong sheet (publisher `4584260126367940`) chỉ xuất hiện trong dòng config `FO_VslTemplate4FirstOpenSDK: Inter splash: [...]` (capture.log:40413, 57183). Không thấy `starting load` cho các ID này. Vì tool chỉ cần ID có mặt trong bản cài nên chúng vẫn được tính là khớp
- Mọi ad khác hiện ra trong lượt chạy đều thuộc publisher `4584260126367940` và có trong sheet: native 105/201/202/301–305, inter 306 onb5 và inter 301 onb1 old
- `adunit_exposure` còn ghi 2 ID nữa của publisher `4973559944609228` trong AdActivity: `/6700186003` và `/1779031819` (capture.log:11360, 52211). Cả hai trùng thời điểm với inter splash, nhiều khả năng là ID nội bộ của mediation chứ không phải ad unit riêng
- Ban đầu ghi là unresolved (1). Người dùng chốt quy tắc "checklist là chuẩn, build điền thừa là sai", nên chuyển sang **lệch (confirmed)**

## Ô trống trong sheet mà build có giá trị (đọc manifest APK bằng aapt2)
Parser bỏ qua dòng sheet có giá trị trống, nên tool không kiểm 3 dòng này:

| Dòng sheet | Sheet | Build |
|---|---|---|
| Facebook App ID | trống | `3292610564230452` (`com.facebook.sdk.ApplicationId` → `string/facebook_app_id`) |
| Facebook Client Token | trống | `7e2c…2358 (đã che)` (`com.facebook.sdk.ClientToken` → `string/facebook_token_id`) |
| App ID | trống | `ca-app-pub-4584260126367940~3637357986` (`com.google.android.gms.ads.APPLICATION_ID`) |

Theo quy tắc "checklist là chuẩn", cả 3 dòng đều tính là lệch.

## Kết luận sau khi áp quy tắc
confirmed 5 (3 ô trống + 2 ID inter splash đang hiện) · disputed 0 · unresolved 0

## Ghi chú
- Tool chỉ đối chiếu chiều sheet → build. 51/51 khớp nghĩa là "ID có trong bản cài", chưa chắc là "placement đang load đúng ID"
- `build_ad_ids` có 12 ID test của Google hoặc ID giữ chỗ (`ca-app-pub-3940256099942544/*`, `ca-app-pub-0000000000000000~0000000000`). Nhiều khả năng đây là hằng số SDK

## Câu hỏi chưa giải quyết
- Bảng điểm trên artifact vẫn ghi 51/51 vì tool không đếm dòng sheet trống và ID ngoài sheet. Muốn bảng điểm tự đếm các chỗ này thì phải sửa tool (`checklist_source.parse_checklist_csv`, `apk_verifier`)

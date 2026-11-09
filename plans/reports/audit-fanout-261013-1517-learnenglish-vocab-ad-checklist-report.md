# Audit checklist ads — learnenglish.language.learningvocabulary.practice

- Run: `wf_20d8ac0a-7cb` · mode `capture` · 2026-10-13
- Build: version_code `2` · audited_at `2026-10-13T08:15:14+00:00`
- Sheet tab: gid `1919567600` (từ sheet, chưa có trong `apps.json`)
- Capture: `missed_home=[]` (tới Home, MainActivity 15:14:12 và 15:15:07), `apk_scan_applicable=true`
- `empty_filters`: `RemoteConfigRepository`, `inter_ads`

## Thống kê

| Mục | Khớp / Tổng |
|---|---|
| 1. Thông số kỹ thuật | 8 / 8 |
| 2. ID ads FO | 0 / 40 |
| 3. ID ads inapp | 2 / 2 |
| 4. ID ads resume | 0 / 6 |
| **Tổng** | **10 / 56** |

`extra` 79 · `leftover_ids` 4: `…/6158728160`, `…/7479548695`, `…/8784891502`, `…/8792630363`.

## Kết quả điều tra

### confirmed (0)

### disputed (1): 5 dòng inter splash 102-spl-*

Sheet: `2572755573`, `7633510569`, `5711332497` (new), `8890751911`, `1068102219` (old).

Runtime, do chính process app ghi:
- New user (PID 5102: Splash → Language → Onboarding → Question → Main): `capture.log:1125` `loadInterstitialAd: …/8784891502 - …/8792630363`; `capture.log:1977` `FOR_TESTER_SHOW_AD: INTERSTITIAL - …/8784891502`.
- Old user (PID 6527: Splash → Question): `capture.log:15510` `loadInterstitialAd: …/6158728160 - …/7479548695`; `capture.log:16050` show `…/6158728160`.

Agent điều tra gắn nhãn `checklist-sai`, bước phản biện bác nhãn đó. Lý do: `apk_strings` báo KHÔNG cho cả ID của sheet lẫn ID đang chạy, tức ID được RC/server cấp lúc chạy. Bên sai có thể là sheet hoặc giá trị RC (hoặc nhánh A/B). Log RC rỗng (`empty_filters`) nên không phân xử được. `-high1` chưa kiểm được vì `loadInterstitialAdDoubleIds` chỉ in 2 ID.
Nhãn đúng: **lệch runtime và sheet, chưa rõ bên sai, cần đối chiếu RC**. Cần người xem lại.

### unresolved (1): 41 dòng còn lại của FO (35) + resume (6)

Không kết luận được. Cấu hình FO app in lúc chạy có đủ ô nhưng ID rỗng:
`FO_VslTemplate4FirstOpenSDK: Banner splash: [, ]`, `Native splash: [, ]`, `LFO1: [, , , ]`, `LFO2: [, , , ]`, `OB1: [, , , ]`, `OB2: [, ]`, `OB3: [, , , ]`, `OB4: [, ]`, `AppResume aoa high: `, `AppResume inter: `.
Native request với ID rỗng: `FOR_TESTER_LOAD_AD: Native ad:Ad with id(OnlyId(adUnitId=)) has load error ... Is your ad unit id correct?` (32 lần). Placement có trong build (`PRELOAD_KEY_NATIVE_LFO1` trong classes4.dex), nên không phải build thiếu; cũng không có ID runtime nào để nói sheet sai.
Cần lượt capture mà RC trả ID. 6 dòng resume còn cần luồng background→resume trong tutorial (resume chỉ có ở luồng tutorial). Lượt này chưa chạy luồng đó.

## Lỗ tool phát hiện được

- Phép kiểm "có trong APK không" vô hiệu với app nhận ID FO qua RC: chính ID runtime (`8784891502`, `6158728160`) cũng vắng APK. `build_ad_ids` chỉ có 2 ID production (reward chat) và ID test. `apk_scan_applicable` vẫn `true`; nên tắt theo vị trí khi ID runtime cũng vắng APK.
- Filter `RemoteConfigRepository`/`inter_ads` không bắt dòng nào trên build này, nên không đối chiếu được sheet với giá trị RC.
- Capture không chạy luồng resume trong tutorial, nên 6 dòng mục 4 không bao giờ được kiểm.

## Lưu ý đọc kết quả

Tool chỉ đối chiếu chiều sheet → build. 46 dòng lệch là do lượt này không nhận được ID FO/resume nào từ RC, không phải 46 dòng sheet sai.

## Câu hỏi chưa giải quyết

- RC của bản version_code 2 có đang publish ID FO/resume không, hay để trống thật?
- ID inter splash đúng là ID của sheet hay `8784891502`/`6158728160`?

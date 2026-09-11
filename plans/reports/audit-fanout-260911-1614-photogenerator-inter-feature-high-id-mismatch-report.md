# Audit fan-out — ai.photogenerator.aivideo.aivideogenerator.aiart

Run: `wf_8f6c22cc-5a6` (ad-checklist-audit-fanout) · 2026-09-11 15:58–16:11 · 2 agents, 0 lỗi

## Kết quả

Deterministic pass settle hết, chỉ 1 dòng đẩy lên agent. Delta so lần trước: **không đổi** (`changed:false`).

| Dòng | Verdict | Verify |
|---|---|---|
| `inter_feature_high` (§3 ID ads inapp, Home) | sheet ≠ build | holds=true |

**0 disputed.**

## Finding: `inter_feature_high` — ID trong sheet không tồn tại trong build

- Sheet ghi: `ca-app-pub-4973559944609228/4070123043`
- Build thực dùng: `ca-app-pub-4973559944609228/2733004612`

### Bằng chứng

APK `ai.photogenerator...-24.apk`, quét toàn bộ 3502 zip entry:
- `4070123043` → **0 hit** (không có ở bất kỳ dex/arsc/entry nào)
- `2733004612`, `4098057173`, `9894079845`, `2486421558` → có trong `classes.dex`
- String table dex lưu ad ID sắp xếp tăng dần; dump lân cận cho `.../3910779284, .../4098057173, .../4112509166` — đúng chỗ `4070123043` phải nằm và trống ⇒ không phải lỗi quét/nén/obfuscate

Log `...-capture.log`:
- L12958 `inter_ads: canRequestAd: key=...2733004612_...4098057173` — nửa normal `4098057173` khớp đúng dòng sheet `inter_feature` ⇒ nửa high build dùng là `2733004612`
- L12966-12968 `loadDoubleIds: canShowHigh=true (key=enable_401_home_a_inter_high), canShowNormal=true (key=show_inter_feature)` → `FOR_TESTER_LOAD_AD: Interstitial ad:Ad with id (.../2733004612) starting load`
- L13509, L19979 `loadDoubleIds: highPriorityAd=NULL for id=.../2733004612` ⇒ runtime gọi thẳng `2733004612` là nửa **HIGH** — không phải suy diễn từ thứ tự trong key
- `grep -c 4070123043` = 0 · `2733004612` = 15 · `4098057173` = 15
- Snapshot `leftover_ids` có `.../2733004612` (ID build không khớp dòng nào trong sheet)

Control group xác nhận quy ước: log chỉ có 2 cặp double-id; cặp `9894079845_5704057970` khớp **chính xác** 2 dòng sheet `inter_style_high`/`inter_style` ⇒ quy ước `key=<high>_<normal>` và logic đối chiếu đúng.

### Giả thuyết thay thế đã loại

1. **build-thiếu** — bác bỏ: dex có `show_inter_feature` + đủ bộ `show_inter_style_high`, `show_inter_uninstall_high`, `show_native_loading_high`, `show_inter_nav_high`
2. **chưa capture đúng màn** — bác bỏ: L12954 `AIP922AIPhotoVideoMakerMainActivity`, `track_ad_request adunitid=2733004612` với `ga_screen_class=AIP922...MainActivity`
3. **A/B variant B chứa ID sheet** — bác bỏ: dex chỉ có duy nhất `enable_401_home_a_inter_high`, không có nhánh `_b_`
4. **ID nạp từ remote config** — không cứu được: runtime thực tế vẫn load `2733004612`
5. **`2733004612` thuộc placement khác** — bác bỏ: cả 15 occurrence đều cặp với `4098057173` trên màn Home

### Ghi chú

- Build dùng cờ A/B `enable_401_home_a_inter_high` thay vì `show_inter_feature_high` — giải thích tên cờ lệch quy ước, không ảnh hưởng kết luận ID
- 2 leftover còn lại (`2836629167`, `4149710834`) là banner, không liên quan
- **Phát biểu nên dùng:** "ID sheet không tồn tại trong build, build dùng `2733004612`, cần ads-team xác nhận ID đúng" — bằng chứng chứng minh sheet và build **lệch nhau**, tự nó không quyết định bên nào sai (nếu sheet là spec ads-team cấp thì có thể dev build nhầm ID)

## Unresolved

- `4070123043` có tồn tại trong AdMob account `4973559944609228` không, gắn placement nào — chỉ tra được qua AdMob console
- Bên nào sai: sheet hay build — cần ads-team xác nhận

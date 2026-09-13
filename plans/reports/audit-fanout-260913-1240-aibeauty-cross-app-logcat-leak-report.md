# Audit fan-out — Lynix / aibeauty (com.aiphotoeditor.aiphotogenerator.aivideogenerator.aibeauty)

Run `wf_9c9964c4-b36` · mode `capture --force` · versionCode 33 · 2026-09-13

## Kết quả

**71/76 khớp**, 5 lệch.

| Mục | Khớp |
|---|---|
| 1. Thông số kỹ thuật | 8/8 |
| 2. ID ads FO | 36/38 |
| 3. ID ads inapp | 21/24 |
| 4. ID ads resume | 6/6 |

Nhóm: `confirmed` 2 · `disputed` 3 · `unresolved` 0.

## Confirmed

- **Home `inter_feature_high`** — sheet ghi `3076727342`, không có trong APK. Build dùng `1744932982` (`classes3.dex`, log 18534 load thành công). Cặp key `1744932982_1763645679`; nửa normal khớp dòng sheet `inter_feature`. Placement có (`CÓ inter_feature`). Lệch ID.
- **`inter_result`** (twin normal của Result) — ID `3169954399` vắng APK **và** tên placement cũng vắng (`KHÔNG inter_result`, `KHÔNG show_inter_result`). Thiếu placement, không phải sai ID.

## Disputed

- **`306_onb4_n_inter_high` + `306_onb4_n_inter`** — nhãn "build thiếu" sai. Placement có, khác tên: `CÓ 306_onb5_n_inter_high`, `CÓ 306_onb5_n_inter` (`classes5.dex`). Kết luận gốc chỉ thử một cách viết tên.
- **`inter_result_high`** — phản biện lật nó **cũng không đứng**. Nó dựa trên `4112509166`, `6032095499`, `9696617141` như "ID chạy thật mà vắng APK" để nói `build_ad_ids` thiếu. Ba ID đó của AI Art, lọt vào log do logcat không lọc package.

## Lỗi tool phát hiện trong lượt này

`adb logcat` bắt toàn máy; app vừa audit không bị dừng trước khi capture app kế. Log aibeauty chứa dòng của aiart (PID 16880) từ 11:31 tới 11:33:30, lượt aibeauty bắt đầu 11:31:15.

Hậu quả đã xảy ra: một phản biện kết luận sai. Rủi ro chưa xảy ra: ID app anh em lọt vào có thể làm một dòng được chấm Khớp nhầm.

Sửa: force-stop app trước khi bắt đầu capture app sau.

## Ghi chú

- Lượt đầu sau khi sửa cách bấm logo splash: `FOR_TESTER` 78 → 320 dòng. Nhóm "chưa thấy trong log" về 0.
- `missed_home = ['old']`; `empty_filters = ['RemoteConfigRepository']` dù APK có chuỗi đó.
- 6 leftover ID; 1 đã giải thích, 5 chưa tra.

## Chưa giải quyết

- Slot 306: sheet `onb4` vs build `onb5` — gõ nhầm hay hai placement khác nhau? Cần ads-team.
- `inter_result_high` thiếu thật hay không — phản biện bị bác chỉ khôi phục nhãn, chưa chứng minh lại.
- Bên nào sai, sheet hay build.

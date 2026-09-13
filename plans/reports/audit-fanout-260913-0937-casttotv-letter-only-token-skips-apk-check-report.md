# Audit fan-out — Cast to TV (com.remote.casttotv.screenmirroring)

Run `wf_cc775c54-b84` · mode `capture` · versionCode 11 · 2026-09-13

## Kết quả

**57/58 khớp.** Một dòng chưa kết luận được bằng máy: `Adjust config event name purchase` = `phinvw`.

| Mục | Khớp |
|---|---|
| 1. Thông số kỹ thuật | 7/8 |
| 2. ID ads FO | 40/40 |
| 3. ID ads inapp | 4/4 |
| 4. ID ads resume | 6/6 |

Nhóm kết quả: `confirmed` 0 · **`disputed` 1** · `unresolved` 0 · `clean` không.

## Dòng disputed

Judge chấm `chua-capture-du`. Verify lật, và tôi kiểm lại — verify đúng.

Dòng này **không phải sheet lệch build**. Nó bị bỏ lại vì bộ lọc của tool.

Bằng chứng:

- `apk_strings.py --package com.remote.casttotv.screenmirroring phinvw` → `CÓ phinvw (classes6.dex)`. Giá trị sheet ghi có trong bản cài.
- `apk_verifier.py:88-91` `is_token_like()` đòi value có **cả chữ cả số** (hoặc ≥12 chữ số). Chạy thật: `phinvw` → False; `x797e0` → True; `q5dxlw86qbcw` → True.
- `apk_verifier.py:112` chỉ đưa dòng token-like vào lượt quét APK ⇒ `phinvw` chưa từng được hỏi tới APK.
- Snapshot xác nhận hai chuẩn chấm: `q5dxlw86qbcw` và `x797e0` mang note "Xác nhận từ APK"; `phinvw` mang note thuần log.
- Control: `x797e0` bắn thật lúc chạy (5 dòng `AdSdkAdjust: Event success data`) nhưng grep trong 26.412 dòng log = **0**. Tầng log không in event token ⇒ capture thêm luồng mua cũng vô ích.

Khác biệt duy nhất giữa ba dòng Adjust cùng mục: có chữ số hay không.

## Cần quyết

1. **Sửa `is_token_like()` thế nào** — thuộc chủ tool. Nới cho token toàn chữ ≥6 sẽ kéo `production` (dòng `Adjust config environment`) thành "xác nhận từ APK", đúng false positive mà docstring hàm cảnh báo. Hướng an toàn hơn: bỏ heuristic có-chữ-số, kiểm tra biên literal trong dex qua tiền tố độ dài ULEB128. Chưa làm, chờ quyết.
2. **Sheet có hai tab cùng khai package này** — gid `1504229618` (registry đang ghim) và `2107085721`. Nếu tab kia mới hơn thì mọi lượt audit app này đang so với checklist sai. Cần ads-team xác nhận.

## Ghi chú lượt chạy

- Chế độ `capture` nhưng runner báo "build chưa đổi" (versionCode 11) → dùng lại log + triage của lượt capture `2026-09-13T02:28Z`, không lái máy lại. Đúng thiết kế.
- `empty_filters` = `FOR_TESTER`, `RemoteConfigRepository` — hai vùng log rỗng. Mọi suy luận "log không có ⇒ sai" vô giá trị với app này. `missed_home` rỗng.
- Note tự sinh "Log không in nó ra" ở dòng `Adjust config token` nói sai: `q5dxlw86qbcw` có 6 lần trong log dưới dạng `app_token`. Không đổi kết luận.

## Chưa giải quyết

- `phinvw` có được nối đúng vào AdjustEvent lúc mua không — APK chỉ chứng minh chuỗi nằm trong build. Phải decompile `classes6.dex` tìm call site.
- Hai câu ở mục "Cần quyết" ở trên.

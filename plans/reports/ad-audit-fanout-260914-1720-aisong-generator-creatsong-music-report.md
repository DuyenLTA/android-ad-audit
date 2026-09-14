# Ad checklist audit — aisong.generator.creatsong.music

- Ngày: 2026-09-14 (audited_at `2026-09-14T10:14:41Z`)
- Chế độ: `capture` (lái máy thật, `pm clear` + thu logcat)
- Run ID: `wf_a4e3ca2d-394`
- version_code: 6 (triage == snapshot, không phán trên ảnh cũ)
- gid sheet: 1748014371 (đọc từ sheet, chưa có trong `apps.json`)

## Thống kê

| Mục | Số |
|---|---|
| Dòng checklist khớp | **54 / 54** |
| Dòng lệch | **0** |
| — 1. Thông số kỹ thuật | 8/8 khớp |
| — 2. ID ads FO | 40/40 khớp |
| — 4. ID ads resume | 6/6 khớp |
| ID chạy trong build nhưng sheet không có dòng nào | **3** |

Cả 4 rổ triage đều rỗng. `missed_home: []` — không luồng nào kẹt trước Home, lượt capture đi tới đủ.

## Điều tra: 3 ad unit ID ngoài checklist (confirmed)

Đã qua phản biện, luận điểm đứng.

| ID | Loại / màn |
|---|---|
| `ca-app-pub-4973559944609228/6006731028` | Banner — MainActivity |
| `ca-app-pub-4973559944609228/7923437602` | Banner — MainActivity |
| `ca-app-pub-4973559944609228/7591275435` | Interstitial — MainActivity |

**Nguyên nhân chung: sheet thiếu hẳn section màn Home/Main.** Snapshot chỉ có 3 section — "1. Thông số kỹ thuật", "2. ID ads FO", "4. ID ads resume" — hụt số 3. Prefix các dòng chạy 101/102/105/106 (splash), 201/202 (lfo), 301–306 (onboarding), 501–503 (resume); không dòng nào cho main/home.

Bằng chứng:

- **Có trong bản cài:** cả 3 nằm trong `build_ad_ids`; `apk_strings.py` xác nhận cả 3 có trong `classes.dex`.
- **Đúng publisher của app:** `4973559944609228` khớp App ID trong sheet (`ca-app-pub-4973559944609228~1585158338`) — không phải ID app anh em.
- **Chạy thật lúc runtime** (dòng `FOR_TESTER_*`, đúng pid của app — `capture.log:190` "Start proc 11579:aisong.generator.creatsong.music", `capture.log:21716` "Start proc 14326:…"):
  - `capture.log:19875` LOAD banner `…/6006731028` + `:20333` `FOR_TESTER_SHOW_AD: BANNER - …/6006731028`
  - `capture.log:19078` LOAD inter `…/7591275435` + `:20163` "has loaded successfully"
  - `capture.log:19076`, `:30684` LOAD banner `…/7923437602` + `:32185` "has loaded with result: Loaded(…7923437602…)"
- **Phản đề đã thử:** không dòng sheet nào mang 3 ID này ở `value` hay `alt_values` → không quy được về dòng twin đã khớp.
- **Độc lập thêm:** `apk_strings.py` thấy chuỗi `inter_main` trong APK (`classes.dex`, `classes4.dex`, `resources.arsc`) trong khi sheet không liệt kê placement main nào.

Không dùng dòng FA-SVC làm bằng chứng (log có lô lạ: `app_id: com.ss.android.ugc.trill`, `app_id: 1788380451687318`).

**Bằng chứng chỉ chứng minh sheet và bản cài lệch nhau** — cần ads-team xác nhận section màn Main bị thiếu trên sheet, chứ chưa tự nó nói bên nào sai.

## Cảnh báo lượt chạy

`empty_filters: ["RemoteConfigRepository", "inter_ads"]` — hai vùng log rỗng hoàn toàn (`grep -c` = 0 cả hai; `FOR_TESTER` vẫn 153 dòng nên capture có dữ liệu).

Hệ quả: mọi lập luận kiểu "log im lặng nên không có" ở hai vùng này vô giá trị lượt này. Thực tế **không chặn kết luận nào**: kết luận trên dựa vào *sự có mặt* trong APK + `FOR_TESTER_*`, không dựa vào im lặng; và section "1. Thông số kỹ thuật" chỉ gồm Adjust token/env/event, Facebook App ID/Client Token, package, App ID — tất cả verify qua APK, không có dòng cờ remote-config nào.

Lưu ý: `RemoteConfigRepository` rỗng nghĩa là lượt này không đối chiếu được giá trị remote config. App này cả 3 ID đều nằm trong APK nên phép kiểm "có trong APK" còn hiệu lực (`apk_scan_applicable: true`, `dev_build_signals: []`).

## Khoảng trống của tool

1. **Không có phép kiểm chiều ngược (build/log → sheet).** Tool chỉ diff từng dòng sheet xuống build/log; ID app thật sự chạy mà sheet không liệt kê bị đổ vào `result.leftover_ids` trần trụi, không đi qua triage. Bằng chứng: `leftover_ids` có 3 ID nhưng cả 4 rổ triage đều rỗng → tool báo "sạch" trong khi nguyên một màn chạy quảng cáo ngoài tầm checklist.
2. **Chưa gán màn cho `leftover_ids`.** Log đã có `ga_screen_class` cho từng ID (cả 3 leftover đều `MainActivity` — `capture.log:19141`, `:19886`, `:30743`). Đọc trường này là tool tự kết luận được, khỏi bắt người kiểm suy ra.
3. **Chưa kiểm độ phủ section của sheet.** Section đánh số 1, 2, 4 — hụt 3. Một check "số section có liên tục không" sẽ tự cảnh báo đúng loại lỗi này.
4. **Cảnh báo `empty_filters` không hạ độ tin dòng nào phụ thuộc vào vùng log rỗng.** Lượt này may không ảnh hưởng, nhưng tool nên gắn cờ.

## Câu hỏi chưa giải quyết

- Sheet có thật sự thiếu section 3 (màn Main), hay parser làm rơi? Agent chỉ đọc được snapshot đã parse, không đọc được sheet sống. Parser xử section 4 bình thường, không dấu hiệu bị rơi — nhưng cần ads-team mở sheet xác nhận.
- 3 ID màn Main là placement hợp lệ chưa kịp đưa vào checklist, hay ID sót lại từ bản cũ? Cần ads-team trả lời.
- Vì sao `RemoteConfigRepository` và `inter_ads` rỗng hoàn toàn lượt này — app đổi tag log, hay luồng capture không chạm tới?

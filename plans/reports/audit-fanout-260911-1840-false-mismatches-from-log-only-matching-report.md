# Dòng đúng bị báo lệch — vì đối chiếu chỉ dựa vào log

App `ai.photogenerator.aivideo.aivideogenerator.aiart`, build 24, 2026-09-11.

## Triệu chứng

Hai lượt capture cùng build, cách nhau 2 tiếng, ra hai điểm khác nhau:

| Lượt | Điểm | Dòng chưa kết luận |
|---|---|---|
| 15:27 | 71/72 | 1 |
| 18:00 | 66/72 | 6 |

App không đổi. 5 dòng chênh đều ở mục 1: Adjust token, 2 event token, Facebook
App ID, Client Token. Không dòng nào hỏng.

## Nguyên nhân, theo thứ tự phát hiện

**1. Tag mang token không nằm trong filter.** Adjust app token đi qua
`AdSdkAdjust`; filter chỉ có `setupAdjust`, mà tag đó chỉ in environment.
6 dòng `AdSdkAdjust` bị bỏ qua hoàn toàn.

**2. Lưới an toàn thủng.** `empty_filters` báo rỗng dù tester dump không bật,
vì `FOR_TESTER` khớp đúng một dòng:

```
1669: I config_for_tester: Firebase token: e5kk-NuKQ...
```

Firebase, chữ thường, không liên quan. Lọt vì `log_extractor.py` so khớp không
phân biệt hoa thường. Một dòng rác làm cảnh báo im lặng và 5 dòng bị trừ oan.

**3. APK không cứu được.** `verify_apk_rows` chỉ xử giá trị hình dạng App ID
hoặc ad unit ID. Token Adjust, FB App ID là chuỗi thường nên bị bỏ qua — dù cả
5 nằm sẵn trong `classes.dex` / `resources.arsc`.

**4. Package name bị gác sai cờ.** `verify_package_rows` chỉ cần `adb`, nhưng
`audit_runner` bật nó theo `capture_log is not None`. Lượt APK-only vẫn cắm máy
(đọc `versionCode` từ `dumpsys`, pull APK qua `adb`), nên phép hỏi luôn dùng
được — mà dòng Package name vẫn bị báo lệch ở mọi lượt APK-only.

**5. `apk_strings.py` nuốt chuỗi đầu tiên.** `package` là positional nên
`--apk X a b c` ăn mất `a`, im lặng. Đúng loại lỗi sinh ra kết luận "không có
trong build" sai.

## Đã sửa

- Thêm `AdSdkAdjust` vào `DEFAULT_FILTERS`
- Khớp filter phân biệt hoa thường — đây là tag log, không phải free text
- Verify-từ-APK cho mọi token đặc trưng, chốt bằng `is_token_like`: có cả chữ
  lẫn số, hoặc dãy số dài. `production` bị loại có chủ đích — APK nào cũng chứa
  nó, cho qua là cho qua một dòng không ai kiểm
- `use_device=True` ở mọi lượt của `audit_runner`
- Dòng chỉ log mới trả lời được, trong lượt không có log: ghi rõ "chưa kiểm
  được", không để nguyên ghi chú nghe như đã tìm và thấy lệch
- `apk_strings.py`: `--package` / `--apk` đều là cờ

## Kết quả

| Chế độ | Trước | Sau |
|---|---|---|
| APK-only | 64/72 | **70/72** |
| Capture | 71/72 | **71/72** |

Lượt capture chốt: `missed_home: []`, `build_ad_ids: 78`,
`empty_filters: ['FOR_TESTER']` — cảnh báo bật đúng (tester dump thật sự không
lên), nhưng điểm không bị trừ oan vì 5 token đã được APK xác nhận. Đúng hành vi
mong muốn: nói ra chỗ capture thiếu mà không đổ lỗi cho app.

Hai dòng còn lại ở chế độ APK-only là đúng bản chất: `inter_feature_high` (lệch
thật) và `production` (không nguồn nào trong chế độ đó trả lời được).

## Một regression tự gây, bắt được nhờ chạy trên dữ liệu thật

Ghi chú "không có log" ban đầu đè mất kết luận đúng của `inter_feature_high` —
dòng mà APK đã chứng minh ID vắng mặt. Dòng placement giữ ID thật ở
`alt_values`, không ở `value`, nên guard chỉ nhìn `value` đã bỏ sót. Thêm
`has_ad_id_candidate()` và test khoá lại. Test suite không phát hiện; chạy thật
mới lộ.

## Đo tốc độ lớp agent

| Lượt | Dòng phán | Thời gian | Mỗi dòng |
|---|---|---|---|
| `wf_8f6c22cc-5a6` | 1 | 13m 00s | 780s |
| `wf_3e37692f-ce4` | 1 | ~7m | ~420s |
| `wf_a06b3a0e-746` | 6 | 6m 04s | **61s** |

Nguyên nhân: judge không còn tự mở APK quét. `build_ad_ids` nằm sẵn trong
triage, `apk_strings.py` trả lời mọi chuỗi khác trong 0,6s.

Cổng verify cũng hoạt động: 5/6 finding là `khong-ket-luan-duoc`, không có luận
điểm để phản biện nên không mở agent. Không có cổng thì 7 agent thay vì 2.

## Verify bắt được judge trượt

Judge gán `checklist-sai` và viết "Sheet nên sửa 4070123043 → 2733004612".
Verify trả `holds=false`: dữ kiện vững, **quy kết thì không**. APK và log chỉ
chứng minh hai bên lệch nhau, không phân biệt được "sheet ghi sai" với "dev
wire nhầm". Verify còn chỉ ra judge dùng ngược chiều một bằng chứng:
`inter_feature_high` là tên placement `_high` duy nhất không có trong dex,
trong khi mọi anh em của nó đều có — điều đó nghiêng về "build khác spec" ít
nhất ngang với "sheet cũ".

## Chưa giải quyết

- `4070123043` có trong AdMob account `4973559944609228` không, gắn placement
  nào — chỉ tra được qua AdMob console
- `2733004612` đã được ads-team duyệt chưa
- Vì sao tester dump lên ở lượt 15:27 mà không lên ở các lượt sau, dù driver
  vẫn spam logo splash và vẫn tới Home
- Luồng không tới được Home vẫn đốt trọn 300s timeout; chưa phân biệt được
  "đang chờ countdown" với "đã kẹt"

# Audit checklist ads — com.nxl.aiphotocreator.aivideogenerator.texttoimage

- **Run:** `wf_16979ee6-9d9` · **Chế độ:** capture (máy thật, `R83L1111AFT`)
- **Build:** versionCode **14** (versionName 2.1.0) · **Audit lúc:** 2026-09-14 13:43 (+07)
- **Kết quả đối chiếu:** **54/54 khớp · 0 lệch**

| Section | Khớp |
|---|---|
| 1. Thông số kỹ thuật | 8/8 |
| 2. ID ads FO | 40/40 |
| 4. ID ads resume | 6/6 |

## Kết luận: sạch

Không còn dòng nào chưa kết luận. Không có `confirmed` / `disputed` / `unresolved`
nào vì không có gì để phán — tầng cơ học đã giải quyết hết 54 dòng.

## vc14 là bản release, khác hẳn vc12

Mọi lượt trước trong buổi chạy trên vc12 và cho 9/54. Nguyên nhân đã xác định lúc
đó: vc12 là build dev phát quảng cáo test. vc14 xác nhận chẩn đoán đó đúng —
cùng checklist, cùng tool, cùng thiết bị, chỉ đổi build thì lệch biến mất.

| | vc12 | vc14 |
|---|---|---|
| `AdSdk: Config variant dev` | `true` | **`false`** |
| `Adjust config environment` | `sandbox` | **`production`** |
| Tham chiếu ID mẫu `3940256099942544` | 198 | **0** |
| Tham chiếu ID thật `4973559944609228` | 9 | **500** |
| Số ID thật khác nhau | 2 | **57** |
| Dòng `FOR_TESTER` | 199 | 251 |
| Khớp | 9/54 | **54/54** |

## 45 dòng chuyển từ lệch sang khớp

`delta.fixed` — toàn bộ phần lệch của vc12 đã khớp trên vc14:

- **Adjust config environment** → `production` (vc12 là `sandbox`)
- **Section 2, ID ads FO** — 38 dòng còn lại đều khớp: `101-spl-a-banner*`,
  `102-spl-o-inter*`, `105-spl-n-native*`, `106_spl_o_native*`, `201-lfo1-*`,
  `202-lfo2-*`, `301`→`306` onb*, `301_onb1_o_*`
- **Section 4, ID ads resume** — cả 6 dòng: `501_aoa_high`, `501_aoa`,
  `502_native_high`, `502_native`, `503_inter_high`, `503_inter`

Đáng chú ý: 6 dòng resume trước đây là nhóm `confirmed` với nhãn *"chưa capture
đủ"* và phản biện đã cho là đúng. Trên vc14 chúng khớp — remote config bản release
có trả giá trị cho các khoá resume, thứ mà vc12 không có.

## Cảnh báo còn lại của lượt capture

Không ảnh hưởng kết quả, nhưng ghi lại cho minh bạch:

- `missed_home: ["old"]` — luồng user cũ vẫn chưa tới Home. Không thành vấn đề ở
  lượt này vì mọi dòng đều đã khớp từ nguồn khác.
- `empty_filters: ["RemoteConfigRepository"]` — vùng log này rỗng. Cũng không cản
  trở vì các dòng placement đã khớp qua `FOR_TESTER_*`.
- `apk_scan_applicable: null` — không quét được APK lượt này (không có bản cache
  cho vc14). Không cần tới, vì toàn bộ bằng chứng đến từ log runtime.
- 11 ID thật mới xuất hiện trong log mà không nằm trên checklist
  (`delta.new_leftover_ids`): `/1248152962`, `/1374129757`, `/2752806321`,
  `/2836738907`, `/5999766241`, `/6107009235`, `/6585375592`, `/7939538105`,
  `/8175553853`, `/8434357894`, `/8869476395`. Đây là **ID build đang dùng nhưng
  checklist không liệt kê** — không phải lỗi, nhưng đáng để ads-team xem có nên bổ
  sung vào sheet không.

## Lỗi công cụ đã sửa trong buổi

| Lỗi | Sửa |
|---|---|
| Guard `if not found: break` coi focus `null` là rời app → sweep logo dừng sau 1/4 điểm → 0 dòng `FOR_TESTER` | `930a664` |
| Quét ID trong APK coi "vắng mặt" là bằng chứng kể cả khi app nạp ID qua remote config → 44 dòng bị buộc tội sai | `d224aea` |
| Màn question dò nút theo label; build ghi `"Get Started"` → capture đứng im tới hết timeout | `484abdd` |
| Verify mở 1 agent/dòng: 17 agent, 18 phút | `72e6ed8` — 1 agent/app |
| Judge viết 45 finding cho rổ chỉ có 1 nguyên nhân | rổ cùng nguyên nhân → 1 finding |
| Mở artifact là cờ opt-in → chạy xong trang không bật | `52cf491` |

Lượt này chạy hết trong **2,7 phút / 1 agent**, so với 18 phút / 17 agent lúc đầu buổi.

## Lỗi công cụ chưa sửa

1. **Thiếu cổng xác thực build trước khi triage.** Nếu ID quan sát thuộc dải mẫu
   `3940256099942544`, hoặc Adjust environment = `sandbox`, tool nên dừng và báo
   *"sai build, audit trên bản release"*. Cả buổi mất nhiều lượt chạy mới phát hiện
   vc12 là build dev — đúng thứ cổng này bắt được trong vài giây.
2. **Dòng config chữ không được đối chiếu.** Tool chỉ so giá trị có *dạng* ad unit
   ID. Cần bảng ánh xạ `production↔sandbox`, `on↔off`, `enable↔disable`.
3. `missed_home: ["old"]` — luồng user cũ vẫn chưa tới Home.

## Câu hỏi chưa giải quyết

1. **11 ID thật ngoài checklist** (`new_leftover_ids`) — build đang chạy chúng nhưng
   sheet không có. Ads-team xác nhận đây là placement mới chưa kịp ghi, hay là ID
   không nên xuất hiện?
2. vc12 (build dev, Adjust `sandbox`) có từng bị đẩy ra ngoài không, hay chỉ nằm trên
   máy test? Lượt audit vc12 có ghi nhận `logPaidAdImpression` trên một ID thật.

**Lưu ý:** bằng chứng chỉ chứng minh sheet và bản cài lệch nhau, không tự nó nói
bên nào sai. Lượt này không có dòng nào lệch, nên không có gì cần ads-team phân xử
ngoài mục 1 ở trên.

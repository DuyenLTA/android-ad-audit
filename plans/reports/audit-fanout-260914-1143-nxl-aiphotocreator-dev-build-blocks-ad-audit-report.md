# Audit checklist ads — com.nxl.aiphotocreator.aivideogenerator.texttoimage

- **Run:** `wf_a75cd28d-c7d` · **Chế độ:** capture (máy thật, `R83L1111AFT`)
- **Build:** versionCode 12 · **Audit lúc:** 2026-09-14 11:55 (+07)
- **Kết quả đối chiếu:** **9/54 khớp · 45 lệch**

| Section | Khớp |
|---|---|
| 1. Thông số kỹ thuật | 7/8 |
| 2. ID ads FO | 2/40 |
| 4. ID ads resume | 0/6 |

## Kết luận: không audit được ID production trên build này

**Bản cài phục vụ quảng cáo test ở gần như mọi placement.** Đây không còn là vấn
đề capture thiếu — lượt này capture đã đầy đủ (xem mục dưới). Màn hình đã tới,
quảng cáo đã hiện, chỉ là hiện bằng ID mẫu của Google.

Bằng chứng từ chính log tester của app, đã tự kiểm chứng lại:

| | |
|---|---|
| `FOR_TESTER_SHOW_AD: NATIVE` | **12/12 lần** dùng `ca-app-pub-3940256099942544/2247696110` (ID mẫu) |
| `FOR_TESTER_SHOW_AD: INTERSTITIAL` | 1 lần ID mẫu `/1033173712`, 1 lần ID thật `/2720278708` |
| Tổng tham chiếu trong log | **198 lần ID mẫu** vs **9 lần ID thật** |
| `FOR_TESTER_CONFIG` | `Adjust config environment: sandbox` |
| | `Version Lib Ads: 1.2.8-alpha03` |
| `AdSdk` | `Config variant dev: true` (`capture.log:1167`, `:39660` ở lượt trước) |

**Việc cần làm: lấy build release rồi audit lại.** Checklist ghi ID production;
build này phát ID test. Hai bên không so được với nhau, và 45 dòng "lệch" ở trên
phần lớn là hệ quả của việc đó, không phải sheet sai.

## Bước ngoặt của lượt này: log tester đã có

| | Trước | Lượt này |
|---|---|---|
| Dòng `FOR_TESTER` | **0** | **199** |
| `empty_filters` | `["FOR_TESTER"]` | `[]` |

`FOR_TESTER_PRELOAD` 122 · `FOR_TESTER_LOAD_AD` 47 · `FOR_TESTER_CONFIG` 16 ·
`FOR_TESTER_SHOW_AD` 14.

Nguyên nhân trước đó: `splash_logo_spam` quét 4 điểm trên dải logo để bật tester
logging, nhưng guard `if not found: break` coi **focus đọc không ra** là "đã rời
app". Lúc splash đang vẽ thì `mCurrentFocus` = `null` — đúng lúc các burst chạy —
nên sweep dừng sau điểm đầu tiên, điểm đó trượt logo, tester logging không bật.
Sửa ở `930a664`; kiểm chứng bằng cách chạy tay đúng 4 toạ độ đó, bỏ qua break →
27 dòng, rồi capture tự động → 199 dòng.

## Bốn nhóm kết quả

### `confirmed` — 1 nhóm / 6 dòng

**Section 4, ID ads resume** (`501_aoa_high`, `501_aoa`, `502_native_high`,
`502_native`, `503_inter_high`, `503_inter`) — **chưa capture đủ**, luận điểm đứng
sau phản biện.

Luồng resume cần chu kỳ background→foreground; lượt này chỉ có 2 lần cold start.
Log chỉ có `AppOpenManager: disableAppResumeWithActivity`, không có lần nạp AOA
nào. Phản biện bổ sung: remote config **không trả giá trị** cho `resume_type`,
`enable_resume`, `enable_resume_high`, `load_ads_resume` (`capture.log:3728-3731`)
→ capture lại nhiều khả năng vẫn không ra ID.

### `disputed` — 2 nhóm, cần người xem lại

**1) 9 dòng luồng old** — judge gắn `chua-capture-du`, **phản biện bác bỏ, và đúng**.

`missed_home: ["old"]` đúng, nhưng các placement này nằm **trước** Home nên
missed_home không giải thích được. Quan trọng hơn: `KEY[106_SPL_O_NATIVE_HIGH]`
**đã chạy trọn** trong lượt old — preload → loaded → `FOR_TESTER_SHOW_AD: NATIVE`
lúc 11:54:37→11:54:42 — và ID hiện ra là ID mẫu `2247696110`, không phải ID
checklist. Nhãn đúng: **build phát ID test**, không phải chưa capture đủ. Hệ quả:
"capture lại đi hết tới Home" sẽ không giải quyết được gì.

**2) Adjust config environment** — judge gắn `checklist-sai`, **phản biện bác bỏ**.

Sheet ghi `production` là *giá trị yêu cầu*; build chạy `sandbox`
(`FOR_TESTER_CONFIG: Adjust config environment: sandbox`). Lệch thật, nhưng lệch ở
**phía build**, không phải sheet ghi sai.

### `unresolved` — 2 nhóm / 29 dòng, chưa từng qua phản biện

- **28 dòng FO luồng new** (101 spl banner ×2, 105 spl native ×2, …) — agent tự
  nhận không đủ bằng chứng.
- **1 dòng** `ca-app-pub-4973559944609228/1407197037` (`102-spl-n-inter-high1`).

### `clean` — không có

## Lỗi công cụ đã sửa trong buổi

| Lỗi | Sửa |
|---|---|
| Guard `if not found: break` coi focus null là rời app → sweep logo dừng sau 1/4 điểm → **0 dòng FOR_TESTER**, mất toàn bộ bằng chứng runtime | `930a664` |
| Quét ID trong APK coi "vắng mặt" là bằng chứng kể cả khi app nạp ID qua remote config → **44 dòng bị buộc tội sai** là "checklist ghi ID không tồn tại" | `d224aea` |
| Màn question dò nút theo label; build này ghi `"Get Started"` → capture đứng im tới hết timeout | `484abdd` |
| Verify mở 1 agent/dòng: 17 agent, 18 phút | `72e6ed8` — 1 agent/app |
| Judge viết 45 finding cho rổ chỉ có 1 nguyên nhân | rổ cùng nguyên nhân → 1 finding |
| Mở artifact là cờ opt-in → chạy xong trang không bật | `52cf491` |

## Lỗi công cụ **chưa** sửa

1. **Thiếu cổng xác thực build trước khi triage.** Nếu (a) `build_ad_ids` không có
   ID thật nào, hoặc (b) ID quan sát trong log thuộc dải mẫu `3940256099942544`,
   hoặc (c) Adjust environment = `sandbox` → phải dừng và báo **"sai build, audit
   trên bản release"**, thay vì sinh 44 dòng rồi để người đọc tự gán nhãn. Hiện
   tool mới bắt được vế (a) và diễn giải sai hướng thành "cần capture đúng màn".
2. **Dòng config chữ không được đối chiếu.** Tool chỉ so giá trị có *dạng* ad unit
   ID. Với dòng `production`, token đối lập `sandbox` nằm sẵn trong
   `result.extra` của chính tool mà không nối được. Cần bảng ánh xạ
   `production↔sandbox`, `on↔off`, `enable↔disable`.
3. **`missed_home: ["old"]` vẫn còn** — luồng user cũ chưa tới Home.

## Câu hỏi chưa giải quyết

1. **Build vc12 có phải build định phát hành không?** Nếu đúng thì `Config variant
   dev: true` + Adjust `sandbox` + ID ads test là lỗi chặn release.
2. **Vì sao 1 interstitial dùng ID thật `2720278708` giữa một build toàn ID test?**
   Lượt trước ID này còn có impression tính tiền (`logPaidAdImpression`). Cố ý hay
   lỗi cấu hình?
3. Luồng resume có show được không kể cả khi capture đúng — remote config không trả
   giá trị cho bất kỳ khoá resume nào.
4. 28 dòng FO luồng new vẫn chưa ai kết luận; cần build release rồi mới xét lại.

**Lưu ý:** bằng chứng chỉ chứng minh sheet và bản cài lệch nhau, không tự nó nói
bên nào sai. Cần ads-team xác nhận.

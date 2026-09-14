# Gate lượt chạy: thêm vế checklist, dùng lại capture, và đo lại 3 giới hạn

5 đề xuất được soi. **2 sửa code, 1 sửa để nói thật, 2 không làm** — lý do dưới, kèm phép đo.

269 test pass (trước: 248). Chưa commit.

---

## 1. Gate chỉ theo versionCode → SỬA

**Đúng.** `audit_runner.py` so đúng `previous["version_code"] == version_code`. Sheet đổi mà
app chưa đổi → vẫn skip → trả kết luận cũ cho checklist mới, không có gì trên trang nói ra.

**Đã làm:**

- `checklist_source.checklist_fingerprint(rows)` — sha256 của **rows đã parse**, không phải
  CSV thô. Re-export, đổi comment cột 4, thêm dòng trống → cùng digest. Đổi section / label /
  value / alt_value → khác digest. Thứ tự alt_values không tính (cell đó vô thứ tự).
- Digest nằm ở **envelope snapshot**, cạnh `version_code` — không nhét vào `result`. Nó là
  metadata của phép so, không phải một dòng checklist.
- Skip khi **cả hai vế** y nguyên. Message đổi: `build và checklist đều chưa đổi`.
- Snapshot cũ không có digest → đọc là **chưa biết**, audit thêm một lượt rồi tự lành.
  Đọc là "chưa đổi" thì mọi snapshot cũ sẽ skip vĩnh viễn.

**Phần đắt giá nhất — không lái máy lại:** sheet đổi + build chưa đổi + có log cũ →
`capture_and_audit` đối chiếu lại trên `out/<pkg>-capture.log` thay vì drive phone. Không có
gì trên sheet làm thay đổi được việc app đã chạy ra sao. Vài giây thay vì vài phút.

Mang theo `missed_home` của lượt capture cũ — độ phủ là thuộc tính của **log**, không phải của
lượt đọc lại nó. Bỏ đi thì trang sẽ khai "lượt này không capture" và cờ lại những dòng đã giải
thích xong. Ghi thêm `capture_reused_from`; banner nói rõ dùng log ngày nào.

Chạy thật, máy `99261FFAZ0077C`:

```
[52/54] com.nxl...texttoimage: 2 dòng mới lệch     ← snapshot cũ không digest → audit lại
[bỏ]    com.nxl...texttoimage: build và checklist đều chưa đổi (versionCode 14)
```

> Lượt smoke test đó ghi đè baseline capture 54/54 bằng baseline APK-only 52/54. Đã khôi phục
> bằng cách đối chiếu lại trên log capture vc14 còn trên đĩa → 54/54, `missed_home: ["old"]`,
> digest `cf9a0059d206f253`. Lượt sau so với mốc đúng.

## 2. Phát hiện dev-build đến trễ → chỉ sửa được phần NÓI THẬT

**Tiền đề đúng, cách đề xuất không chạy được.** Quét chuỗi tĩnh trên chính APK **release**
vc14 đang cài:

```
Config variant dev          -> CÓ (classes6.dex)
setupAdjust                 -> CÓ (classes6.dex)
sandbox                     -> CÓ (classes3.dex, classes4.dex)
ca-app-pub-3940256099942544 -> CÓ (classes6.dex, resources.arsc)
```

Đó là **format string in log** và **hằng số của SDK** — build nào cũng có. Quét tĩnh sẽ báo
mọi build là build dev. `android:debuggable` thì không kiểm chứng được: không còn APK dev vc12
để đối chứng, và build dev loại này thường ký release + không debuggable (nên mới gửi được cho
tester).

Thêm nữa, ở **luồng capture** gate tĩnh sẽ **chậm hơn**: pull APK mất vài chục giây, còn marker
trong log tới sau ~1 giây. `log_watcher` đã bỏ dở ngay tại đó.

**Lỗ thật tìm ra khi soi chỗ này:** `dev_build_signals()` chỉ đọc giá trị app **chạy ra**, nên
lượt `--apk` luôn trả `[]` → triage ghi `[]` → đọc như "đã kiểm, build sạch". Lượt đó không có
gì để đọc.

**Đã làm:** triage ghi `null` (chưa biết) chứ không `[]` khi không có log; banner nói thẳng
"cũng vì thế mà chưa kiểm được đây là build release hay build dev".

## 3. Remote Config API làm nguồn bằng chứng thứ 4 → KHÔNG LÀM, ghi vào giới hạn

Chẩn đoán đúng: app nạp ID lúc chạy rơi vào rổ `APK không kiểm được`, lối ra duy nhất là chờ
log bắt trúng màn. Hỏi thẳng Firebase Remote Config sẽ lấp đúng khoảng trống đó.

Cần **credential của project Firebase** — lượt audit không có, và đó là quyền của app team chứ
không phải của người chạy audit. Không dựng stub. Đã ghi vào "Giới hạn đã biết" để lần sau ai
có quyền thì biết đây là việc đáng làm.

## 4. Biến thể A/B theo cohort → KHÔNG LÀM, ghi vào giới hạn

Không có bằng chứng app này chia cohort, và không biết cơ chế ép cohort nào.

Quan trọng hơn: hệ quả **không phải kết luận sai**. Dòng không thấy rơi vào "chưa kết luận" chứ
không bị buộc tội — thiết kế "vắng mặt trong log không bao giờ là bằng chứng" đã che đúng ca
này. Cái mất là **tính tái lập**. Đã ghi vào giới hạn: đừng đọc một lượt sạch là đã phủ hết
mọi nhóm.

## 5. Không lưu lịch sử report → SỬA

`artifact_report_builder.archive_previous()` copy trang cũ sang `out/history/<pkg>-artifact-<lúc>.html`
trước khi ghi đè. Copy chứ không move: write hỏng sau đó thì trang published vẫn còn chỗ cũ.

Republish giữ nguyên link là **cố ý** (link đã chia sẻ), giá phải trả là trang cũ biến mất khỏi
link đó. `plans/reports/` giữ báo cáo markdown nhưng không giữ **thứ ads-team thật sự nhìn thấy**.

---

## File đổi

| File | Đổi gì |
|---|---|
| `checklist_source.py` | `checklist_fingerprint()` |
| `check_ads.py` | re-export fingerprint |
| `audit_pipeline.py` | `run_audit(checklist=...)` — nhận sheet đã fetch, khỏi tải 2 lần |
| `audit_snapshot.py` | `save(..., checklist_digest=)` trên envelope |
| `audit_runner.py` | `_skip_reason`, `_only_the_sheet_moved`, `_previous_triage`; nhánh dùng lại log; `dev_build_signals` → `null` khi không log |
| `artifact_run_context.py` | banner: chưa kiểm được build; banner: log dùng lại |
| `artifact_report_builder.py` | `archive_previous()` |
| `.claude/workflows/audit-fanout.mjs` | comment + prompt agent theo gate mới |

**Test mới (21):** 8 fingerprint · 7 gate/reuse · 3 archive · 4 banner. Kiểm phản chứng: bỏ vế
checklist ra khỏi `_skip_reason` → 4 test mới đỏ đúng chỗ.

**Artifact đã publish lại:** `d95e3c4a` v4 · `d7935fbb` v7 · `375ccb87` v10 — cả ba đều còn câu
"không có `--force` thì build chưa đổi sẽ bị bỏ qua", giờ đã đúng.

## Câu hỏi chưa giải quyết

1. `b499b2e9` ("Ad Checklist Diff") vẫn mô tả Streamlit GUI đã xoá ở `b8f947e` — cắt phần GUI
   giữ lại trang CLI thủ công, hay cho nghỉ hẳn?
2. Digest hiện tính trên **toàn tab**. Sửa một dòng ở section không liên quan cũng khiến app
   audit lại. Có muốn chặt hơn không, hay cứ để thận trọng?
3. `out/history/` chưa có giới hạn số bản. Mỗi trang ~50–100 KB, chưa đáng lo — có muốn tự dọn
   sau N bản không?
4. Có ai trong team lấy được credential Firebase Remote Config không? Đó là thứ duy nhất mở
   được rổ "APK không kiểm được".

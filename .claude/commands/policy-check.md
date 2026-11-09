---
description: Check policy Ads + Sub (sheet Apero Policy) của một app Android trên máy thật, rồi xuất báo cáo artifact
argument-hint: "<package> [--serial <serial>] [--no-sub] [--no-fresh] [--grade <run-dir>]"
---

Check policy quảng cáo và gói mua của một app theo sheet **Apero Policy** (tab Đối tác + Ad_VN + Sub_VN,
mọi app dùng chung bộ rule — user chốt 04/11/2026), trên máy thật, bản **release** có ad thật.
Kết quả chỉ ra **artifact**, không ghi ngược vào sheet. Tham số: $ARGUMENTS

## 0. Tìm repo

- `<repo>` (repo này): `git rev-parse --show-toplevel` nếu CWD nằm trong nó, rồi `$AD_AUDIT_REPO`, rồi
  `~/android-ad-audit` — lấy chỗ đầu tiên có `tools/ad-policy-check/evidence_collector.py`.
- `<rc>` (trình lái + khóa máy dùng chung): `$RC_RUNNER_REPO`, rồi `~/Desktop/check_remote_config`, rồi
  `~/check_remote_config` — chỗ có `src/rcr/fo_flow.py`.
- `<tool>` = `<repo>/tools/ad-policy-check`. Bộ gom chạy bằng **venv của `<rc>`**
  (`<rc>/.venv/Scripts/python`), phần chấm và report chạy bằng venv của `<repo>` (`<repo>/.venv/Scripts/python`,
  cần `imageio-ffmpeg` trong `requirements.txt`).

Không thấy repo nào thì dừng và nêu các chỗ đã thử. Mọi lệnh: `cd <tool> && PYTHONIOENCODING=utf-8 …`.

## 1. Máy và app

1. `adb devices`: một máy thì lấy máy đó; nhiều máy mà không có `--serial` thì hỏi máy nào.
2. App phải cài sẵn và là **bản release**: `adb -s <serial> shell dumpsys package <pkg>` — có `DEBUGGABLE`
   trong flags thì dừng ("bản debug, ad test không đo được AdChoices/nhãn thật"). Lấy `versionName`/`versionCode`.
3. Mọi máy là máy test AdMob và mọi tài khoản là license test: được bấm ad, được mua sub, không hỏi.
4. Lượt trước còn sub test chưa huỷ thì bộ gom tự dừng (exit 5) — sub test tự hết sau 6 lần gia hạn × 5 phút.
   Lượt mua chỉ bấm Subscribe khi sheet Play ghi "Test card"; không thấy thì không mua.

`--grade <run-dir>`: bỏ qua bước 2, chấm lại một lượt đã có.

## 2. Gom bằng chứng (máy)

```
cd <tool> && PYTHONIOENCODING=utf-8 <rc>/.venv/Scripts/python -W ignore evidence_collector.py --package <pkg> --serial <serial> [--no-sub] [--no-fresh]
```

Chạy ~6-8 phút: `pm clear` → FO tới Home bằng `rcr.fo_flow.walk_to` (bấm thử CTA native, inter từ cái thứ 2,
link Privacy trên paywall; ở màn Onboarding đầu tiên ẩn app rồi mở lại để bắt resume ad — resume chỉ có trong
tutorial — rồi bấm thử nó) → Home/mở lại (Home không được có resume) → dò Home (Settings + Privacy/Terms/Share/Rate, màn nội dung,
paywall qua nút Pro) → mua sub test → tìm "Cancel sub" trong app → huỷ trên Play. In ra `<run-dir>`.

- Exit 3 = máy đang có lượt khác giữ khóa `<rc>/out/.may-<serial>.lock` → dừng, báo, không chen.
- Exit 5 = lượt trước đã mua sub test mà chưa huỷ được, app còn Pro (không ad) → báo số phút còn phải chờ, không chạy.
- Exit 4 = lượt dừng giữa chừng (`meta.json.error`). `ForeignDriverError` = có phiên khác lái chung máy: không
  chấm, báo user. Lỗi khác: vẫn chấm phần đã có, ghi lý do vào câu báo.
- Lỗi của tool (driver kẹt, bấm sai, parse sai trên app mới) → Claude tự sửa trong `<tool>`, chạy test
  (`<repo>/.venv/Scripts/python -m pytest -q`), chạy lại — không giao lại user.

## 3. Chấm

```
cd <tool> && PYTHONIOENCODING=utf-8 <repo>/.venv/Scripts/python policy_check_runner.py <run-dir>
```

App không bán sub (plan tuần / tin build ghi "Off subs") thì thêm `--off-sub "plan tuần ghi Off subs"`: rule Sub
đang BLOCKED vì không tới paywall thành **N/A**. Vẫn gặp paywall thì rule vẫn chấm bình thường, ghi mâu thuẫn vào notes.

Ra `results.json` (mỗi checker: PASS / FAIL / CAN_XEM / BLOCKED / NA + lý do + bằng chứng) và
`visual-queue.json`. Rule mới trong sheet chưa có checker hiện thành "chấm tay" — thêm checker vào
`policy-checkers.json` + module `checkers_*.py` nếu làm được trong lượt.

## 4. Claude chấm phần phải nhìn

Đọc `visual-queue.json`; với mỗi mục **Read từng ảnh** trong `images` (sheet video 1 ô/giây, ảnh màn) và trả lời
đúng `question` theo chữ của rule. Luật:
- Kết luận **chỉ PASS hoặc FAIL** (user chốt 09/11/2026: không để Cần xem / BLOCKED / chờ người). Chấm theo chữ
  rule + ví dụ trong sheet. Ảnh chưa đủ để kết luận → lấy thêm bằng chứng (sheet video dày hơn qua
  `Run.video_sheet`, ảnh khác trong `frames/`, dòng `logcat.txt`) hoặc lái máy đo lại (mục 4b), không đoán PASS.
- Ảnh màn được chụp **ngay sau** dump nên có thể lệch vài trăm ms; dump và ảnh mâu thuẫn → tin dump, ghi rõ.
- Nút X / đếm ngược: đếm ô từ ô đầu có ad. Inter **đầu tiên** không bị bấm thử (để đo X); inter đã bấm thử
  dừng video nên X có thể không hiện — đừng chấm X trên inter đó.

Ghi `<run-dir>/visual-verdicts.json` = `{checker_id: {"status": "...", "reason": "...", "evidence": [...]?,
"judged_by": "..."?}}` rồi gộp: `policy_check_runner.py <run-dir> --visual <run-dir>/visual-verdicts.json`.

## 4b. Chốt hết BLOCKED / Cần xem — bắt buộc trước report

`policy_check_runner.py` (cả khi gộp `--visual`) exit 2 và in `CÒN n MỤC CHƯA CHỐT` khi còn CAN_XEM/BLOCKED;
`policy_report.py` cũng từ chối ra report khi còn. Gỡ từng mục theo thứ tự:

1. **Chạy bổ sung trên máy** (lượt chính không tới được Settings / màn tiện ích, kết quả AI, paywall, mua sub):
   `cd <tool> && PYTHONIOENCODING=utf-8 <rc>/.venv/Scripts/python -W ignore evidence_followup.py <run-dir> --serial <serial> [--no-sub]`
   — mở lại app (không `pm clear`), dò Home + mua sub, ghi nối vào cùng `<run-dir>`; rồi chấm lại (mục 3–4).
   Driver kẹt ở màn lạ → sửa `evidence_home_explorer.py` (thêm test từ dump màn đó), chạy lại.
2. **Claude tự lái máy** bằng adb khi tool vẫn chưa tạo được điều kiện: tới đúng màn rule cần, chụp
   `screencap` + `uiautomator dump` vào `<run-dir>/manual/`, đo/nhìn, ghi verdict PASS/FAIL với `evidence`
   là các file đó và `"judged_by": "Claude lái tay"`. Lỗi tool gặp lúc này → sửa tool cho lượt sau.
3. **N/A chỉ khi app thật sự không có thứ rule nói tới** — phải có căn cứ, ghi vào lý do: app Off subs
   (`--off-sub`), checklist ads của app không có vị trí reward/banner, app không có tính năng AI tạo nội dung,
   resume đã thử ở tutorial mà không bật. "Lượt này chưa gặp" chưa phải căn cứ → quay lại bước 1–2.

## 5. Rà FAIL giả và PASS giả — bắt buộc trước khi báo

Mở bằng chứng của **mọi FAIL** và mọi PASS dựa trên đo đạc lạ. Bẫy đã gặp (đã sửa trong code, gặp kiểu mới thì sửa tiếp):
- native đang vuốt dở (khung chạm mép, hẹp hơn màn) → nhãn Ad ngoài màn, không phải thiếu;
- WebView là media của native hoặc chính inter → không phải "màn webview của app";
- khung chứa native không id bao ngoài ad → không phải "content đè ad";
- cửa sổ resume chỉ là ~10s sau khi mở lại app; inter khi bấm nội dung ở Home không phải resume;
- khung native không id: tool lấy node nhỏ nhất bao media + CTA + nhãn Ad (không dùng AdChoices để dựng khung).

Cách hiểu user đã chốt (04/11/2026): link Privacy / Terms mở ra ngoài app là **đạt** (chỉ cần có và bấm mở được);
không có free trial thì rule trial **N/A**; paywall không có sale hiện 2 giá là **FAIL**. Tool chỉ check **Android**: rule chỉ dành cho iOS (Restore,
Sub_VN #10 — kind `ios_only` trong `policy-checkers.json`) bị bỏ hẳn, không chấm, không lên report (user chốt
09/11/2026). Sheet thêm rule iOS mới → map vào checker `ios_only`, đừng để nó thành "rule chưa có checker".
FAIL thật phải có bằng chứng chỉ ra được (ảnh / dòng log / toạ độ). Một lượt bằng chứng chắc là đủ, không chạy lặp để xác nhận.

## 6. Ghi nhận ngoài sheet

Quét `logcat.txt`: exception trong SDK ads (`System.err` quanh `populate…AdView`, `GoogleMobileAds` lỗi), popup
AdMob native validator báo issue, màn loading lạ. Ghi `<run-dir>/notes.json` = `[{"title", "detail"}]` —
phát biểu là "cần dev xem", không khẳng định bug.

## 7. Report

```
cd <tool> && PYTHONIOENCODING=utf-8 <repo>/.venv/Scripts/python policy_report.py <run-dir> --app "<tên app> <versionName> (<versionCode>) · release" --title "Policy <tên ngắn> <versionName>" --notes <run-dir>/notes.json --out <scratchpad>/policy-<pkg>.html
```

Publish file đó thành artifact (icon `checklist`). Cùng app thì **republish đè cùng link**: link lưu ở
`<tool>/out/<pkg>/artifact-link.txt` — đọc trước, có thì publish với `url` đó; publish xong ghi lại. Không tự mở
artifact, chỉ đưa link.

## 8. Báo lại

Mở đầu bằng link artifact, rồi: app + version + máy; số PASS/FAIL/N/A; từng FAIL kèm bằng chứng một dòng; N/A kèm
căn cứ; mục nào Claude lái tay mới chốt được thì nói rõ; ghi nhận ngoài sheet; trạng thái sub
(đã huỷ chưa). Lượt chạy từ tin build trong qa-auto thì gửi kết quả vào qa-auto (trả lời dưới tin build).
Không commit gì nếu user chưa bảo.

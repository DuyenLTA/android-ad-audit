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
link Privacy trên paywall) → Home/mở lại (resume) → dò Home (Settings + Privacy/Terms/Share/Rate, màn nội dung,
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
- Chỉ chấm theo rule + ví dụ trong sheet; không chắc → `CAN_XEM` kèm điều cần người nhìn, không đoán PASS.
- Ảnh màn được chụp **ngay sau** dump nên có thể lệch vài trăm ms; dump và ảnh mâu thuẫn → tin dump, ghi rõ.
- Nút X / đếm ngược: đếm ô từ ô đầu có ad. Inter **đầu tiên** không bị bấm thử (để đo X); inter đã bấm thử
  dừng video nên X có thể không hiện — đừng chấm X trên inter đó.

Ghi `<run-dir>/visual-verdicts.json` = `{checker_id: {"status": "...", "reason": "..."}}` rồi gộp:
`policy_check_runner.py <run-dir> --visual <run-dir>/visual-verdicts.json`.

## 5. Rà FAIL giả và PASS giả — bắt buộc trước khi báo

Mở bằng chứng của **mọi FAIL** và mọi PASS dựa trên đo đạc lạ. Bẫy đã gặp (đã sửa trong code, gặp kiểu mới thì sửa tiếp):
- native đang vuốt dở (khung chạm mép, hẹp hơn màn) → nhãn Ad ngoài màn, không phải thiếu;
- WebView là media của native hoặc chính inter → không phải "màn webview của app";
- khung chứa native không id bao ngoài ad → không phải "content đè ad";
- cửa sổ resume chỉ là ~10s sau khi mở lại app; inter khi bấm nội dung ở Home không phải resume;
- khung native không id: tool lấy node nhỏ nhất bao media + CTA + nhãn Ad (không dùng AdChoices để dựng khung).

Cách hiểu user đã chốt (04/11/2026): link Privacy / Terms mở ra ngoài app là **đạt** (chỉ cần có và bấm mở được);
không có free trial thì rule trial **N/A**; paywall không có sale hiện 2 giá là **FAIL**; Restore chỉ iOS → **N/A**.
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

Mở đầu bằng link artifact, rồi: app + version + máy; số PASS/FAIL/Cần xem/BLOCKED/N/A; từng FAIL kèm bằng chứng
một dòng; mục Cần xem nói rõ cần nhìn gì; BLOCKED nói thiếu điều kiện gì; ghi nhận ngoài sheet; trạng thái sub
(đã huỷ chưa). Lượt chạy từ tin build trong qa-auto thì gửi kết quả vào qa-auto (trả lời dưới tin build).
Không commit gì nếu user chưa bảo.

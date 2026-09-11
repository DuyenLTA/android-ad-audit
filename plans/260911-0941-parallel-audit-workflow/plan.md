# Parallel Audit Workflow — nhiều app, chạy lặp, ít người can thiệp

Chuyển `tools/ad-checklist-diff` từ tool 1-app-1-người thành pipeline chạy được
nhiều app song song và lặp định kỳ.

## Nguyên tắc
- Phần diff/scan giữ nguyên là Python deterministic. Agent chỉ phán dòng
  ambiguous, viết report, quyết định escalate.
- Tách 2 lane: **device-free** (fan-out không giới hạn) và **device-bound**
  (queue tuần tự, 1 device).

## Dữ kiện đã đo (không đoán)
- APK scan 3 app song song, không cần device: **0.6s** (78/80/84 ID mỗi app).
- APK verify cứu được **42/45** dòng ID mà không vào màn nào.
- Mở app không tap gì: `FOR_TESTER = 0` → log tester **bắt buộc** spam logo.
- Spam tap `540,1000` trên 1080x2280: `FOR_TESTER 53`, `_CONFIG 8`, `_LOAD_AD 23`.
- Luồng thật: Splash → `VslTemplate4OnboardingActivity` (`id/btnNextOnboarding`)
  → `VslTemplate4QuestionActivity` → `gms.ads.AdActivity` → `VslBillingActivity`
  ("Continue with ads") → `...MainActivity` = Home.
- Máy hiện tại **không có KVM** (`/dev/kvm` absent, 0 vmx/svm) → emulator không
  khả thi ở đây; APK có đủ `x86_64` nên máy có KVM thì mở được hướng đó.
- 2 luồng cần test riêng: **new user** (`pm clear` → ads FO) và **old user**
  (launch thường → ads resume/inapp).

## Phases
| # | Phase | Trạng thái |
|---|-------|-----------|
| 01 | [Headless audit engine](phase-01-headless-audit-engine.md) — CLI `--json/--apk/--package`, log optional, exit code, registry | **Xong** |
| 02 | [Device driver automation](phase-02-device-driver-automation.md) — tự mở app, spam logo, qua onboarding, 2 luồng user | **Xong** |
| 03 | Agent fan-out (`workflows/audit-fanout.mjs`): 1 agent/app phán dòng ambiguous, có lượt phản biện | **Xong** |
| 04 | Lặp định kỳ: `audit_runner.py` bỏ qua build chưa đổi, diff snapshot, xuất delta + triage | **Xong** |
| 05 | Lane device trong runner (`--capture`) + cron hàng ngày (`scheduled-audit.sh`) | **Xong** |

## Dependencies
- 01 chặn tất cả: chưa có JSON + CLI device-free thì agent phải parse HTML.
- 02 độc lập với 01 về code, nhưng 03 cần cả hai.
- 04 cần snapshot JSON của 01.

## Không làm (YAGNI)
- Không biến diff/scan thành agent.
- Không dùng Agent Teams — đây là audit định kỳ, không phải nhiều người sửa code.
- Không auto-host report (đã chốt: giữ artifact publish qua Claude).

## Kết quả Phase 01 + 02 (đo thật)
- 1 lệnh, không ai đụng máy: chạy cả 2 luồng (new + old) vào tới Home, capture
  chung 1 log → **71/76**, đúng bằng bản chạy tay.
- `--apk` chạy không cần device: 64/76 (mục "Thông số kỹ thuật" vẫn cần log).
- Exit code: 2 khi còn Lệch, 0 khi đủ.
- 5 dòng Lệch còn lại là thật: 2 ID `306_onb4_n_inter*` + `inter_feature_high`
  không có trong APK; `inter_result*` thì placement không tồn tại trong build.

## Kết quả Phase 03 + 04 (đo thật)
- `audit_runner.py` chạy 3 lần liên tiếp: lần 1 audit (64/76, 12 dòng mới lệch),
  lần 2 **bỏ qua** vì versionCode 33 chưa đổi, lần 3 `--force` → không đổi.
- Triage tách đúng: 5 dòng "không có trong build" (5 lỗi thật) + 7 dòng "chưa
  thấy trong log" (mục thông số kỹ thuật, do lượt đó chạy APK-only).
- Bug bắt được: file triage từng trùng tên với file snapshot nên ghi đè baseline
  → mất lịch sử. Đã đổi thành `<package>-triage.json`, có test chặn.
- Còn lại: cron thực tế (chạy `audit_runner.py` theo lịch) và chạy thử workflow
  agent — cả hai chưa bật.

## Kết quả Phase 05 (đo thật)
- Lane device đã nằm trong runner: `audit_runner.py --capture` tự lái máy cho
  từng app rồi audit trên đúng log vừa ghi, tuần tự một app một lượt. Trước đó
  runner chỉ có lane APK; phần capture vẫn phải chạy tay.
- Chạy thật 1 lệnh, không ai đụng máy: **71/76**, đúng bằng bản chạy tay ở
  Phase 02. So với baseline APK-only: 7 dòng "fix" (đúng các dòng chỉ log mới
  trả lời được), 0 dòng mới lệch, 2 ID lạ mới.
- Triage sau lượt capture: 5 dòng "không có trong build", **0 dòng "chưa thấy
  trong log"** -- đúng như kỳ vọng, 7 dòng "chưa thấy" của lượt APK-only trước
  đó là giả, do lượt đó không capture.
- Cron đã bật: `0 9 * * *` gọi `scheduled-audit.sh` (APK-only). Wrapper chỉ in
  ra stdout khi có dòng mới lệch hoặc lỗi, nên cron chỉ gửi mail khi có chuyện;
  không có máy cắm thì bỏ lượt, exit 0. Đã test cả hai nhánh.
- Sửa kèm: `run_all` không truyền `snapshots_dir` nên test ghi thẳng vào
  `snapshots/` thật (`com.a.json`, `com.b.json` lẫn với baseline). Đã thông
  tham số và thêm test chặn.

## Kết quả chạy thật agent fan-out
- 6 agent (1 judge + 5 phản biện), 0 lỗi, ~12 phút, 656k token.
- **4/5 finding được giữ, 1 bị bác.** Dòng bị bác (`inter_result_high`): nhãn
  cuối đúng nhưng 2/3 bằng chứng sai -- judge nói "không có biến thể result nào
  trong build", thực tế build có `show_result_img_vid(_high)`. Lượt phản biện
  làm đúng việc của nó.
- Kết luận được giữ: cặp `306_onb4_n_inter*` là **checklist ghi sai ID** (build
  dùng `6620824217`/`5307742543`, và placement tên `onb5` chứ không phải
  `onb4`); `inter_feature_high` cũng checklist sai (build dùng `1744932982`);
  `inter_result` là **build thiếu placement** thật.
- 2 "ID lạ mới" mà pass deterministic bắt được chính là ID build đang dùng --
  hai lớp độc lập chỉ vào cùng một chỗ.

## Khoảng hở filter -- đã đóng
- Dòng `D TAG : loadInterstitialAd: <high> - <normal>` không khớp filter nào
  trong 6 filter cũ, nên nửa normal của cặp (`5307742543`) không vào
  `trusted_values` và không hiện ở `leftover_ids`. Không phải lỗi
  `extract_values` -- nó đã `finditer` mọi ID trên dòng.
- Người dùng chốt thêm `loadInterstitialAd` vào `DEFAULT_FILTERS`. Đo trên đúng
  log capture: **71/76 không đổi, 0 dòng đổi trạng thái** (không sinh "Khớp"
  giả -- đây là rủi ro chính của việc nới filter), `5307742543` vào đúng
  `leftover_ids`. Baseline snapshot đã chạy lại để lượt sau không báo nhầm ID
  này là "ID lạ mới".
- Gộp kèm: GUI có list filter riêng trùng nội dung với CLI. Sửa một chỗ là hai
  bên lệch nhau, nên `streamlit_app.FILTERS` giờ trỏ thẳng vào
  `check_ads.DEFAULT_FILTERS`, có test chặn.

## Việc còn lại
- Sửa sheet theo 4 finding đã giữ: quyết định của người làm checklist, không
  phải của tool.
- Push: credential hiện tại (`DuyenLTA`) không có quyền ghi vào
  `LuuThiAnDuyen/android-ad-audit`, commit đang nằm local.

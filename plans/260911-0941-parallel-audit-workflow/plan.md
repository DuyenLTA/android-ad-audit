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
| 03 | Agent fan-out (Workflow): 1 agent/app phán dòng ambiguous + viết report | Sau 01+02 |
| 04 | Lặp định kỳ: cron theo versionCode, diff 2 snapshot JSON, chỉ báo delta | Sau 03 |

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

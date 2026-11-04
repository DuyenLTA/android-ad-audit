# Plan: tự check policy Ads + Sub trên máy thật

Nguồn rule: sheet "Apero Policy" (`17r_R39x2F8RyQDBgHUeq5jWwzAGS92yQNb9RXS4-NLA`)
- Ad_VN: 19 rule · Đối tác: 33 rule (bao trùm Ad_VN, thêm resume/webview/no-data/close 15s/link "AD") · Sub_VN: 10 rule · Ads_ENG: bản EN

## Hình thức: tool + 1 command, đặt trong repo `android-ad-audit`
- **Tool Python** (`tools/ad-policy-check/`): lái máy, gom bằng chứng, tự chấm rule đo được bằng số (bounds, thời gian, app đang foreground)
- **Claude chấm bằng mắt**: chỉ những rule cần nhìn ảnh (nền trong suốt, bố cục bị cắt, màu nền, text sub)
- **Command `/policy-check <package> [--ads|--sub]`**: chạy tool → Claude chấm phần visual → publish artifact → báo Discord
- Không dùng Workflow fan-out, không tách repo: dùng lại `device_*.py`, `log_extractor.py`, `checklist_source.py`, `artifact_report_builder.py`, `discord_notify.py`

## Nguyên tắc
- Đọc sheet live mỗi lượt (như checklist ads). Map rule → checker theo **(tab, N°)** trong `policy-checkers.yaml`. Rule mới chưa map → hiện "CHƯA CÓ CHECKER, chấm tay", không bỏ qua im lặng
- Mỗi rule ra 1 kết quả: PASS / FAIL / CẦN XEM / BLOCKED / N/A, kèm ảnh + đoạn log + toạ độ
- Bắt bằng chứng **theo từng lần ad xuất hiện** (key theo placement lấy từ logcat), không theo rule
- Bấm ad là được (mọi máy là máy test AdMob)

## Phase
| # | Phase | Status |
|---|---|---|
| 1 | [Map rule + checker registry](phase-01-rule-registry.md) | Done |
| 2 | [Bộ gom bằng chứng ad](phase-02-ad-evidence-collector.md) | Done |
| 3 | [Checker tự động Ads](phase-03-ads-auto-checkers.md) | Done |
| 4 | [Chấm visual + report + command](phase-04-visual-judge-report-command.md) | Done |
| 5 | [Sub / paywall](phase-05-subscription-paywall-checks.md) | Done (huỷ sub trên Play chưa chạy được: Play báo Server error) |

| 6 | Gắn vào rc-check: mục 7a trong `check_remote_config/.claude/commands/rc-check.md` — chạy `/policy-check <pkg> --serial <serial>` **cuối lượt** (sau khi case xong + `--restore`), vì lượt policy mua sub test làm app Pro ~30 phút, chạy trước thì hỏng case ads (đổi so với ý ban đầu "sau 3c"). Không chặn rc-check | Done |

MVP = phase 1→4 với Inter + Native + Banner + "click ad có xử lý". Phase 5 làm sau khi MVP chạy thật trên 1 app.

## Phân loại nhanh (chi tiết ở phase 1)
- **Tool tự chấm (~55%)**: loading trước inter, inter hiện ngay sau click, nút tắt ≤15s, tắt inter có chuyển màn, inter không trước splash, click ad/CTA có xử lý, không ad trên màn webview, ad/content đè nhau, MediaView ≥120dp, Attribution ≥15px, AdChoices trong khung, loading ≥3/4 kích thước ad, loading có ngay từ đầu, resume không show sau permission/rate/privacy, Privacy/ToS mở in-app
- **Claude nhìn ảnh (~35%)**: nền resume trong suốt, bố cục native bị cắt, màu nền ad vs app, màn không có data mà vẫn đặt ad, dấu "Watch an ad" của reward, nút link ngoài có chữ "AD", nút report của app AI, thông tin paywall (giá/quyền lợi/thời hạn/trial/sale/cancel anytime), cỡ chữ trial
- **N/A**: Restore (chỉ iOS). Popup thanh toán Play + cancel sub sau khi mua: tool tự mua bằng tài khoản license test

## Phụ thuộc
- Flow lái app: dùng lại `flows/<package>.yaml` của `auto-check-event-tracking` (record-flow)
- Thông tin placement ad: checklist ads sheet đang dùng cho `/audit-fanout`

## Đã chốt (user, 04/11/2026)
1. Mọi app dùng chung một bộ rule = Đối tác + Ad_VN + Sub_VN (rule trùng giữa 2 tab ads gộp vào 1 checker)
2. Không ghi ngược vào sheet, chỉ xuất artifact
3. Mọi máy/tài khoản là license test → tool tự mua sub; Sub 5 và 9 là auto, không BLOCKED
4. Check trên bản release, ad thật → AdChoices chấm được

## Tiến độ
- Phase 1 xong: `tools/ad-policy-check/policy_source.py`, `policy_registry.py`, `policy-checkers.json` (dùng JSON thay YAML để khỏi thêm dependency), 8 test pass. Sheet live: 59 rule → 38 checker, 0 rule chưa map
- Chạy thử máy thật 04/11 (Pixel 6, Hair AI 2.9.0, `evidence_collector.py`): bắt được inter splash + native ở 2 màn Language. Đo được từ UI dump: bounds native/media/nhãn Ad/AdChoices/CTA/shimmer, overlap, thứ tự activity (splash → AdActivity → Language). Thiếu: (1) frame quá thưa (~5s/frame, theo nhịp navigator) → rule thời gian chưa chấm chắc được; (2) navigator kẹt ở onboarding → chưa tới Home/banner/reward/resume/sub; (3) ảnh chụp sau UI dump ~1s, ở Language1 ảnh lệch với dump (dump có native, ảnh không có) → phải chụp ảnh trước rồi dump ngay, lệch thì CẦN XEM; (4) chưa thử bấm ad/CTA
- Phase 2 (04/11, chạy thật Pixel 6 · Hair AI 2.9.0): bộ gom `evidence_collector.py` dùng trình lái của rc-check (`rcr.fo_flow.walk_to`, luật chung VSL template, không cần flow riêng từng app) → đi trọn splash → inter → Language 1-2 → Onboarding → Question → inter → Paywall → Home → Home/mở lại. Ghi kèm: dump + ảnh mỗi màn, video cả lượt (`screenrecord`), activity mỗi 0,5s, logcat, bấm thử CTA native (Onboarding, Question → Chrome = có xử lý). Giữ chung khóa máy với rc-check/bot + chặn khi phiên khác lái chen.
  - Bỏ hướng flow tuần tự của event-tracking: bấm ad giữa chừng làm flow lệch bước, đứng ở Language 2
  - Inter đầu tiên không bấm (bấm làm video creative dừng → nút X không hiện → hỏng phép đo 15s); từ inter thứ 2 mới bấm, sau đó BACK đóng. Nút X của creative test không có trong cây UI → đo bằng video
  - Ghi nhận cần xem: Language 2 có lúc AdMob native validator báo "1 implementation issue", logcat NPE trong `Admob.populateUnifiedNativeAdView` (setVisibility/setText trên null)
- Phase 3+4 (04/11): `policy_evidence.py` (đọc lượt), `checkers_fullscreen_resume.py`, `checkers_native_banner.py`, `checkers_reward_app_sub.py`, `policy_check_runner.py` (results.json + visual-queue.json, `--visual` gộp verdict Claude), `policy_report.py` + template → artifact. Lượt Fravix 2.9.0: 16 PASS · 0 FAIL · 2 Cần xem · 6 BLOCKED · 14 N/A. Rà FAIL giả: 2 lỗi tool đã sửa (WebView media của native bị tính là màn webview; khung native không id bị tính là nút đè ad)
  - Còn: command `/policy-check`, bấm thử inter thứ 2, lái tới banner/reward/AI result/màn tiện ích, lượt mua sub (phase 5)
- Lượt đầy đủ 04/11 (Fravix 2.9.0): thêm dò Home (`evidence_home_explorer.py`: Settings → Share/Privacy/Terms, màn nội dung, Pro → paywall), mua sub test (`evidence_sub_purchase.py`), bấm inter thứ 2 (bọc `rcr.ui_dump.dump`), bấm link Privacy trên paywall. Kết quả: 20 PASS · 1 FAIL (Privacy trên paywall mở Chrome, rule yêu cầu mở trong app) · 2 Cần xem · 1 BLOCKED (nút report AI result) · 14 N/A
- Command `/policy-check` (repo `.claude/commands/policy-check.md` + file trỏ ở `~/.claude/commands/`)
- Còn mở: lái tới màn kết quả AI (cần chọn ảnh + gen); ảnh chụp sau dump đôi khi lệch màn; huỷ sub trên Play chưa kiểm được trên máy

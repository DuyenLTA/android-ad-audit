# Phase 2: Bộ gom bằng chứng ad

## Overview
Ưu tiên: cao · Status: Todo · Lái app theo flow, mỗi lần ad xuất hiện thì chụp một "gói bằng chứng".

## Key insights
- Đã có: `device_driver`, `device_navigator`, `device_close_button`, `device_popup_windows`, logcat capture trong `audit_runner --capture`
- Checker cần thời gian ở mức trăm ms (latency inter, placeholder đầu tiên) → `uiautomator dump` chậm (~1-2s). Dùng `screenrecord` hoặc `screencap` liên tục + mốc thời gian logcat; UI dump chỉ chụp lúc màn đã đứng yên
- Không bấm đóng ad sớm, chờ hết đếm ngược (tối đa 20s)

## Gói bằng chứng (`out/<package>/<run>/evidence/<seq>-<placement>/`)
- `before.png` + `before.xml` (màn trước khi bấm)
- `frames/` ảnh chụp liên tục từ lúc bấm → ad hiện (inter/resume) hoặc vào màn → ad load (banner/native)
- `ad.png` + `ad.xml` lúc ad đang hiện
- `after.png` + `after.xml` sau khi tắt ad
- `meta.json`: placement, ad unit, activity trước/sau, mốc thời gian click/show/close, density, có WebView không
- `click.json`: kết quả bấm ad/CTA (foreground trước/sau)

## Kịch bản
1. Đi flow bình thường; logcat thấy ad load/show → mở gói bằng chứng
2. Native/banner: chụp vùng ad + dump bounds; một lần mỗi placement thì bấm CTA kiểm tra xử lý, rồi Back về
3. Inter: bấm vào vị trí đặt ad (theo flow), chụp liên tục đến khi có AdActivity, poll nút tắt, ghi giây xuất hiện
4. Resume: Home → chờ → mở bằng icon (không dùng Recent); thêm lượt đi qua permission/rate/privacy rồi quay lại
5. Hết flow → `evidence/index.json`

## Files
Tạo: `tools/ad-policy-check/evidence_collector.py`, `evidence_frames.py` (chụp liên tục), `evidence_pack.py` (ghi gói). Dùng lại `device_*.py` qua import.

## Todo
- [ ] Chụp liên tục có mốc thời gian, khớp với logcat
- [ ] Gói bằng chứng theo placement
- [ ] Lượt bấm ad/CTA một lần mỗi placement
- [ ] Lượt resume qua các màn tiện ích
- [ ] Chạy thật trên 1 app có sẵn flow

## Success criteria
1 lượt trên app thật cho ra gói bằng chứng đủ cho mọi placement có trong checklist ads.

## Risks
- Bấm trượt vào creative → nhảy sang YouTube: dùng lại logic `device_close_button`, sai thì BACK
- Native validator popup che màn (OPPO): né như trong `device_popup_windows`

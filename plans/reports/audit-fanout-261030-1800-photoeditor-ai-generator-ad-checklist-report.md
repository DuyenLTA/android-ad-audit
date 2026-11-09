# Audit checklist ads — photoeditor.ai.generator.photovideo.image

- Run: wf_2a593b3a-072 · mode: capture (máy thật, pm clear) · version_code 1 · audited_at 2026-10-30T11:00Z
- Sheet tab gid=268751493 (từ sheet, chưa có trong apps.json)

## Kết quả
- Khớp 51/52, lệch 1
  - 1. Thông số kỹ thuật 4/4
  - Facebook Client Token 1/2 (App ID lệch)
  - 2. ID ads FO 40/40
  - 4. ID ads resume 6/6
- confirmed: 1 · disputed: 0 · unresolved: 0

## Confirmed — App ID (section Facebook Client Token)
- Sheet: `ca-app-pub-4973559944609228~8688685320`
- Build (AndroidManifest.xml): `ca-app-pub-4584260126367940~3637357986`
- apk_strings (UTF-8 + UTF-16LE) trên `~/.cache/ad-checklist-diff/photoeditor.ai.generator.photovideo.image-1.apk`: không có `4973559944609228`, không có `8688685320`.
- Mọi ad unit ID trong sheet + build_ad_ids đều publisher 4584260126367940 → sheet tự mâu thuẫn ở dòng App ID. Agent gắn nhãn checklist-sai; verify đứng. Báo ra ngoài vẫn là "cần ads-team xác nhận".
- Kết luận dựa trên manifest (App ID không nạp runtime), không dựa log; grep log = 0.
- Dòng App ID nằm dưới section "Facebook Client Token" trên sheet — lỗi bố cục sheet, không đổi kết luận.

## Lượt capture
- missed_home: [] · leftover_ids: [] · new_leftover_ids: []
- empty_filters: RemoteConfigRepository, inter_ads.
- Delta: lần đầu snapshot (51 dòng mới) + App ID ở "broke".
- build_ad_ids có placeholder `ca-app-pub-0000000000000000~0000000000` và ID test 3940256099942544 — không phải App ID manifest.

## Ghi chú cách đọc
- 25 ID ads chỉ xuất hiện trong dòng dump cấu hình FO, không có load/show (tier thấp). Leftover rỗng → không có dấu hiệu ID bị thay; chỉ chưa chứng minh runtime từng tier.
- `301_onb1_o_inter` không có trong log, khớp nhờ APK.
- Resume (501–503) chưa đo runtime (không đi luồng HOME→mở lại).

## Câu hỏi chưa giải quyết
- App ID đúng là của tài khoản nào — ads-team xác nhận.

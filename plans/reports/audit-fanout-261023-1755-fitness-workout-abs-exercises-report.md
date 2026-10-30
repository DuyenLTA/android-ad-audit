# Audit fanout — fitness.workout.aitraining.abs.exercises

- Run: `wf_e6675b51-908` · mode: `capture` (pm clear + lái lại máy thật)
- Checklist: sheet gid=422709729 (chưa có trong `apps.json`), digest `47aad700f3675a65`
- Build: version_code 1 · audited_at 2026-10-23T11:03:35Z

## Kết quả
- 52/52 dòng khớp, 0 lệch, 0 dòng chưa kết luận → workflow xếp app vào `clean`
- confirmed 0 · disputed 0 · unresolved 0
- Section: 1. Thông số kỹ thuật · Facebook Client Token · 2. ID ads FO · 4. ID ads resume — mọi dòng `found: true`
- leftover_ids: rỗng; triage (không có trong build / chưa thấy trong log / APK không kiểm được / khác): rỗng
- dev_build_signals: rỗng; missed_home: rỗng

## Capture
- New user: Permission → Splash → AdActivity → Language 1.1/2.1 → Onboarding → Question → AdActivity → Main (tới Home)
- Old user: Splash → AdActivity → Question → AdActivity → Main (tới Home)
- Log: `tools/ad-checklist-diff/out/fitness.workout.aitraining.abs.exercises-capture.log`

## Lưu ý đọc kết quả
- Tool chỉ đối chiếu chiều sheet → build. Khớp hết không có nghĩa build không có ID ngoài checklist.
- Build còn nạp các ad unit test của Google (`ca-app-pub-3940256099942544/...`) bên cạnh ID prod `4584260126367940`. Có thể là mặc định của SDK; tool không kết luận.
- delta so với snapshot trước: lần audit đầu, mọi dòng là `rows_added`; broke/fixed rỗng.

## Câu hỏi chưa giải quyết
- ID test Google trong build: có cần ads-team xác nhận là mặc định của SDK, không phải ID bị gắn vào placement thật?

# Audit ad checklist — com.hairai.hairstyletryon.haircolorchanger (vc21, 2.8.0)

- Run: `wf_6e173808-eab` · mode `capture` · device `18311FDF60085N` · audited_at 2026-10-10T04:19:17Z
- Checklist: sheet tab gid `1210594131` (from sheet, not yet in `apps.json`)
- Lượt trước (`wf_f59ad8ed-8f4`) dừng vì máy cài build dev (`Config variant dev: true`); user cài lại bản release rồi chạy lại. Lượt này `dev_build_signals` rỗng.

## Kết quả

- **54/54 dòng khớp**, 0 lệch, 0 chưa kết luận → workflow trả `clean`.
- confirmed: 0 · disputed: 0 · unresolved: 0
- Lần audit đầu cho app này → `delta.rows_added` = 54 (không có snapshot cũ để so `broke/fixed`).
- Hai luồng capture đều tới Home (`missed_home` rỗng):
  - new user: Permission → Splash → inter → Language 1/2 → Onboarding → Question → inter → Billing → Main
  - old user: Splash → inter → Question → inter → Billing → Main

## ID build dùng nhưng sheet không ghi (5)

Tool chỉ đối chiếu chiều sheet → build. 5 ad unit ID dưới đây được SDK load lúc chạy (`FOR_TESTER_LOAD_AD`) nhưng không có dòng nào trong checklist:

| Ad unit ID | Loại | Kết quả load lúc chạy |
|---|---|---|
| `ca-app-pub-4584260126367940/2910260367` | Native | No fill |
| `ca-app-pub-4584260126367940/6136841893` | Native | No fill |
| `ca-app-pub-4584260126367940/4031770345` | Interstitial | No fill, sau đó load thành công |
| `ca-app-pub-4584260126367940/6466361999` | Interstitial | load thành công |
| `ca-app-pub-4584260126367940/4087610665` | Interstitial | No fill |

Bằng chứng chỉ cho thấy build gọi các ID này; không nói checklist thiếu hay build dùng sai. Cần ads-team xác nhận các ID này có thuộc placement nào trong checklist không (vd. ID high-floor / dự phòng chưa được ghi).

## Lưu ý đọc kết quả

- `empty_filters` = `RemoteConfigRepository`, `inter_ads`: hai vùng log này không có dòng nào trong lượt capture. Kết luận dựa trên `FOR_TESTER_*` + quét APK.
- `pm clear` đã chạy ở cả hai lượt → dữ liệu app trên máy đã bị xoá.

## Câu hỏi chưa giải quyết

- 5 ID ngoài checklist ở trên thuộc placement nào — cần ads-team trả lời.

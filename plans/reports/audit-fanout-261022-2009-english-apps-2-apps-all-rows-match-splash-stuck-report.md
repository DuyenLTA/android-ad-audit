# Audit fan-out — 2 app English (lượt nhiều app)

- Run: `wf_cf90de3f-e76` · mode: capture (`pm clear`, luồng new + old, capture lần lượt trên 1 máy)
- Ngày: 2026-10-22 · cả 2 app lấy checklist từ sheet, chưa có trong `apps.json`

| Package | vc | Khớp | confirmed/disputed/unresolved | Tới Home |
|---|---|---|---|---|
| com.aienglishspeaking.ailanguagetutor.aienglishlearning.aitutor (gid=837344454) | 6 | 54/54 | 0/0/0 | Không |
| learnenglish.language.learningvocabulary.practice (gid=1919567600) | 2 | 56/56 | 0/0/0 | Không |

## com.aienglishspeaking.ailanguagetutor.aienglishlearning.aitutor
- Thông số kỹ thuật 8/8 · ID ads FO 40/40 · ID ads resume 6/6
- 0 dòng chưa kết luận → clean, không cần agent phán
- Delta: không dòng hỏng/sửa, không ID mới ngoài sheet. Snapshot ghi 8 mục `extra`

## learnenglish.language.learningvocabulary.practice
- Thông số kỹ thuật 8/8 · ID ads FO 40/40 · ID ads inapp 2/2 · ID ads resume 6/6
- 0 dòng chưa kết luận → clean
- Delta: không dòng hỏng/sửa, không ID mới ngoài sheet. Snapshot ghi 8 mục `extra`

## Cảnh báo capture (cả 2 app)
- Cả luồng new và old đều kẹt ở SplashActivity ("hết cách thử, dừng sớm"), không tới Home
- Khớp đủ vì ID thấy được trong bản cài/log khởi động; placement chỉ load sau Home chưa được quan sát lúc chạy → khớp = "ID có trong bản cài", chưa phải "load đúng vị trí"
- Đây là app thứ 3 liên tiếp trong ngày kẹt ở Splash (cùng aihomedecor vc9) → nghi driver capture có vấn đề chung, không riêng app
- `dev_build_signals` = 0 cả 2 app

## Ghi chú
- Tool chỉ đối chiếu chiều sheet → build; khớp hết không có nghĩa bản cài không còn ID ngoài checklist

## Câu hỏi chưa giải quyết
- Vì sao driver kẹt ở SplashActivity ở cả 3 app hôm nay — đổi UI splash chung (template), hay driver/`home_match` mặc định đã lỗi thời? Cần `/record-flow` hoặc debug driver

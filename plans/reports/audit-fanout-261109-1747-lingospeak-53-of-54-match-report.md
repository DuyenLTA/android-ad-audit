# Audit-fanout · lingospeak.english.learnlanguage.speak (LingoSpeak 2.1.0, versionCode 11)

- Máy: 3454184009000HI (vivo V2143). Chế độ: capture (pm clear), force. Run: wf_27d65baa-9a9
- Kết quả: 53/54 khớp. confirmed 0 · disputed 0 · unresolved 1. Đi tới Home cả user mới / user cũ.
- Unresolved: Adjust config environment = production. Log không in environment (filter setupAdjust/AdSdkAdjust rỗng), Adjust có chạy (tracking_install_adjust, tracker Organic). Không quét được chuỗi trong APK.
- Lượt trước (wf_15caeec3-14a) hỏng: bản script cũ không truyền --serial, adb báo "more than one device". Không dùng kết quả lượt đó.

## Câu hỏi chưa giải quyết
- Adjust environment production: cần dev xác nhận.

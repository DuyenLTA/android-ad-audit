# Một lượt fan-out tốn thời gian ở đâu

Đo ngày 2026-09-11, app `ai.photogenerator.aivideo.aivideogenerator.aiart`,
máy `99261FFAZ0077C`, APK 50,5MB / log 2,7MB.

## Phần đối chiếu: không đáng kể

| Việc | Thời gian |
|---|---|
| `apk_ad_ids` — quét toàn bộ APK, ra 78 ID | 0,36s |
| `load_trusted_lines` — 7 filter trên log 2,7MB → 715 dòng | 0,02s |
| 4 hàm `extract_*` | 0,00s |
| **Tổng** | **~0,4s** |

Trực giác "chỉ map với checklist thôi mà sao lâu" là đúng. Phần diff không chậm.

## Chỗ thật sự tốn: lớp agent

| Lượt | Thời gian | Token |
|---|---|---|
| `wf_8f6c22cc-5a6` (judge + verify, 1 finding) | 13 phút | 149k |
| `wf_3e37692f-ce4` (rerun `--skip`) | 7 phút | 155k |

Nguyên nhân: prompt bảo agent tự mở APK quét bằng zipfile. Mỗi agent viết lại
vòng quét đó, quét đi quét lại file 50MB, 34 tool call.

**Đã sửa** (`b4ca754`): triage mang sẵn `build_ad_ids`; `apk_strings.py` trả lời
mọi chuỗi khác trong 0,6s, quét cả UTF-8 lẫn UTF-16LE. Lệnh đó tái lập đúng ba
kết luận mà hai lượt agent trên tốn nhiều phút để chứng minh.

## Capture: đã sát sàn, đừng tối ưu nữa

Giả thuyết ban đầu: `POLL_SECONDS = 2` làm driver phát hiện đổi màn trễ.
Đã thử tách thành poll 0,5s / settle 2s rồi chạy A/B thật trên cùng máy, cùng app:

| | Thời gian | Tới Home |
|---|---|---|
| poll 0,5s | 118,9s | cả hai luồng |
| poll 2s (nguyên bản) | 120,6s | cả hai luồng |

Chênh 1,7s — nhiễu. **Đã revert**, giữ nguyên `POLL_SECONDS = 2`.

Driver không chờ vòng poll, nó chờ chính app dựng màn. 120s phân rã thành:

- ~48s: 16 lần tra node × ~3,7s cho `uiautomator dump`
- 24s: dwell 12s × 2 luồng (cố ý — placement ở Home cần thời gian request)
- 32s: settle 2s sau mỗi hành động
- 10s: các bước `wait` khai trong rule
- còn lại: `pm clear`, splash, dựng màn

Đã thử ba cách dump, không cách nào nhanh hơn:

| Cách | Thời gian |
|---|---|
| `dump /sdcard` + `cat` (hiện tại) | 3,73s |
| `exec-out uiautomator dump /dev/tty` | 3,96s |
| `--compressed` | 4,02s |

Chi phí đó là của `uiautomator`, không phải của cách gọi.

## Kết luận

Muốn một lượt nhanh hơn thì cắt ở lớp agent, không phải lớp máy.

**Cập nhật 2026-09-13:** đòn bẩy còn lại ở lớp máy đã dùng. Luồng không tới được
Home giờ dừng sớm thay vì đốt trọn 300s. Chỗ từng kẹt — phân biệt "đang chờ
countdown" với "đã kẹt" — hoá ra không cần đoán: màn chờ countdown là màn có
`repeat_from`, tức nó vẫn liên tục thực hiện step, nên nó không bao giờ rơi vào
trạng thái rỗi. Chỉ màn không khớp rule nào, hoặc đã hết step và không có
`repeat_from`, mới đếm rỗi; đủ `STUCK_POLLS = 15` (~30s) thì dừng. Timeout giữ
nguyên làm lưới chặn cuối. Kết quả trả về thêm trường `stopped`
(`home` / `stuck` / `timeout`) để bản tóm tắt nói đúng lý do thay vì gọi mọi
thất bại là timeout.

## Chưa giải quyết

- `DEFAULT_DWELL_SECONDS = 12` chưa được đo lại bao giờ; có thể thừa hoặc thiếu.
- `STUCK_POLLS = 15` chọn theo suy luận, chưa đo trên máy thật: chưa có lượt nào
  kẹt thật sự để biết 30s rỗi là đủ rộng hay đã quá rộng.

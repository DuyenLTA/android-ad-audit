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

**Cập nhật 2026-09-14 — đã đo `DEFAULT_DWELL_SECONDS`.** Máy `R83L1111AFT`
(SM_A075F, 720x1600). Chạy tới Home với `dwell=0` rồi quan sát thêm 45s, đo
offset từng dòng log tin cậy so với lúc chạm Home:

| | lượt new | lượt old |
|---|---|---|
| dòng tin cậy sau Home | 23 | 23 |
| dòng cuối cùng | +2,2s | +2,1s |
| còn dòng nào trong khoảng +4s → +45s | không | không |

Nhưng **không hạ hằng số**: cả lượt đo đều trả `No fill` trên mọi ad unit, tức
là đường về nhanh nhất một request có thể đi. Lượt nào fill thật sẽ log muộn
hơn, mà mẫu đo không có lượt nào như vậy.

Thay vào đó dwell kết thúc khi log lặng: tối thiểu 3s, lặng 4s thì thôi, trần
vẫn đúng 12s cũ nên trường hợp xấu nhất không đổi. Đo lại trên máy: **7,0s và
6,5s** thay cho 12s+12s.

Phân rã một lượt điều hướng (lượt new, 86,8s tới Home, đo từng lời gọi adb):

| hạng mục | giây | lần | tb |
|---|---|---|---|
| sleep (poll 2s + wait khai báo + dwell) | 48,0 | 19 | 2,53 |
| `uiautomator dump` | 32,4 | 12 | 2,70 |
| spam tap splash | 1,6 | 3 | 0,55 |
| `dumpsys window` | 1,6 | 19 | 0,09 |
| còn lại (tap, rm, monkey, swipe, pm clear, wm size) | 2,6 | 29 | — |

## Chưa giải quyết

- `STUCK_POLLS = 15` chọn theo suy luận, chưa đo trên máy thật: chưa có lượt nào
  kẹt thật sự để biết 30s rỗi là đủ rộng hay đã quá rộng.
- Dwell mới chưa gặp lượt nào ad **fill** thật. Ngưỡng lặng 4s đang dựa trên
  toàn mẫu `No fill`; gặp lượt fill thì phải đo lại xem 4s có còn đủ.
- 32s/lượt là sleep poll (`POLL_SECONDS = 2` x 16 vòng). Đã A/B một lần, kết quả
  118,9s vs 120,6s — nằm trong nhiễu, nên đã hoàn nguyên. Đừng thử lại nếu
  không có cách đo tách bạch hơn.

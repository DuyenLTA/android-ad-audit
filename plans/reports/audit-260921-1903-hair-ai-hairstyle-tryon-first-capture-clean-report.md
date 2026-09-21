# Audit ads — com.hairai.hairstyletryon.haircolorchanger

- Lượt chạy: `wf_22e3fa53-5df` · chế độ `capture` · 2026-09-21T12:06:38Z
- Máy: `29301FDH2006K7` · versionCode build: **19**
- Checklist: sheet gid `1210594131` (chưa có trong `apps.json`, phân giải từ sheet)
- Digest checklist: `8a19b5ce0bd43bb1`

## Kết quả

**54/54 dòng khớp. 0 dòng lệch.** Không có dòng nào chưa kết luận được.

| Mục checklist | Khớp |
|---|---|
| 1. Thông số kỹ thuật | 8/8 |
| 2. ID ads FO | 40/40 |
| 4. ID ads resume | 6/6 |

Triage rỗng cả bốn nhóm: `không có trong build` 0 · `chưa thấy trong log` 0 ·
`APK không kiểm được (ID nạp lúc chạy)` 0 · `khác` 0.

Ba nhóm phán của workflow: `confirmed` 0 · `disputed` 0 · `unresolved` 0 →
app nằm trong `clean`.

## Delta

Lượt audit **đầu tiên** của app này — trước đó không có snapshot nào trong repo.
Nên `rows_added` = 54, `rows_removed` = 0, `broke` = 0, `fixed` = 0. Không có
baseline để so; các lượt sau mới có delta thực nghĩa.

## Điểm cần ads-team xác nhận

**5 ad unit ID chạy trong build nhưng không có dòng nào trong checklist:**

```
ca-app-pub-4584260126367940/2910260367
ca-app-pub-4584260126367940/4031770345
ca-app-pub-4584260126367940/4087610665
ca-app-pub-4584260126367940/6136841893
ca-app-pub-4584260126367940/6466361999
```

Tool chỉ đối chiếu chiều **sheet → build**: mọi ID sheet khai đều tìm thấy trong
log, nhưng chiều ngược lại không được chấm. 54/54 khớp **không** có nghĩa là
build không chạy ID nào ngoài checklist — 5 ID trên là bằng chứng ngược lại.
Cùng publisher ID (`4584260126367940`) nên nhiều khả năng là ID hợp lệ chưa được
thêm vào sheet, nhưng đó là việc ads-team xác nhận, không phải tool kết luận.

## Cảnh báo lượt capture

- `empty_filters`: `RemoteConfigRepository`, `inter_ads` — hai bộ lọc này không
  bắt được dòng log nào. Không làm hỏng kết quả (mọi ID sheet khai đều đã tìm
  thấy qua lọc khác), nhưng nghĩa là lượt này không quan sát được remote-config
  lúc chạy qua đường đó.
- `missed_home`: rỗng — capture đi tới được màn home, không sót luồng.
- `dev_build_signals`: rỗng — không thấy dấu hiệu build dev.

## Ghi chú lượt chạy

Hai lượt trước cùng phiên không ra kết quả, không phải lỗi app:

1. `wf_72d390e2-47c` (`skip`) — app chưa từng audit, không có snapshot trên đĩa
   để xử lý. `skip` luôn rỗng với app mới.
2. `wf_bcb1a71b-496` (`apk`) — chập mạng khi tải sheet
   (`RemoteDisconnected`, `checklist_source.py:63`). Thử lại tay ngay sau đó tải
   được bình thường, 54 dòng. Lỗi nhất thời.

## Câu hỏi chưa giải quyết

- 5 ID leftover ở trên là ID hợp lệ chưa khai sheet, hay ID không nên chạy?
- Có nên ghi app vào `apps.json` với `gid=1210594131` để khỏi tra sheet mỗi lượt?
- `RemoteConfigRepository` / `inter_ads` rỗng là do app đổi tên log, hay do lượt
  capture không chạm luồng inter? Cần một lượt nữa để biết là kinh niên hay cá biệt.

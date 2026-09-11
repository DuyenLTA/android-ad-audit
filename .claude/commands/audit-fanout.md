---
description: Audit checklist quảng cáo cho app trong registry, rồi xuất báo cáo artifact
argument-hint: "[tên app hoặc package] [--skip|--apk] [--force]"
---

Chạy workflow `audit-fanout` rồi xuất báo cáo. Tham số người dùng đưa vào: $ARGUMENTS

## 1. Đọc registry

Đọc `tools/ad-checklist-diff/apps.json`. Mỗi entry có `label`, `package`, `gid`.

Nếu `$ARGUMENTS` có nêu tên app hoặc package thì chỉ lấy app đó (khớp `label`
không phân biệt hoa thường, hoặc khớp `package`); không nêu thì lấy hết.
Không tìm ra app nào khớp thì dừng và liệt kê các app có trong registry — đừng
đoán, và đừng chạy hết cả registry thay thế.

## 2. Gọi workflow

Gọi Workflow tool với `name: "audit-fanout"` và args:

- `apps`: danh sách package lấy ở bước 1. Bắt buộc, không bao giờ để rỗng.
- `audit`: `"capture"` mặc định · `"apk"` nếu có cờ `--apk` · `"skip"` nếu có cờ `--skip`
- `force`: `true` nếu có cờ `--force`

Mặc định `capture` sẽ lái máy thật và chạy `pm clear` trên app — đó là chế độ
hoạt động bình thường của tool, không phải thao tác nguy hiểm, cứ chạy. Có nói
trong lời báo là đã capture lại, đừng dừng lại hỏi chọn chế độ.

Workflow chỉ nhận diện được khi phiên mở tại thư mục gốc repo. Nếu không thấy
tên, kiểm tra CWD trước khi tìm đường khác.

## 3. Xuất báo cáo artifact

Với mỗi app vừa chạy:

1. Viết mảnh HTML phần điều tra vào `out/<package>-findings.html` và phần ghi
   chú + câu hỏi chưa giải quyết vào `out/<package>-notes.html`, dựa trên
   `confirmed` / `disputed` mà workflow trả về. Chỉ viết những gì agent thật sự
   chứng minh được, kèm trích dẫn nguồn (tên file + chuỗi tìm thấy/không thấy).
   Không có finding nào thì bỏ qua hai file này.
2. Dựng trang:

   ```
   .venv/bin/python tools/ad-checklist-diff/artifact_report_builder.py <package> \
     --findings out/<package>-findings.html \
     --notes    out/<package>-notes.html \
     --highlight <đuôi ID mà phần điều tra có giải thích>
   ```

3. Publish `out/<package>-artifact.html` bằng Artifact tool. App nào đã có
   artifact từ lượt trước thì truyền `url` của nó để giữ nguyên link, đừng tạo
   trang mới.

Trang phải mở đầu bằng thống kê khớp/lệch rồi mới tới phần điều tra — builder
lo sẵn phần đó. Một báo cáo mở đầu bằng đúng một dòng lệch đọc như tool chỉ tìm
được một dòng, chứ không phải 71/72 khớp.

## 4. Commit

Ghi báo cáo markdown vào `plans/reports/`, commit theo conventional commits, và
push lên remote `duyen` (`origin` là repo khác, không có quyền push).
`snapshots/` và `out/` nằm trong `.gitignore` — không cố thêm chúng vào.

## Báo lại

Nói rõ: bao nhiêu dòng khớp / lệch mỗi app, dòng nào `disputed` (cần người xem
lại), link artifact. Bằng chứng chỉ chứng minh sheet và bản cài lệch nhau —
không tự nó nói bên nào sai, nên phát biểu theo hướng "cần ads-team xác nhận"
thay vì khẳng định checklist sai.

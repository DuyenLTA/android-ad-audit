---
description: Audit checklist quảng cáo cho app trong registry, rồi xuất báo cáo artifact
argument-hint: "[tên app hoặc package] [--skip|--apk] [--force]"
---

Chạy workflow `audit-fanout` rồi xuất báo cáo. Tham số người dùng đưa vào: $ARGUMENTS

## 0. Tìm repo root trước đã

Command này chạy được từ thư mục bất kỳ, nên **đừng giả định CWD**. Tìm repo
theo thứ tự, lấy cái đầu tiên có `tools/ad-checklist-diff/audit_runner.py`:

1. `git rev-parse --show-toplevel` (nếu CWD đang nằm trong chính repo này)
2. biến môi trường `$AD_AUDIT_REPO`
3. `~/android-ad-audit`

Không thấy thì dừng, nói rõ đã tìm ở đâu. Gọi đường dẫn tìm được là `<repo>`.

Từ đây trở đi mọi lệnh bash đều mở đầu bằng `cd <repo> && …`, và mọi đường dẫn
truyền cho agent đều là **tuyệt đối**. Agent không thừa hưởng CWD của phiên
gọi — đường dẫn tương đối là cách chắc chắn nhất để nó đọc nhầm file.

## 1. Đọc registry

Không nêu tên app trong `$ARGUMENTS` thì lấy hết registry:
`<repo>/tools/ad-checklist-diff/apps.json`.

Có nêu tên thì **đừng tự so chuỗi** — chạy, theo thứ tự này:

```
cd <repo> && .venv/bin/python tools/ad-checklist-diff/find_app.py "<tên>"
cd <repo> && .venv/bin/python tools/ad-checklist-diff/find_app.py --device "<tên>"
```

Cái đầu tra registry (tức thì). Exit 1 thì chạy cái thứ hai: nó quét **mọi app
đang cài trên máy** và khớp theo tên hiện trên icon — lần đầu ~15 giây cho cả
máy, sau đó có cache nên vài giây.

Người ta gõ cái họ nhìn thấy: "Nexus", không phải nickname nội bộ "AI Art", càng
không phải package id.

Thêm `--add` vào lệnh thứ hai để app tìm được tự vào registry:

```
cd <repo> && .venv/bin/python tools/ad-checklist-diff/find_app.py --device --add "<tên>"
```

`gid` không phải hỏi: mỗi tab trong sheet có dòng `Package name` của chính nó,
nên tab nào thuộc app nào là **đọc được**, không đoán. Tên tab là mã dự án, đừng
cố khớp nó với tên app.

Dòng in ra có `gid=<số>` là xong, chạy tiếp. Hai trường hợp phải **dừng và hỏi
người dùng**, đừng tự chọn:

- `gid=? (… nhiều tab cùng khai app này)` — sheet có 2 tab cho cùng app, chọn
  bừa là đối chiếu nhầm checklist
- `gid=? (sheet không có tab nào khai package này)` — app đang cài nhưng chưa có
  checklist; không có gì để đối chiếu

Theo exit code:

- `0` — đúng một app, chạy nó
- `1` — không khớp. **Dừng**, in nguyên danh sách nó gợi ý. Đừng đoán, và tuyệt
  đối đừng chạy cả registry thay thế: lượt capture mặc định `pm clear` app, chạy
  nhầm app là xoá dữ liệu của app không liên quan
- `2` — nhiều app khớp. **Dừng**, liệt kê ra và hỏi người dùng chọn

## 2. Gọi workflow

Gọi Workflow tool với `scriptPath: "<repo>/.claude/workflows/audit-fanout.mjs"`
và args:

- `apps`: danh sách package lấy ở bước 1. Bắt buộc, không bao giờ để rỗng.
- `repoDir`: `<repo>`
- `toolDir`: `<repo>/tools/ad-checklist-diff`
- `audit`: `"capture"` mặc định · `"apk"` nếu có cờ `--apk` · `"skip"` nếu có cờ `--skip`
- `force`: `true` nếu có cờ `--force`

Dùng `scriptPath` chứ đừng dùng `name: "audit-fanout"`: tên chỉ phân giải được
khi phiên mở đúng tại repo root, còn command này chạy từ đâu cũng phải được.

Mặc định `capture` sẽ lái máy thật và chạy `pm clear` trên app — đó là chế độ
hoạt động bình thường của tool, không phải thao tác nguy hiểm, cứ chạy. Có nói
trong lời báo là đã capture lại, đừng dừng lại hỏi chọn chế độ.

## 3. Xuất báo cáo artifact

Với mỗi app vừa chạy:

1. Viết mảnh HTML phần điều tra vào `<repo>/tools/ad-checklist-diff/out/<package>-findings.html`
   và phần ghi chú + câu hỏi chưa giải quyết vào `…/out/<package>-notes.html`,
   dựa trên `confirmed` / `disputed` / `unresolved` mà workflow trả về. Chỉ viết những gì agent
   thật sự chứng minh được, kèm trích dẫn nguồn (tên file + chuỗi tìm thấy hoặc
   không thấy). Không có finding nào thì bỏ qua hai file này.
2. Dựng trang:

   ```
   cd <repo> && .venv/bin/python tools/ad-checklist-diff/artifact_report_builder.py <package> \
     --findings out/<package>-findings.html \
     --notes    out/<package>-notes.html \
     --highlight <đuôi ID mà phần điều tra có giải thích> \
     --run <run ID workflow vừa trả về> \
     --mode <capture|apk|skip — đúng chế độ vừa chạy> \
     --report plans/reports/<báo cáo bước 4>.md
   ```

   `--run`, `--mode`, `--report` bắt buộc truyền — không có chỗ nào trên đĩa ghi
   lại ba thứ đó. Đừng gõ tay chúng vào template: template dùng chung cho mọi
   app, mọi lượt. `delta` và cảnh báo capture thì builder tự đọc từ triage.

   Builder mặc định đọc `snapshots/` và ghi `out/` cạnh chính nó, nên đường dẫn
   trong lệnh trên tính từ `<repo>`.
3. Publish `<repo>/tools/ad-checklist-diff/out/<package>-artifact.html` bằng
   Artifact tool. App nào đã có artifact từ lượt trước thì truyền `url` của nó
   để giữ nguyên link, đừng tạo trang mới.

Trang phải mở đầu bằng thống kê khớp/lệch rồi mới tới phần điều tra — builder
lo sẵn phần đó. Một báo cáo mở đầu bằng đúng một dòng lệch đọc như tool chỉ tìm
được một dòng, chứ không phải 71/72 khớp.

## 4. Commit

Ghi báo cáo markdown vào `<repo>/plans/reports/`, commit theo conventional
commits, và push lên remote `duyen` (`origin` là repo khác, không có quyền
push). `snapshots/` và `out/` nằm trong `.gitignore` — không cố thêm chúng vào.

## Báo lại

Nói rõ: bao nhiêu dòng khớp / lệch mỗi app, link artifact, và ba nhóm kết quả:

- `confirmed` -- có luận điểm, đã qua phản biện, luận điểm đứng
- `disputed` -- có luận điểm, phản biện làm nó đổ. **Cần người xem lại.**
- `unresolved` -- agent tự nhận không đủ bằng chứng, chưa từng qua phản biện
  (không có gì để phản biện). Cũng cần người xem, nhưng vì lý do khác hẳn.

App nào nằm trong `clean` thì không còn dòng nào chưa kết luận -- nói thẳng là
sạch, đừng im lặng bỏ qua khiến người đọc tưởng nó bị lỗi.

Bằng chứng chỉ chứng minh sheet và bản cài lệch nhau —
không tự nó nói bên nào sai, nên phát biểu theo hướng "cần ads-team xác nhận"
thay vì khẳng định checklist sai.

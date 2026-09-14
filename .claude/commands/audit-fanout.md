---
description: Audit checklist quảng cáo cho một app theo package, rồi xuất báo cáo artifact
argument-hint: "<package> [--skip|--apk] [--force]"
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

## 1. Lấy package

Command này **chỉ nhận package id**, không nhận tên app. Khớp theo tên là khớp
mờ: gõ thiếu một ký tự thì nó trả về app hàng xóm chứ không trả về lỗi, và lượt
capture mặc định `pm clear` đúng cái app nó nhận được — sai app là xoá dữ liệu
của app không liên quan. Package id gõ sai thì phải hỏng ra mặt, đừng đoán hộ.

`$ARGUMENTS` không có chuỗi nào trông như package (`com.abc.xyz`) thì **dừng**,
in registry ra và hỏi người dùng chọn. Không nêu app thì cũng **đừng chạy cả
registry thay thế** — mỗi lượt là một app, do người dùng chỉ đích danh.

Có package thì phân giải nó — vẫn **đừng tự so chuỗi**:

```
cd <repo> && .venv/bin/python tools/ad-checklist-diff/find_app.py --exact "<package>"
```

Package **không cần có sẵn trong `apps.json`**. Registry chỉ là cache: mỗi tab
trong sheet tự khai dòng `Package name` của nó, nên tab nào thuộc app nào là đọc
được. Registry biết thì trả lời ngay, không biết thì nó hỏi sheet.

Theo exit code:

- `0` — phân giải được, chạy nó. In kèm `gid=… — từ sheet, chưa có trong
  registry` nghĩa là app chưa được ghi vào `apps.json`; vẫn chạy bình thường
- `1` — **dừng**, in nguyên văn lý do. Ba lý do khác nhau, đừng gộp:
  - *Không phải package id* — người dùng gõ tên app. Hỏi lại package
  - *Sheet không có tab nào khai package này* — chưa có checklist để đối chiếu.
    Không có gì để chạy; báo để nhờ ads-team thêm tab
  - *Sheet có 2 tab cùng khai package này* — chọn bừa là đối chiếu nhầm
    checklist. **Hỏi người dùng** tab nào đúng, rồi ghi entry vào `apps.json`
    với `gid` đó

Muốn app khỏi phải tra sheet mỗi lượt thì ghi nó vào registry một lần:

```
cd <repo> && .venv/bin/python tools/ad-checklist-diff/find_app.py --device --add "<tên trên icon>"
```

Đây là tiện ích, không phải điều kiện để chạy.

## 2. Gọi workflow

Workflow tool **chỉ nhận `scriptPath` nằm trong working directory của phiên**,
mà command này chạy từ đâu cũng được — nên trỏ thẳng vào `<repo>/.claude/...`
sẽ hỏng đúng những lượt chạy ngoài repo. Copy script ra chỗ phiên đọc được
trước đã, **luôn luôn**, đừng chờ nó báo lỗi rồi mới vòng:

```
cp <repo>/.claude/workflows/audit-fanout.mjs <scratchpad>/audit-fanout.mjs
```

`<scratchpad>` là thư mục scratchpad của phiên (system prompt có nêu). Copy
không đổi hành vi gì: `repoDir` và `toolDir` truyền vào là đường dẫn tuyệt đối,
nên script chạy ở đâu cũng đọc đúng repo.

Rồi gọi Workflow tool với `scriptPath: "<scratchpad>/audit-fanout.mjs"` và args:

- `apps`: danh sách package lấy ở bước 1. Bắt buộc, không bao giờ để rỗng.
- `repoDir`: `<repo>`
- `toolDir`: `<repo>/tools/ad-checklist-diff`
- `audit`: `"capture"` mặc định · `"apk"` nếu có cờ `--apk` · `"skip"` nếu có cờ `--skip`
- `force`: `true` nếu có cờ `--force`

Đừng dùng `name: "audit-fanout"`: tên chỉ phân giải được khi phiên mở đúng tại
repo root. Cũng đừng đọc file rồi truyền vào `script` — script dài vài trăm dòng,
lượt nào cũng nhét nguyên nó vào hội thoại là tốn vô ích.

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
     --findings tools/ad-checklist-diff/out/<package>-findings.html \
     --notes    tools/ad-checklist-diff/out/<package>-notes.html \
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
3. Trước khi publish, hỏi xem app này đã có trang chưa:

   ```
   cd <repo> && .venv/bin/python tools/ad-checklist-diff/artifact_link.py \
     --package <package> --show
   ```

   Có link thì truyền vào `url` khi publish để giữ nguyên trang — người ta đã
   chia sẻ link đó rồi, tạo trang mới là link cũ lặng lẽ thành bản cũ. Chưa có
   thì publish mới.

4. Publish `<repo>/tools/ad-checklist-diff/out/<package>-artifact.html` bằng
   Artifact tool, rồi ghi lại link — **bước này bắt buộc, không phải tuỳ chọn**:

   ```
   cd <repo> && .venv/bin/python tools/ad-checklist-diff/artifact_link.py \
     --package <package> <url vừa publish>
   ```

   Ghi link là **tự mở trình duyệt**, không cần cờ gì thêm: lượt chạy nào xong
   cũng phải bật trang lên cho người dùng xem, nên đó là mặc định chứ không phải
   thứ để nhớ bật. Máy không có màn hình thì nó báo ra stderr và vẫn lưu link —
   không coi đó là lỗi của lượt chạy. (`--no-open` chỉ dùng khi người dùng bảo
   đừng mở.)

   Vẫn in URL ra trong lời báo: browser có thể không mở được, và người ta còn
   cần link để gửi cho ads-team.

Trang phải mở đầu bằng thống kê khớp/lệch rồi mới tới phần điều tra — builder
lo sẵn phần đó. Một báo cáo mở đầu bằng đúng một dòng lệch đọc như tool chỉ tìm
được một dòng, chứ không phải 71/72 khớp.

## 4. Báo cáo markdown

Ghi báo cáo vào `<repo>/plans/reports/` — đây là file mà bước 3 truyền vào
`--report`, nên viết nó trước khi dựng trang.

**Dừng ở đây. Không `git add`, không `git commit`, không `git push`.** Lượt audit
chỉ sinh ra file; đưa file nào vào lịch sử git là việc của người dùng, không
phải của command. Muốn commit thì người dùng sẽ tự nói.

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

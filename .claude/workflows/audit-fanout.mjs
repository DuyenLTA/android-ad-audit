export const meta = {
  name: 'audit-fanout',
  description: 'One agent per app: judge the rows the audit could not settle, verify each claim, write a report',
  phases: [
    { title: 'Audit', detail: 'chạy audit_runner.py để có triage mới' },
    { title: 'Judge', detail: 'một agent mỗi app, phán các dòng triage' },
    { title: 'Verify', detail: 'phản biện từng kết luận' },
  ],
}

// Consumes what `audit_runner.py` already decided mechanically. The deterministic
// pass settles every row it can from the log and the APK; only two kinds of row
// reach an agent:
//   - "không có trong build": the checklist ID is absent from the installed APK
//   - "chưa thấy trong log": nothing in the capture speaks to this row
// Everything else is already Khớp/Lệch with evidence and needs no judgement.
//
// Lives in .claude/workflows/ so it can be run by name: `chạy workflow
// audit-fanout` from a session opened at the repo root.
//
// `apps` has to be passed in -- a workflow script cannot read apps.json itself
// (no filesystem in here), so the calling session reads the registry and hands
// the packages over:
//   args: { apps: ['com.example.app'], audit: 'capture' }
// `toolDir` only needs passing when the tool is not where it normally sits.
//
// `audit` picks what the first phase does:
//   'capture' (default) -- drive the phone, then audit against that log
//   'apk'               -- audit from the APK only, no device driving
//   'skip'              -- judge whatever triage is already on disk
// `force: true` re-audits a build already audited; without it the runner skips
// an unchanged versionCode and the triage on disk still stands, which is the
// point of the snapshot -- same build, same answer, no reason to drive the
// phone again.
// The audit runs here rather than being a separate thing to remember, because a
// triage nobody refreshed is the failure this whole tool exists to avoid: an
// APK-only triage carries "chưa thấy trong log" rows that are artefacts of not
// capturing, and agents handed those rows argue about bugs that do not exist.

const toolDir = args?.toolDir ?? 'tools/ad-checklist-diff'
// Agents do not inherit the calling session's CWD, so a run started from
// anywhere but the repo root has to be told where the repo is. Default '.'
// keeps a session opened at the root behaving exactly as before.
const repoDir = args?.repoDir ?? '.'
const apps = args?.apps ?? []
const auditMode = args?.audit ?? 'capture'
const force = args?.force === true

if (apps.length === 0) {
  // Without this the pipeline quietly runs over nothing and returns an empty
  // report, which reads like "no findings" rather than "you gave me no apps".
  throw new Error(
    'Chưa có app nào: truyền args.apps, ví dụ { apps: ["com.example.app"] }. ' +
    'Danh sách package nằm ở ' + toolDir + '/apps.json.',
  )
}

const AUDIT_SCHEMA = {
  type: 'object',
  properties: {
    command: { type: 'string' },
    exit_code: { type: 'number' },
    output: { type: 'string' },
  },
  required: ['command', 'exit_code', 'output'],
}

const FINDINGS_SCHEMA = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          value: { type: 'string' },
          label: { type: 'string' },
          verdict: {
            type: 'string',
            enum: ['checklist-sai', 'build-thieu', 'chua-capture-du', 'khong-ket-luan-duoc'],
          },
          evidence: { type: 'string' },
          suggested_id: { type: 'string' },
        },
        required: ['value', 'verdict', 'evidence'],
      },
    },
  },
  required: ['findings'],
}

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    holds: { type: 'boolean' },
    why: { type: 'string' },
  },
  required: ['holds', 'why'],
}

const judge = (pkg) => agent(
  `Đọc ${toolDir}/out/${pkg}-triage.json và ${toolDir}/snapshots/${pkg}.json
(đường dẫn tính từ thư mục gốc của repo).

Với MỖI dòng trong triage (chỉ những dòng này, không xét dòng đã Khớp), kết luận:
- checklist-sai: ID trong sheet không tồn tại trong build, và log cho thấy build dùng ID khác
- build-thieu: placement không có trong build (tên placement cũng không xuất hiện)
- chua-capture-du: dòng này cần luồng/màn chưa được capture
- khong-ket-luan-duoc: không đủ bằng chứng

Cách kiểm chứng, dùng đúng các nguồn này, KHÔNG đoán:
- APK đang cache: ~/.cache/ad-checklist-diff/${pkg}-*.apk
  (tìm chuỗi bằng python zipfile, quét entry .dex/.arsc)
- Nếu tên placement không xuất hiện trong dex thì đó là build-thieu, không phải sai ID
- Log của lượt capture gần nhất: ${toolDir}/out/${pkg}-capture.log -- tìm cặp
  key=<high_id>_<normal_id>: nửa kia của cặp đã khớp checklist thì nửa còn lại
  chính là ID build đang dùng cho dòng twin
Mỗi finding phải kèm evidence trích dẫn được (tên file + chuỗi tìm thấy/không thấy).

TRƯỚC KHI PHÁN, đọc phần đầu triage để biết lượt capture sinh ra nó đi tới đâu.
Nó quyết định kết luận nào còn đứng được:
- missed_home không rỗng: các luồng đó chưa tới Home, nên dòng nào phụ thuộc màn
  sau Home thì phải là chua-capture-du, KHÔNG được kết luận checklist-sai hay
  build-thieu chỉ vì log im lặng.
- missed_home là null: lượt đó không capture gì cả (chỉ đọc APK), nên MỌI kết
  luận dựa trên "log không có" đều vô giá trị. Log trên đĩa là của lượt trước,
  có thể khác build.
- empty_filters không rỗng: cả vùng đó không có dòng log nào, xử như trên.
- version_code trong triage khác version_code trong snapshot, hoặc audited_at đã
  cũ: nói rõ trong evidence rằng đang phán trên ảnh chụp cũ.
- triage không có các trường trên: file sinh từ bản tool cũ, chưa ghi bối cảnh.
  Xử như không biết gì về lượt capture, và nói rõ điều đó trong evidence.
Vắng mặt trong log KHÔNG BAO GIỜ tự nó là bằng chứng, chỉ vắng mặt trong APK mới
là bằng chứng. Thiếu bối cảnh thì trả khong-ket-luan-duoc, đừng đoán bù.`,
  { label: `judge:${pkg}`, phase: 'Judge', schema: FINDINGS_SCHEMA },
)

const verify = (pkg, f) => agent(
  `Phản biện kết luận sau về app ${pkg}, dòng checklist "${f.value}".
Kết luận: ${f.verdict}. Bằng chứng đưa ra: ${f.evidence}

Tự kiểm lại từ APK/log. Trả holds=false nếu bằng chứng không đứng vững hoặc
có cách giải thích khác hợp lý hơn. Đừng xác nhận chỉ vì nghe hợp lý.`,
  { label: `verify:${pkg}:${f.value}`, phase: 'Verify', schema: VERDICT_SCHEMA },
)

if (auditMode !== 'skip') {
  phase('Audit')
  const flags = (auditMode === 'capture' ? ' --capture' : '') + (force ? ' --force' : '')
  // Deliberately one agent running one command: the verdicts stay Python's, and
  // an agent that starts improvising flags is an agent rewriting the audit.
  const audit = await agent(
    `Chạy đúng một lệnh này, không thêm bớt cờ nào, không đổi thư mục nào khác:

    cd ${repoDir} && .venv/bin/python ${toolDir}/audit_runner.py${flags}

Nó có thể lái máy thật và mất vài phút -- chờ cho xong, đừng bỏ ngang, đừng
chạy lại. Báo "build chưa đổi" là ĐÚNG, không phải lỗi: triage cũ vẫn dùng được
vì cùng build thì cùng kết quả.
Nếu lệnh lỗi thì BÁO LẠI nguyên văn, KHÔNG tự sửa lệnh và chạy lại.
Trả về: command đã chạy, exit code, và toàn bộ output nó in ra.`,
    { label: 'audit', phase: 'Audit', schema: AUDIT_SCHEMA },
  )
  if (!audit || audit.exit_code === 1) {
    // exit 1 is the runner failing outright; exit 2 just means rows are still
    // mismatched, which is the normal case the agents exist to explain.
    throw new Error(
      `audit_runner.py không chạy được, dừng trước khi agent phán trên triage cũ:\n` +
      (audit ? audit.output : '(agent không trả về gì)'),
    )
  }
  log(`Audit xong (exit ${audit.exit_code}). Sang phần phán các dòng chưa kết luận được.`)
}

const results = await pipeline(
  apps,
  (pkg) => judge(pkg).then((r) => ({ pkg, findings: r.findings ?? [] })),
  ({ pkg, findings }) =>
    parallel(
      findings.map((f) => () => verify(pkg, f).then((v) => ({ pkg, ...f, verify: v }))),
    ),
)

const all = results.flat().filter(Boolean)
return {
  confirmed: all.filter((f) => f.verify?.holds),
  disputed: all.filter((f) => !f.verify?.holds),
}

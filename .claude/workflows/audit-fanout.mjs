export const meta = {
  name: 'audit-fanout',
  description: 'One agent per app: judge the rows the audit could not settle, verify each claim, write a report',
  phases: [
    { title: 'Audit', detail: 'chạy audit_runner.py để có triage mới', effort: 'low' },
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
    // Bản tóm tắt đã in sẵn con số này cho từng app; đọc lại ở đây rẻ hơn nhiều
    // so với việc mở một agent chỉ để biết app đó có việc gì cho agent không.
    apps: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          package: { type: 'string' },
          unsettled: { type: 'number' },
        },
        required: ['package', 'unsettled'],
      },
    },
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

// Judge and verify ask the same questions of the same files, so they get the
// same briefing. Verify used to get only the finding text -- no paths, no tool
// names -- and spent its first third of an hour of wall clock rediscovering the
// repo with `ls -R` and `find`, reading the tools' source to learn what they do,
// and finally writing its own zipfile sweep in /tmp. That sweep is exactly what
// apk_strings.py was built to replace.
const sources = (pkg) => `Nguồn, dùng đúng các file này, KHÔNG đoán và KHÔNG đi tìm:
- triage:  ${toolDir}/out/${pkg}-triage.json
- log capture: ${toolDir}/out/${pkg}-capture.log
  CẢNH BÁO: adb logcat bắt cả máy, không lọc theo app. App khác đã bị dừng trước
  khi capture, nhưng FA-SVC (Firebase Analytics, nằm trong Play Services) vẫn
  upload theo lô những event nó gom từ TRƯỚC đó, và lô đó có thể của app khác.
  Mỗi lô mang dòng "app_id: <package>" của chính nó. Dòng FA-SVC nào thuộc lô có
  app_id KHÁC ${pkg} thì KHÔNG phải bằng chứng về build này -- đã có lượt kết
  luận sai vì lấy ad unit ID của app anh em làm "ID đang chạy mà vắng APK".
  Bằng chứng runtime đáng tin nằm ở FOR_TESTER_* và inter_ads.
- snapshot (file lớn, chỉ mở phần cần): ${toolDir}/snapshots/${pkg}.json

- "ID này có trong bản cài không": tra thẳng mảng build_ad_ids trong triage --
  đó là toàn bộ ad unit ID tool đã quét được từ APK. ĐỪNG tự mở APK ra quét lại.
  build_ad_ids là null thì mới cần tự kiểm.
- Chuỗi khác (token, tên placement, tên cờ), chạy đúng một lệnh, đừng tự viết
  zipfile, đừng đọc source của tool để hiểu nó làm gì:

    cd ${repoDir} && .venv/bin/python ${toolDir}/apk_strings.py --package ${pkg} <chuỗi> <chuỗi>

  \`--package\` là CỜ, không phải positional: mọi tham số không có cờ đều bị coi
  là chuỗi cần tìm. Nó quét cả UTF-8 lẫn UTF-16LE trong mọi entry, xong trong
  dưới một giây, và in ra entry chứa chuỗi đó. Tự viết vòng quét tay vừa chậm
  vừa hay sót UTF-16LE -- sót là báo nhầm "không có trong build" cho chuỗi thật
  sự có.`

// Vắng mặt trong log KHÔNG BAO GIỜ tự nó là bằng chứng, và điều đó đúng với cả
// agent phán lẫn agent phản biện -- nên bối cảnh lượt capture cũng dùng chung.
const captureContext = `TRƯỚC KHI KẾT LUẬN, đọc phần đầu triage để biết lượt capture sinh ra nó đi tới đâu:
- missed_home không rỗng: các luồng đó chưa tới Home, nên dòng nào phụ thuộc màn
  sau Home thì chưa kết luận được từ việc log im lặng.
- missed_home là null: lượt đó không capture gì cả (chỉ đọc APK), nên MỌI kết
  luận dựa trên "log không có" đều vô giá trị. Log trên đĩa là của lượt trước.
- empty_filters không rỗng: cả vùng log đó không có dòng nào, xử như trên.
- version_code trong triage khác trong snapshot, hoặc audited_at đã cũ: nói rõ
  là đang phán trên ảnh chụp cũ.
- triage không có các trường trên: file sinh từ bản tool cũ. Xử như không biết gì
  về lượt capture, và nói rõ điều đó.
Vắng mặt trong log KHÔNG BAO GIỜ tự nó là bằng chứng, chỉ vắng mặt trong APK mới
là bằng chứng.`

const judge = (pkg) => agent(
  `Đọc ${toolDir}/out/${pkg}-triage.json trước -- nó có đủ dòng cần phán, kèm
build_ad_ids, missed_home, empty_filters.
${toolDir}/snapshots/${pkg}.json là file lớn: CHỈ mở khi thật sự cần đối chiếu
dòng anh em (twin) hoặc danh sách leftover_ids, và khi mở thì chỉ đọc phần cần.

Với MỖI dòng trong triage (chỉ những dòng này, không xét dòng đã Khớp), kết luận:
- checklist-sai: ID trong sheet không tồn tại trong build, và log cho thấy build dùng ID khác
- build-thieu: placement không có trong build (tên placement cũng không xuất hiện)
- chua-capture-du: dòng này cần luồng/màn chưa được capture
- khong-ket-luan-duoc: không đủ bằng chứng

${sources(pkg)}
- Nếu tên placement không xuất hiện trong APK thì đó là build-thieu, không phải sai ID
- Trong log tìm cặp key=<high_id>_<normal_id>: nửa kia của cặp đã khớp checklist
  thì nửa còn lại chính là ID build đang dùng cho dòng twin
Mỗi finding phải kèm evidence trích dẫn được (tên file + chuỗi tìm thấy/không thấy).

${captureContext}
Thiếu bối cảnh thì trả khong-ket-luan-duoc, đừng đoán bù.`,
  { label: `judge:${pkg}`, phase: 'Judge', schema: FINDINGS_SCHEMA },
)

const verify = (pkg, f) => agent(
  `Phản biện kết luận sau về app ${pkg}, dòng checklist "${f.value}".
Kết luận: ${f.verdict}. Bằng chứng đưa ra: ${f.evidence}

Tự kiểm lại từ APK/log, ĐỪNG tin lời bằng chứng trên. Trả holds=false nếu bằng
chứng không đứng vững hoặc có cách giải thích khác hợp lý hơn. Đừng xác nhận chỉ
vì nghe hợp lý.

Kiểm lại độc lập nghĩa là tự chạy lại phép kiểm, KHÔNG phải tự đi tìm lại chỗ để
chạy. Mọi đường dẫn và công cụ cần dùng nằm ngay dưới đây -- đừng \`ls\`, đừng
\`find\`, đừng đọc source của tool để đoán nó làm gì.

${sources(pkg)}

${captureContext}

Nếu nhãn của kết luận sai nhưng dữ kiện đúng, holds=false và nói rõ nhãn nào mới
đúng. Nếu chỗ gãy nằm ở chính tool (một phép kiểm đáng lẽ phải chạy mà không
chạy), nói thẳng ra -- đó là phát hiện có giá trị hơn việc phán lại dòng đó.`,
  { label: `verify:${pkg}:${f.value}`, phase: 'Verify', schema: VERDICT_SCHEMA },
)

// Đọc được thì dùng để bỏ bớt agent ở dưới; không đọc được thì để rỗng, và mọi
// app đều được phán -- thiếu thông tin phải nghiêng về làm thừa, không phải bỏ sót.
let unsettled = {}

if (auditMode !== 'skip') {
  phase('Audit')
  // Every package is named on the command line. Without this the runner walks
  // the whole registry, so asking about one app drives the phone over all of
  // them -- and a capture `pm clear`s each app it visits, wiping the data of
  // apps nobody asked about.
  const only = apps.map((pkg) => ` --package ${pkg}`).join('')
  const flags = (auditMode === 'capture' ? ' --capture' : '') + (force ? ' --force' : '') + only
  // Deliberately one agent running one command: the verdicts stay Python's, and
  // an agent that starts improvising flags is an agent rewriting the audit.
  const audit = await agent(
    `Chạy đúng một lệnh này, không thêm bớt cờ nào, không đổi thư mục nào khác:

    cd ${repoDir} && .venv/bin/python ${toolDir}/audit_runner.py${flags}

Nó có thể lái máy thật và mất vài phút -- chờ cho xong, đừng bỏ ngang, đừng
chạy lại. Báo "build chưa đổi" là ĐÚNG, không phải lỗi: triage cũ vẫn dùng được
vì cùng build thì cùng kết quả.
Nếu lệnh lỗi thì BÁO LẠI nguyên văn, KHÔNG tự sửa lệnh và chạy lại.

Trả về: command đã chạy, exit code, toàn bộ output nó in ra, và trường "apps" --
mỗi app một dòng trong bản tóm tắt, kèm con số sau "chưa kết luận:" ở cuối dòng
đó. Chép đúng số đã in, đừng tự đếm lại. Dòng nào không có đoạn "chưa kết luận:"
thì BỎ app đó ra khỏi "apps", đừng đoán số 0 -- không biết thì để lớp sau xử.`,
    // Chạy đúng một lệnh rồi chép lại output -- không có gì để cân nhắc, nên
    // không trả tiền cho việc cân nhắc.
    { label: 'audit', phase: 'Audit', schema: AUDIT_SCHEMA, effort: 'low' },
  )
  if (!audit || audit.exit_code === 1) {
    // exit 1 is the runner failing outright; exit 2 just means rows are still
    // mismatched, which is the normal case the agents exist to explain.
    throw new Error(
      `audit_runner.py không chạy được, dừng trước khi agent phán trên triage cũ:\n` +
      (audit ? audit.output : '(agent không trả về gì)'),
    )
  }
  unsettled = Object.fromEntries(
    (audit.apps ?? []).map((a) => [a.package, a.unsettled]),
  )
  log(`Audit xong (exit ${audit.exit_code}). Sang phần phán các dòng chưa kết luận được.`)
}

// App không còn dòng nào chưa kết luận thì không có gì để phán. `undefined`
// nghĩa là audit không khai được con số -- lúc đó vẫn phán, vì bỏ sót một dòng
// lệch tốn kém hơn nhiều so với một agent chạy không.
const idle = apps.filter((pkg) => unsettled[pkg] === 0)
const toJudge = apps.filter((pkg) => unsettled[pkg] !== 0)

if (idle.length) {
  log(`Sạch, không cần phán: ${idle.join(', ')}`)
}
if (toJudge.length === 0) {
  log('Mọi app đều sạch -- không mở agent nào ở Judge/Verify.')
  return { confirmed: [], disputed: [], unresolved: [], clean: idle }
}

// "Không kết luận được" không có luận điểm nào để phản biện, nên nó đi thẳng ra
// ngoài thay vì tốn một agent chỉ để nghe lại đúng câu đó.
const arguable = (f) => f.verdict !== 'khong-ket-luan-duoc'

const results = await pipeline(
  toJudge,
  (pkg) => judge(pkg).then((r) => ({ pkg, findings: r.findings ?? [] })),
  ({ pkg, findings }) =>
    parallel(
      findings.map((f) => () =>
        arguable(f)
          ? verify(pkg, f).then((v) => ({ pkg, ...f, verify: v }))
          : Promise.resolve({ pkg, ...f, verify: null }),
      ),
    ),
)

const all = results.flat().filter(Boolean)
return {
  confirmed: all.filter((f) => f.verify?.holds),
  disputed: all.filter((f) => f.verify && !f.verify.holds),
  // Chưa từng qua phản biện: agent tự nhận không đủ bằng chứng. Cần người xem,
  // nhưng khác hẳn disputed -- disputed là có luận điểm và luận điểm đó đổ.
  unresolved: all.filter((f) => !f.verify),
  clean: idle,
}

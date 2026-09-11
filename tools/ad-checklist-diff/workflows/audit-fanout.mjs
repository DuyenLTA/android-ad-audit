export const meta = {
  name: 'ad-checklist-audit-fanout',
  description: 'One agent per app: judge the rows the audit could not settle, verify each claim, write a report',
  phases: [{ title: 'Judge' }, { title: 'Verify' }],
}

// Consumes what `audit_runner.py` already decided mechanically. The deterministic
// pass settles every row it can from the log and the APK; only two kinds of row
// reach an agent:
//   - "không có trong build": the checklist ID is absent from the installed APK
//   - "chưa thấy trong log": nothing in the capture speaks to this row
// Everything else is already Khớp/Lệch with evidence and needs no judgement.
//
// Run it with the triage files as args, e.g.
//   args: { toolDir: '/abs/path/tools/ad-checklist-diff', apps: ['com.example.app'] }

const toolDir = args?.toolDir ?? '.'
const apps = args?.apps ?? []

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
  `Đọc ${toolDir}/out/${pkg}-triage.json và ${toolDir}/snapshots/${pkg}.json.

Với MỖI dòng trong triage (chỉ những dòng này, không xét dòng đã Khớp), kết luận:
- checklist-sai: ID trong sheet không tồn tại trong build, và log cho thấy build dùng ID khác
- build-thieu: placement không có trong build (tên placement cũng không xuất hiện)
- chua-capture-du: dòng này cần luồng/màn chưa được capture
- khong-ket-luan-duoc: không đủ bằng chứng

Cách kiểm chứng, dùng đúng các nguồn này, KHÔNG đoán:
- APK đang cache: ${toolDir}/../../../.cache/ad-checklist-diff/${pkg}-*.apk
  (tìm chuỗi bằng python zipfile, quét entry .dex/.arsc)
- Nếu tên placement không xuất hiện trong dex thì đó là build-thieu, không phải sai ID
- Log gần nhất nếu có, để tìm cặp key=<high_id>_<normal_id>: nửa kia của cặp đã khớp
  checklist thì nửa còn lại chính là ID build đang dùng cho dòng twin
Mỗi finding phải kèm evidence trích dẫn được (tên file + chuỗi tìm thấy/không thấy).`,
  { label: `judge:${pkg}`, phase: 'Judge', schema: FINDINGS_SCHEMA },
)

const verify = (pkg, f) => agent(
  `Phản biện kết luận sau về app ${pkg}, dòng checklist "${f.value}".
Kết luận: ${f.verdict}. Bằng chứng đưa ra: ${f.evidence}

Tự kiểm lại từ APK/log. Trả holds=false nếu bằng chứng không đứng vững hoặc
có cách giải thích khác hợp lý hơn. Đừng xác nhận chỉ vì nghe hợp lý.`,
  { label: `verify:${pkg}:${f.value}`, phase: 'Verify', schema: VERDICT_SCHEMA },
)

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

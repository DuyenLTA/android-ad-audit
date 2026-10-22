# Change log knowledge base — audit-fanout

KB của workflow này: `.claude/commands/audit-fanout.md` (quy trình, điểm dừng),
`.claude/workflows/audit-fanout.mjs` (brief cho agent judge/verify), `DEFAULT_FILTERS` và alias
trong `tools/ad-checklist-diff/check_ads.py`, luật dừng trong `audit_runner.py`, tài liệu
`tools/ad-checklist-diff/README.md`, bài học trong `plans/reports/`.

Mỗi lần sửa KB: thêm một dòng vào mục "Bài học" nếu sửa vì đầu ra sai, ghi số trước và sau.

## Bài học (sửa vì đầu ra sai)

| Ngày | Đầu ra sai | Sửa gì | Trước → sau |
|---|---|---|---|
| 11/09/2026 | Cấu hình đúng bị báo lệch vì chỉ so log | So thêm chuỗi trong APK (`d45e5ad`, `3eb6e95`) | Xem report `260911-1840` trong `plans/reports` |
| 13/09/2026 | Log FA-SVC của app khác lẫn vào lượt capture | Bỏ batch của app khác (`3ed2b36`) | Hết dòng khớp nhầm |
| 13/09/2026 | Filter FA-SVC và UMP che mất dòng thật | Revert hai filter (`8982495`, `e139129`) | Quy tắc cũ đã xóa |
| 14/09/2026 | Bản dev vc12 bị chấm thành 45 lệch (9/54 khớp) | Dừng khi nhận ra bản dev, exit 3 (`7af0bc4`) | vc14 bản release 54/54 |
| 14/09/2026 | Verify mỗi dòng một agent: 17 agent, 18 phút | Một agent mỗi app, trả lời cả nhóm triage một lần (`72e6ed8`, `77935e6`) | 17 agent → 1 agent mỗi app |
| 14/09/2026 | Quét APK mù bị coi là bằng chứng | Không tính là bằng chứng (`d224aea`) | — |

## Commit đụng tới KB

| Ngày | Commit | Loại | Thay đổi | File KB |
|---|---|---|---|---|
| 10/10/2026 | `49ae2f8` | Sửa sau lỗi | fix(audit-fanout): resolve the venv python per OS instead of hardcoding .venv/bin | `.claude/commands/audit-fanout.md`, `.claude/workflows/audit-fanout.mjs` |
| 23/09/2026 | `e8961de` | Sửa sau lỗi | fix(audit-fanout): mở trang artifact bằng browser sau khi ghi link | `.claude/commands/audit-fanout.md` |
| 21/09/2026 | `b03ea1c` | Sửa sau lỗi | fix(audit-fanout): ghi link artifact mà không bật cửa sổ browser thứ hai | `.claude/commands/audit-fanout.md` |
| 14/09/2026 | `0eb7487` | Thêm quy tắc | feat(audit-fanout): write the artifact page for the ads team | `.claude/commands/audit-fanout.md` |
| 14/09/2026 | `0db0f0e` | Sửa sau lỗi | fix(audit-fanout): let the command run from outside the repo | `.claude/commands/audit-fanout.md` |
| 14/09/2026 | `5d03736` | Thêm quy tắc | feat(ad-checklist-diff): gate a re-audit on the checklist, not just the build | `.claude/workflows/audit-fanout.mjs`, `tools/ad-checklist-diff/audit_runner.py`, `tools/ad-checklist-diff/check_ads.py` |
| 14/09/2026 | `b8f947e` | Khác | refactor(ad-checklist-diff): remove the Streamlit GUI | `tools/ad-checklist-diff/README.md`, `tools/ad-checklist-diff/check_ads.py` |
| 14/09/2026 | `e139129` | Sửa sau lỗi | fix(ad-checklist-diff): drop the UserMessagingPlatform filter | `tools/ad-checklist-diff/README.md`, `tools/ad-checklist-diff/check_ads.py` |
| 14/09/2026 | `3ed2b36` | Thêm quy tắc | feat(ad-checklist-diff): abandon a dev-build capture, and drop other apps' batches | `tools/ad-checklist-diff/audit_runner.py` |
| 14/09/2026 | `8c8a373` | Sửa sau lỗi | fix(ad-checklist-diff): scan every APK of the build, and match a label's other name | `tools/ad-checklist-diff/check_ads.py` |
| 14/09/2026 | `7af0bc4` | Thêm quy tắc | feat(ad-checklist-diff): stop the run when the build is a dev build | `.claude/workflows/audit-fanout.mjs`, `tools/ad-checklist-diff/audit_runner.py` |
| 14/09/2026 | `04a2d33` | Thêm quy tắc | feat(ad-checklist-diff): say on the page what the run already knew | `tools/ad-checklist-diff/audit_runner.py` |
| 14/09/2026 | `77935e6` | Sửa sau lỗi | fix(audit-fanout): answer a whole triage bucket once, not row by row | `.claude/workflows/audit-fanout.mjs` |
| 14/09/2026 | `d224aea` | Sửa sau lỗi | fix(ad-checklist-diff): stop reading a blind APK sweep as evidence | `tools/ad-checklist-diff/audit_runner.py` |
| 14/09/2026 | `72e6ed8` | Sửa sau lỗi | fix(audit-fanout): verify a whole app in one agent, not one per row | `.claude/workflows/audit-fanout.mjs` |
| 14/09/2026 | `52cf491` | Sửa sau lỗi | fix(ad-checklist-diff): open the artifact when its link is recorded | `.claude/commands/audit-fanout.md` |
| 14/09/2026 | `42e339f` | Khác | merge: bring in the capture fixes from the other machine |  |
| 14/09/2026 | `e51bbba` | Sửa sau lỗi | fix(ad-checklist-diff): keep a killed run from writing into the next capture | `.claude/commands/audit-fanout.md` |
| 14/09/2026 | `674de69` | Khác | docs(ad-checklist-diff): document the per-app artifact links | `tools/ad-checklist-diff/README.md` |
| 14/09/2026 | `f62b474` | Thêm quy tắc | feat(ad-checklist-diff): remember each app's page, and open it when a run ends | `.claude/commands/audit-fanout.md` |
| 13/09/2026 | `25d8f63` | Khác | refactor(audit-fanout): brief the verify agent like the judge | `.claude/commands/audit-fanout.md`, `.claude/workflows/audit-fanout.mjs` |
| 13/09/2026 | `499d3f0` | Sửa sau lỗi | fix(ad-checklist-diff): make the capture worth trusting | `tools/ad-checklist-diff/README.md`, `tools/ad-checklist-diff/audit_runner.py` |
| 13/09/2026 | `c13e1fc` | Thêm quy tắc | feat(ad-checklist-diff): print Vietnamese output on a Windows console | `tools/ad-checklist-diff/check_ads.py` |
| 11/09/2026 | `aa5667a` | Thêm quy tắc | feat(ad-checklist-diff): let the sheet say which tab belongs to which app | `.claude/commands/audit-fanout.md`, `tools/ad-checklist-diff/README.md` |
| 11/09/2026 | `5097535` | Thêm quy tắc | feat(ad-checklist-diff): find any installed app by the name on its icon | `.claude/commands/audit-fanout.md`, `tools/ad-checklist-diff/README.md` |
| 11/09/2026 | `425a465` | Thêm quy tắc | feat(ad-checklist-diff): find an app by the name on the phone | `.claude/commands/audit-fanout.md`, `tools/ad-checklist-diff/README.md` |
| 11/09/2026 | `3eb6e95` | Sửa sau lỗi | fix(ad-checklist-diff): answer the two rows an APK-only run kept failing | `tools/ad-checklist-diff/audit_runner.py` |
| 11/09/2026 | `d45e5ad` | Sửa sau lỗi | fix(ad-checklist-diff): stop reporting correct config as mismatched | `tools/ad-checklist-diff/README.md`, `tools/ad-checklist-diff/check_ads.py` |
| 11/09/2026 | `f53edc8` | Khác | perf(audit-fanout): stop paying for deliberation where there is none | `.claude/workflows/audit-fanout.mjs` |
| 11/09/2026 | `afc564a` | Khác | docs(ad-checklist-diff): measure where a run goes, and leave the driver alone | `tools/ad-checklist-diff/README.md` |
| 11/09/2026 | `b4ca754` | Khác | perf(ad-checklist-diff): answer the APK question before an agent has to ask it | `.claude/workflows/audit-fanout.mjs`, `tools/ad-checklist-diff/README.md`, `tools/ad-checklist-diff/audit_runner.py` |
| 11/09/2026 | `0cbb31b` | Thêm quy tắc | feat(audit-fanout): pass the run's own identity to the report builder | `.claude/commands/audit-fanout.md` |
| 11/09/2026 | `7f9a619` | Sửa sau lỗi | fix(ad-checklist-diff): stop typing one run's facts into the shared template | `tools/ad-checklist-diff/README.md` |
| 11/09/2026 | `5d16222` | Khác | perf(audit-fanout): only open an agent where there is something to judge | `.claude/commands/audit-fanout.md`, `.claude/workflows/audit-fanout.mjs`, `tools/ad-checklist-diff/audit_runner.py` |
| 11/09/2026 | `fbcc73c` | Sửa sau lỗi | fix(ad-checklist-diff): put the capture's own context inside the triage | `.claude/workflows/audit-fanout.mjs`, `tools/ad-checklist-diff/README.md`, `tools/ad-checklist-diff/audit_runner.py` |
| 11/09/2026 | `e1793bf` | Sửa sau lỗi | fix(audit-fanout): run from any directory, not just the repo root | `.claude/commands/audit-fanout.md`, `.claude/workflows/audit-fanout.mjs`, `tools/ad-checklist-diff/README.md` |
| 11/09/2026 | `f8823e2` | Thêm quy tắc | feat(audit-fanout): run the whole audit from one slash command | `.claude/commands/audit-fanout.md`, `tools/ad-checklist-diff/README.md` |
| 11/09/2026 | `e100d3a` | Khác | docs(ad-checklist-diff): link the workflow guide from the agent section | `tools/ad-checklist-diff/README.md` |
| 11/09/2026 | `e55ba58` | Thêm quy tắc | feat(ad-checklist-diff): build the shareable report from the snapshot | `tools/ad-checklist-diff/README.md` |
| 11/09/2026 | `51a8d00` | Thêm quy tắc | feat(ad-checklist-diff): trust the line that prints the Adjust environment | `tools/ad-checklist-diff/check_ads.py` |
| 11/09/2026 | `46bd1b9` | Thêm quy tắc | feat(ad-checklist-diff): audit from inside the fan-out instead of before it | `.claude/workflows/audit-fanout.mjs` |
| 11/09/2026 | `02f7b21` | Thêm quy tắc | feat(ad-checklist-diff): let the registry name the sheet its gids point into | `tools/ad-checklist-diff/README.md`, `tools/ad-checklist-diff/audit_runner.py` |
| 11/09/2026 | `b868134` | Thêm quy tắc | feat(ad-checklist-diff): make the fan-out runnable by name | `.claude/workflows/audit-fanout.mjs`, `tools/ad-checklist-diff/README.md` |
| 11/09/2026 | `cda1bb3` | Thêm quy tắc | feat(ad-checklist-diff): trust the bare-tag interstitial load line | `tools/ad-checklist-diff/README.md`, `tools/ad-checklist-diff/check_ads.py` |
| 11/09/2026 | `18cdb3c` | Thêm quy tắc | feat(ad-checklist-diff): drive the phone from the runner, and audit on a daily schedule | `tools/ad-checklist-diff/README.md`, `tools/ad-checklist-diff/audit_runner.py` |
| 11/09/2026 | `43941c9` | Thêm quy tắc | feat(ad-checklist-diff): audit the whole registry on a schedule, reporting only changes | `tools/ad-checklist-diff/README.md`, `tools/ad-checklist-diff/audit_runner.py` |
| 11/09/2026 | `ebe73cf` | Thêm quy tắc | feat(ad-checklist-diff): audit both user journeys unattended, and without a device | `tools/ad-checklist-diff/check_ads.py` |
| 08/09/2026 | `70f7c24` | Thêm quy tắc | feat(ad-checklist-diff): open the report through its shareable artifact link | `tools/ad-checklist-diff/README.md` |
| 08/09/2026 | `e52f6f6` | Sửa sau lỗi | fix(ad-checklist-diff): verify from APK, open report over http, scope hints per row | `tools/ad-checklist-diff/README.md`, `tools/ad-checklist-diff/check_ads.py` |
| 08/09/2026 | `38f4b06` | Khác | Update README to match the current filter list and mismatch-note behavior | `tools/ad-checklist-diff/README.md` |
| 08/09/2026 | `72e8d0c` | Khác | Reword mismatch notes to say ID lệch explicitly | `tools/ad-checklist-diff/check_ads.py` |
| 08/09/2026 | `e2fb02b` | Khác | Prefix every mismatch note with the checklist's own expected ID | `tools/ad-checklist-diff/check_ads.py` |
| 08/09/2026 | `84ab2ec` | Khác | Narrow the mismatch-note fallback to same-line key co-occurrence | `tools/ad-checklist-diff/check_ads.py` |
| 08/09/2026 | `d3ee765` | Khác | Show what the log actually has for each mismatched (Lệch) row | `tools/ad-checklist-diff/check_ads.py` |
| 07/09/2026 | `b5a316e` | Khác | Rename the fail-status label from Thiếu to Lệch | `tools/ad-checklist-diff/README.md`, `tools/ad-checklist-diff/check_ads.py` |
| 07/09/2026 | `9986afe` | Khác | Revert the inter_feature_high alias -- it was an unverified guess | `tools/ad-checklist-diff/check_ads.py` |
| 07/09/2026 | `490bb53` | Khác | Hardcode the inter_feature_high naming alias instead of a sheet edit | `tools/ad-checklist-diff/check_ads.py` |
| 07/09/2026 | `20ecafb` | Khác | Add optional alt-values sheet column for naming-mismatch rows | `tools/ad-checklist-diff/README.md`, `tools/ad-checklist-diff/check_ads.py` |
| 07/09/2026 | `a2b8bbe` | Khác | Verify Package name and App ID rows the GUI's log filters can't reach | `tools/ad-checklist-diff/README.md` |
| 07/09/2026 | `7e0dad8` | Khác | Split check_ads.py into focused modules to stay under 200 lines each | `tools/ad-checklist-diff/check_ads.py` |
| 28/08/2026 | `87800e7` | Khác | Add ad-checklist-diff: Android ad/config checklist audit tool | `tools/ad-checklist-diff/README.md`, `tools/ad-checklist-diff/check_ads.py` |

Sinh lại bảng: `git log --name-only -- .claude tools/ad-checklist-diff/check_ads.py tools/ad-checklist-diff/README.md tools/ad-checklist-diff/audit_runner.py`

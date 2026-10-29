# Phase 3b: local redlines and accept/reject renewal

- Read Phase 3a and 1028 helpers and reuse their source snapshot, pixel/upstream scoring and encoding.
- Verify phase-1 hashes, wait for Word master ALLDONE, resolve every candidate only through find_output; retain generation/Word failures as ITT zero with reasons.
- Snapshot bench main, pin fingerprint 5e481477e2196f6b, numpy 144 DPI without cache; verify upstream binary hash and score at 150 DPI.
- Prepare 2,800 redlines tool rows, 2,400 Set B tool rows and 800 Set B reference assets. Six process workers; per-case fingerprints and immediate raster cleanup.
- Replace 1,400 redlines cases' jubarte/docxodus maps; remove stale version lanes; append 400 accept + 400 reject cases as ar/accept_all and ar/reject_all. Preserve source case order, other tools, Word columns and every byte outside DATA.
- Audit every input, checkpoint, case, asset and preservation constraint; report per group/tool means with denominators and failure stages/reasons; manifest and exact sizes.
- Run pure-helper coverage tests and real scorer API smoke; Vite console-pipe + Playwright integration with JPEG screenshots. No Word/uploads/commits/posts/live writes.

## Viewer decision

The existing redlines DATA schema supports independent groups, references, per-case tool versions, failures, metrics and page PDFs. Append two groups to the existing viewer, retaining all original rows in order and the full HTML/JavaScript envelope unchanged. This is the smallest faithful change and needs no separate page or navigation change.

## Working notes

- Word master log contained ALLDONE before reading SuperDoc outputs.
- Original local main ref was stale; origin/main 3121c4988d72bf5cd93607c18cb50e3d713ce338 matches the completed Phase 3a snapshot. The build records the exact archived main ref and commit.
- Pure-helper red/green cycle: 17 intended failures before implementation; green Coverage: 100% lines, 100% branches. A failed failure-row assertion exposed incomplete test fixture setup (missing stale PDF); fixture corrected without reducing assertions.
- Added real Wordcraft availability-list regression; all 27 unit/integration tests pass with Coverage: 100% lines, 100% branches across common.py and prepare_helpers.py. Public scorer/upstream identity smoke passes.
- Spec and independent code-quality reviews approved after adding strict accepted/rejected DOCX manifest confirmation and final generation-failure hash rechecks. Full scoring/asset audit/browser checks still pending.
- First subagent-owned scoring session ended with 895 valid records. Six abandoned raster folders removed; root-owned run resumed those records (recovery.json). No generation or Word rerun or scoring/input change.

## Complete

- All 6,000 records built, zero build errors; 693 generation failures and 139 Word failures retained as ITT zero.
- Preview: 1,400 compare cases updated, 29 historical cases byte-identical, 800 Set B cases appended; 2,229 cases total. All HTML outside DATA, other engines, Word columns and original order verified unchanged.
- Full audit passed: 14,099 unique input files, 6,000 checkpoints and 22,706 assets. Manifest has 22,707 entries. No temporary PNGs.
- 27 pytest tests passed, Coverage: 100% lines, 100% branches for changed pure helpers; scorer/upstream API identity integration passed.
- Final Playwright passed 8 cases, versions/metrics/assets/PDFs/ITT-zero/sorting/navigation; 40 local and 15 retained remote responses, no exceptions/bad assets/unexpected remote requests. 16 JPEGs visually inspected; console-pipe and raw V8 coverage saved.
- Corrected browser fixture/coverage-export issues and retained-asset routing after confirming Phase 3a's missing local assets exist at their original published URLs. Diagnostics retained, no assertions removed.
- Assets 1,538,121,096 bytes; complete build 1,611,938,831 bytes. Full per-group/tool metrics and failure reasons in build/REPORT.md; verification.json records final gates. Local preview remains at http://127.0.0.1:8180/redlines/.
- Local-only boundary honored. No Word, uploads, commits, pushes, GitHub posts or source viewer writes. No required work remains.

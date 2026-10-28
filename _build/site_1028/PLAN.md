# 2026-10-28 review-site renewal

All writes stay here. No upload, live HTML edits, commit or push.

- [x] Read main AGENTS.md, PUBLISHING.md, issues 94–96 and site_1011 scripts; inspect both DATA/viewers.
- [x] Build A: download sha-verified v1; preserve recorded pixel ITT/failures; all-page upstream metrics; first-three-page images/PDFs; delete inputs/rasters.
- [ ] Build B: map 800 split pairs and original versions to verified hub PDFs; reconcile 13 existing pair identities; metrics/images/PDFs; delete inputs/rasters.
- [x] Build C: verify metadata/PDFs against public manifest; folder-specific engines/versions and recorded pixels; metrics/images/PDFs; delete inputs/rasters.
- [x] Patch copies only, retain historical cases, hide unrelated engine lanes per new case, add pixel sorting and per-case versions.
- [x] Verify all case assets/schema/scores and duplicate identities, browser-smoke both viewers with local new assets and console capture; write report and README.

Implementation: process.py closely follows site_1011's draw/metrics/encode/case; prepare.py adapts the three records into jobs. Checkpoints remain under build/records; only completed per-case output is reusable. Six concurrent cases, one engine raster at a time, Rayon limited to one thread per scorer. Inputs deleted after the corresponding set passes integrity checks. Automated tests focus on deterministic metadata and patch transformations; integration checks use actual PDFs and upstream binary.

Observed: v1 2,925/2,925 built and asset-validated; 32,493 assets / 1.883 GiB. Live viewers unchanged by SHA256. V1 browser smoke passed with images, versions, PDF links and numeric Pixel sorting; no page errors. Split source gap remains pending user location; eight legacy pair aliases and 800 exact jobs prepared. Wordcraft compare/convert job pixel means and source hashes checked. Last completed Python suite: 19 passed; Coverage: 93.62% lines, 84.78% branches. Expanded final suite will run after all available sets finish.

Final available-set verification: 24 passed; Coverage: 86.19% lines, 76.62% branches (pytest scope all renewal Python scripts). All 3,725 completed cases / 55,385 assets validated. No source HTML or scorer binary changes. Final browser checks pending their current run; no downloaded PDFs or generated PNGs retained. Set B remains blocked on its exact candidate PDFs.

Final browser verification passed: three completed sets plus two historical selections; 77 local assets loaded, PDF links returned valid PDFs, Pixel sorting in both directions, versions and first-three-page counts checked, health HTTP 200, no page exceptions. Console messages from both viewer routes appear through vite-plugin-console-pipe. The 800-case split remains unbuilt; no placeholder rows or substituted PDFs were emitted.

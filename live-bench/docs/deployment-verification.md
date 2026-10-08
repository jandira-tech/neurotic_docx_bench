<!-- SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC -->
<!-- SPDX-License-Identifier: AGPL-3.0-only -->
# Deployment verification — 8 October 2026

## Services and browser checks

Cloudflare Worker `jubarte-live-bench` serves one dataset at `www.jubarte.pro/live`,
`jubarte.pro/live`, `redlines.free/live`, and `arthur.law/docx-bench-live`.
Astro 7.3.7, EmDash 1.2.0 and self-hosted PDF.js 6.4.299 provide the frontend. The
existing Jubarte whale, Graphite/Night palette and licensed fonts are preserved.
All four URLs were opened in the in-app browser: live state and both PDF pages
rendered. Page navigation, pause and historical fixture selection worked.

Dedicated resources are D1 `jubarte-live-bench` (database
`efb01828-aca6-4f92-9a3c-7433931e8f0f`), R2 `jubarte-live-bench-artifacts` and the
SESSION KV binding in `wrangler.jsonc`. Both migrations are applied. Routes cover
only the benchmark paths. Original site roots retained their observed statuses,
redirects and available ETags. Public CMS/setup routes are disabled.

The existing redlines.free Cloudflare challenge sometimes returns 403 to plain CLI
requests; its browser successfully loaded the dashboard, live data and PDFs. Existing
protection was preserved. The backend publishes through jubarte.pro.

Coolify service `laxbthc1lmn8o41rlymgf8lx` runs one backend replica. Updated image:
`sha256:68166646ada8b71bc8f26b904f5a624c4c651de8ddf8686279da158ebeb7b694`.
Docker inspection confirmed running/healthy, zero restarts, no exposed/published
ports, read-only root, 4 GiB memory, two CPUs, 256 PIDs, dropped capabilities and
no privilege escalation. `MAX_FIXTURE_BYTES=20000000` and `MAX_BATCHES=0` are active.
Its executable health check reads the worker's atomic heartbeat.

## Real data and file bounds

Updated run `01a11a49-7e73-770c-997d-0013581d67e9` downloaded its first 200 actual
linked documents before benchmarking; the largest was 4,384,190 bytes. Four rejected
packages remained recorded. At 07:11 UTC five reviews were complete and review six
was being measured. These are actual corpus documents and scores.

Previous run `01a11a2d-884c-767a-8634-241e1514740c` retains nine published reviews.
Every artifact of updated-run review four (23 objects) was retrieved and checked
against its declared SHA256 and size. PDF byte ranges returned 206 with `%PDF-`.
Artifact HEAD requests worked across all aliases. Source files, PDFs, redlines,
score JSON and PNG evidence remain accessible across runs.

An authenticated 20,000,001-byte upload returned 413 and created no object (404).
Unauthenticated ingestion returned 401. The 20 MB bound applies to advertised and
streamed downloads, tool inputs/outputs, subprocess file writing, publisher uploads
and Cloudflare artifact metadata. Existing published history is preserved. Large
manifests split into verified parts without dropping review metadata.

The first production group of 100 is still processing. Full 100-review archive/retry,
archive splitting, refill at review 90 and predecessor continuity passed local tests.
Production group completion is not claimed as already observed.

## Versions and references

Production records Jubarte 0.11.3, LibreOffice 26.8.0.3, docxide 0.18.3,
Docxodus `docx-scalpel` 0.6.5, .NET 10.0.12 and SuperDoc Redlines commit
`06d9fcfbb80b28cee0c7cd71cda720297712ace5`. Binary/archive hashes, corpus revision,
scorer/raster identity and worker source fingerprint accompany the run. Current
worker fingerprint: `cafb1917fb38955e70866bf71aad75915d99f799fdf07d4233b81a2ba0450bb4`.

Live Word controls returned 200 for conversion and comparison, and the redline
passed all four accept/reject functional checks. Multipart names are `document`
for conversion and `original`/`revised` for comparison. Package rejections are logged
independently. See `word-endpoint-verification.md` for the controls and diagnoses.

## Validation

- Backend: 60 tests; covered policy, state, safety, IO, scoring and seed modules
  achieved **94.9% lines / 91.4% branches**. External tool adapters are not included
  in this coverage claim. Ruff passed and CLI help executed successfully.
- Frontend: 30 tests; covered API/policy/store/view-model modules achieved
  **100% lines / 99.04% branches**. Type checks reported zero errors/warnings;
  build and dependency audit passed.
- Container image smoke executed all six real tools, generated and scored outputs,
  checked functional reconstruction and four PNGs, enforced the file-writing bound
  and denied Internet sockets while retaining Unix sockets. Synthetic smoke scores
  were never published as corpus measurements.
- OrbStack Compose smoke `jubarte-bench-smoke4` completed three real reviews and
  acknowledged its three small local archives; it exited 0 with zero restarts.
- Browser console was captured with `vite-plugin-console-pipe`; no browser render
  errors were observed. EmDash development type generation reports a 404 warning
  because public CMS routes are intentionally disabled.
- Full-ID search exposed D1's 50-byte LIKE pattern limit. Literal `instr` search
  now supports complete corpus IDs and was reverified in production. See the
  [D1 limits](https://developers.cloudflare.com/d1/platform/limits/).

Secrets stay outside Git and frontend assets. Word credentials belong only to the
backend. Font copyright notices are preserved. Subtree licensing metadata is included;
whole-repository REUSE lint has pre-existing failures outside this task and is not
claimed as passing.

## Theme and attribution update — 2026-10-08

Frontend version `8c9f3917-a274-40c7-b9f4-ee264e56e2ea` adds accessible Light/Dark
buttons in the header. Browser checks on local development and production verified
both choices, their selected state, and persistence across reloads. The initial
theme follows the browser preference until the visitor makes a choice.

SuperDoc's corpus is credited above the live telemetry and in a dedicated thank-you
section. Its dataset, editor repository, visual benchmark repository and ODC-By
license are linked, alongside Jubarte, Docxodus, SuperDoc Redlines, LibreOffice,
docxide and Microsoft Word. Links were checked against upstream project pages.

All 30 frontend tests passed with **100% lines / 99.04% branches** for the existing
API/policy modules. The theme interaction was verified in the browser; it is not
included in that unit coverage claim. Type checks, build and Wrangler dry run passed.
The development health endpoint returned 200 and console output was captured by
`vite-plugin-console-pipe`; the existing disabled-EmDash-typegen warning remains.
HTTP checks verified the new controls/credits and health responses on the apex,
www and arthur.law routes; the redlines.free route was verified in the browser.

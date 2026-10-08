<!-- SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC -->
<!-- SPDX-License-Identifier: AGPL-3.0-only -->
# Jubarte Live Bench implementation plan

This plan was prepared before implementation and updated as the user clarified the
six tools, outbound-only deployment, archive presentation and 20 MB file limit.

## Architecture and acceptance criteria

An outbound-only Python container on Coolify owns a persisted SQLite queue and outbox.
It initially samples 200 corpus rows and downloads the actual documents from their
URLs. One benchmark worker runs one operation at a time. At review 90 of each internal
100-review group it queues another 100, indefinitely. The previous sampled fixture
remains the predecessor across boundaries, beginning with a reproducible complex seed.
Failed downloads and unsafe packages retain their occurrence and diagnosis.

Word conversion and comparison are independent reference operations. Conversion tools
are soffice, docxide and Jubarte; redline tools are the Docxodus Python wheel, SuperDoc
Redlines and Jubarte. Conversion fallback is soffice; redline fallback is Docxodus with
a common soffice renderer. References are labelled. Broken candidates score zero with
a valid reference. Infrastructure failures and absent references remain unscored.
The existing technical scorer and functional lens supply the metrics; Jubarte renders
with `--revisions word`.

D1 stores metadata, diagnoses, scores and version provenance; R2 stores immutable
checksummed artifacts and completed archive manifests. Occurrences have independent
UUIDv7 keys. Publication retries before local pruning. Files and uploads have a hard
20,000,000-byte limit; oversized archives split into verified parts. XML, ZIP, PDF,
subprocess and container bounds protect the parser boundary. Native parsers receive
no credentials or Internet sockets.

Astro/EmDash reads D1/R2 dynamically at the four requested paths. Existing Jubarte
styles, actual measurements rotating after a ten-second arrival delay, PDF page
controls, score visualizations and searchable all-run history define the frontend.
Internal groups are absent from the dashboard. The backend exposes no port and uses
an executable heartbeat health check.

## Execution and verification

- [x] Isolate changes in `c/jubarte-live-bench`; preserve the engine and dirty canonical benchmark checkout.
- [x] Implement deterministic policy, sampling, reference selection, chain boundaries, queue transactions, publication retries and pruning.
- [x] Integrate six real tools, release installers, the Python wheel/.NET runtime, technical scoring and functional checks.
- [x] Implement authenticated immutable ingestion, D1 migrations/cohort rollups, R2 artifacts and complete archive validation.
- [x] Build the branded rotating dashboard, all-run search, PDF rendering and visualizations.
- [x] Resolve the prior independent specification review's actionable findings.
- [x] Run tests with line/branch coverage, format/type checks, CLI startup and container tool/isolation smoke checks.
- [x] Complete the OrbStack/Compose pipeline on three real documents, acknowledge small smoke archives and exit 0.
- [x] Verify 100-review archive publication/retry, oversized archive splitting, refill and predecessor continuity locally.
- [x] Deploy Cloudflare and Coolify; verify initial 200 URL downloads, advancing real results, old-run history and four browser aliases.
- [x] Verify production rejects oversized uploads before creating objects.
- [x] Record Word endpoint controls, deployment versions and observed evidence.

The first production group of 100 remains in progress. Its completion and near-end
replenishment are covered by deterministic/integration checks; no full production
group is claimed as already observed. The worker continues independently of this chat.
See `deployment-verification.md` for time-bounded observations.

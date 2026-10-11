<!-- SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC -->
<!-- SPDX-License-Identifier: AGPL-3.0-only -->
# Jubarte Live Bench

An outbound-only benchmark worker continuously downloads actual DOCX files linked by
`superdoc-dev/docx-corpus`, measures conversions and redlines, and publishes immutable
evidence to Cloudflare D1 and R2. An Astro/EmDash dashboard reads those bindings at request
time. New measurements require no frontend deployment.

The public dashboard shares one dataset at:

- https://www.jubarte.pro/live
- https://jubarte.pro/live
- https://redlines.free/live
- https://arthur.law/docx-bench-live

Only these paths and their descendants are routed to this Worker. Other site routes are
preserved. Public EmDash administration and setup routes are disabled.

## Measurement policy

Conversions: Jubarte, LibreOffice (`soffice`), and docxide. Redlines: Jubarte,
Docxodus (`docx-scalpel` Python wheel with .NET), and SuperDoc Redlines. The existing
`neurotic_docx_bench.pipeline` technical PDF scorer supplies fidelity, page-count penalties,
ink and text metrics. The functional lens independently checks whether accepting and
rejecting tracked changes reconstruct the two inputs. Full per-page score JSON and a PNG
inspection view accompany each scored candidate.

Word at `WORD_PUBLIC_URL` is preferred independently for `/v1/convert` and `/v1/compare`.
If conversion fails, LibreOffice provides that reference. If compare or rendering the
Word redline fails, Docxodus provides the redline reference and LibreOffice renders
the whole redline cohort. Every stage records its status, elapsed time and relevant tool.
Jubarte native PDFs always use `--revisions word`.

A broken candidate scores zero when a usable reference exists. Infrastructure errors
and missing references remain unscored. A fallback reference is labelled as a reference
and is never measured against itself. Reference and renderer cohorts stay separate.
Failed or unsafe fixtures retain their occurrence and failure evidence. An unsafe
predecessor makes the next redline unavailable; conversion of the next fixture still runs.

Each fixture, generated output, archive object and upload is limited to **20,000,000
bytes (20 MB)**. A smaller fixture limit may be configured; a larger one is rejected.
Both advertised and streamed download sizes are checked. Tool subprocesses also have
a 20 MB file-writing limit. Oversized outputs are recorded as tool-specific failures.
Archive manifests split into independently verified parts when necessary. ZIP parts,
XML expansion, nesting and entity declarations have additional preflight limits.

Each queued review receives a UUIDv7, independent of the corpus ID or document hash.
The sampler visits a reproducible random permutation before beginning another cycle.
All corpus fields, download metadata, checksums, security decisions, tool versions and
binary hashes are recorded. The complex `starting_point.docx` is generated reproducibly
and is the first predecessor; subsequent comparisons use the previous sampled fixture,
including across internal group boundaries.

The worker initially downloads 200 fixtures. It processes one fixture at a time and
queues another 100 at review 90 of each group. Each completed group has a verified,
immutable 100-review R2 manifest and a D1 archive record. SQLite commits completion,
predecessor and outbox together. Publication is retried before deleting local evidence;
only acknowledged files are pruned. The latest predecessor stays on disk. The frontend
does not expose this grouping: it rotates measured outputs with a ten-second delay,
supports pausing, and searches/paginates review history across every run.

The header offers Light and Dark themes, retaining each visitor's choice in browser
storage and restoring it before paint. Until a choice is made, the theme follows the
browser preference. The credits section thanks SuperDoc for the public DOCX corpus and
visual benchmark methodology, links the corpus's ODC-By attribution license, and links
all benchmarked tools and Microsoft Word.

## Local startup with OrbStack

Run from `live-bench/` in this checkout. Copy `.env.example` to `.env`, set the existing
Word token and a random ingest token of at least 24 characters. Keep `.env` private.

```sh
cd frontend
npm ci
npx wrangler d1 migrations apply DB --local
```

For the local smoke test, put `INGEST_TOKEN=local-smoke-token-at-least-24-characters`
in `frontend/.dev.vars` and start `npm run dev -- --background`. This includes
`vite-plugin-console-pipe`; use `npx astro dev logs` to inspect browser errors.
Return to `live-bench/`, ensure OrbStack is running, then:

```sh
PATH=/Users/arthrod/.orbstack/bin:$PATH docker compose build
PATH=/Users/arthrod/.orbstack/bin:$PATH docker compose -p jubarte-bench-smoke \
  -f compose.yaml -f compose.smoke.yaml up -d
PATH=/Users/arthrod/.orbstack/bin:$PATH docker compose -p jubarte-bench-smoke \
  -f compose.yaml -f compose.smoke.yaml logs -f
```

This uses a dedicated volume and stops successfully after three real reviews. Its
restart policy is `no`; capped smoke runs must never use `unless-stopped`. Reuse the
same volume only with identical tool versions, worker source, corpus revision and group
size. For a new smoke run, use a new Compose project name. Preserve old evidence until
publication is acknowledged.

Do not run `astro build` concurrently with the Astro development server: it changes
Vite's dependency cache. Stop dev before building and restart it afterward. For the
continuous local worker, omit the smoke override and use the production ingest settings.

## Cloudflare and Coolify deployment

`frontend/wrangler.jsonc` records the dedicated D1, R2, session KV and exact host routes.
Authenticate Wrangler to the owning account. Apply migrations before publishing code:

```sh
cd frontend
npx wrangler d1 migrations apply DB --remote
npm run check
npm run build
npx wrangler secret put INGEST_TOKEN
npx wrangler deploy
```

Configure the same ingest token in Coolify and set `WORD_API_TOKEN` there. Never put
the Word credential in Cloudflare or in a frontend bundle. The image must be built
for the Coolify server's architecture from the benchmark repository root:

```sh
docker build -t jubarte-live-bench:production -f live-bench/Dockerfile .
```

Use `compose.coolify.yaml` for the backend service. It exposes no domain or port.
Its executable Docker health check reads an atomically replaced heartbeat file.
`MAX_BATCHES=0` runs continuously. Keep the configured data volume across same-version
restarts. An engine/worker upgrade requires a new run/volume so immutable version
metadata remains accurate; existing D1/R2 history remains browsable.

The image resolves and checksum-verifies the latest stable Jubarte and LibreOffice at
build time. It pins docxide and SuperDoc Redlines, installs the Docxodus wheel and .NET,
and records exact versions/hashes. It runs as UID 10001, with a read-only root, bounded
tmpfs, 4 GB memory, two CPUs, 256 PIDs, no capabilities and no privilege escalation.
Logs rotate at 20 MB with three files. Parser/scorer subprocesses receive no credentials,
cannot create Internet sockets on Linux, and have process-group timeouts, CPU, file and
descriptor limits. ZIP/XML and generated packages pass bounded preflight before parsing;
PDFs have page-count and raster-cost limits. Publication requires authentication,
checksums, immutable keys and complete manifests.

See [deployment-verification.md](docs/deployment-verification.md) for the observed
production checks and [word-endpoint-verification.md](docs/word-endpoint-verification.md)
for the live Word endpoint contract and package-rejection controls.

## Verification

```sh
cd backend
uv sync --dev
uv run ruff check livebench tests
uv run ruff format --check livebench tests
uv run pytest --cov=livebench.benchmark --cov=livebench.state \
  --cov=livebench.models --cov=livebench.safety --cov=livebench.corpus \
  --cov=livebench.config --cov=livebench.publisher --cov=livebench.scorer \
  --cov=livebench.seed --cov=livebench.pdf_probe \
  --cov-report=term-missing --cov-report=json:coverage.json --cov-branch
uv run python scripts/coverage_summary.py
uv run jubarte-live-bench --help
cd ../frontend
npm test
npm run check
```

Coverage above measures the tested policy, storage, downloader, safety, scoring and seed
modules; it does not claim coverage of every external tool adapter. Real files and
processes belong to integration tests; network tests use HTTPX's upstream `MockTransport`
and database tests use in-memory SQLite. An additional container image smoke test in
`backend/scripts/image_smoke.py` executes all six real tools, scoring and network isolation
against a reproducible pair while intentionally making the Word reference unavailable.
Never publish synthetic smoke scores as corpus results.

## Asset provenance

The dashboard follows the existing Jubarte Graphite/Night styles and whale mark from
the Jandira-owned Jubarte site. Manrope, JetBrains Mono and Source Serif 4 font files
retain their SIL Open Font License texts in `frontend/src/styles/fonts/`. The project
code is AGPL-3.0-only under the repository's `LICENSE`; upstream tools keep their own
licenses and provenance, pinned in the image and run metadata.

PDF previews use Mozilla PDF.js; its Apache-2.0 license is included with self-hosted
build assets. No external CDN is required to view evidence.

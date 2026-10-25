# Publishing fixtures and results

How bench products leave this machine: review fixtures and page images go to a public
**R2** bucket, the live benchmark streams into a **D1** database, the dashboard reads
D1/R2 at request time, and the review website is this repo's **gh-pages** branch
(checked out at `site/`). Everything goes through **wrangler** (Cloudflare) or the
Hugging Face hub. After a publish, the local heavy artifacts are deleted — the tracked
records (`results/*.jsonl`, `REPORT.md`, snapshots) are the copy of record, and the
bytes live on R2 / the hub.

## The map

| What | Where | Managed by |
|---|---|---|
| Review fixtures (page images, PDFs, cohort packages) | R2 bucket `neurotic-docx-bench-pages`, public at `https://pub-92c80eda1059428394970066c8500eda.r2.dev/` | `scripts/publish/upload_r2.py` |
| Fast bulk upload (thousands of objects) | Worker `ndb-r2-upload` → `https://ndb-r2-upload.cicero-im.workers.dev` | `scripts/publish/r2-upload-worker/` |
| Live benchmark (continuous DOCX/redline runs) | D1 `jubarte-live-bench` (id `efb01828-…8f0f`) + R2 `jubarte-live-bench-artifacts` | `live-bench/backend` worker via `/api/ingest` |
| Live dashboard | Worker `jubarte-live-bench`, routes `jubarte.pro/live`, `redlines.free/live`, `arthur.law/docx-bench-live` | `live-bench/frontend`, `wrangler deploy` |
| Review website (static viewers) | GitHub Pages on this repo's `gh-pages` branch → `https://jandira-tech.github.io/neurotic_docx_bench/`; checkout at `site/` (git-ignored) | `git worktree` + push |
| Corpus DOCX/PDF (the oracle tree) | HF dataset `arthrod/neurotic_docx_bench-fixtures` | `bench fixtures download|upload`, `scripts/hf_fixtures/` |

Cloudflare account: `5651b2fe85f9bbb0fc1b8f4ad2cb4e64` (Arthursrodrigues@gmail.com).
Everything above lives on it. The D1 harvest tooling is `live-bench/harvest/` with its
README.

## Setup (once per machine)

```bash
bunx wrangler login          # OAuth in the browser; token lands in ~/.wrangler/config/default.toml
bunx wrangler whoami         # check; also refreshes the token — the token lives ~1 h
```

The Python uploader reuses that OAuth token; when it expires mid-run the script runs
`bunx wrangler whoami` itself to refresh. `npx -y wrangler …` works everywhere bun
isn't.

## Publish review fixtures to R2

One directory → one prefix. Objects are immutable by convention (the Worker refuses
overwrites with 412), served with a one-year cache header, and the uploader skips keys
already present.

```bash
# small sets: straight through the R2 API (rate limit ~4 uploads/s)
uv run --with httpx python scripts/publish/upload_r2.py <local_dir> <r2_prefix>

# thousands of files: through the upload Worker (no rate limit, 32 parallel)
uv run --with httpx python scripts/publish/upload_r2.py <local_dir> <r2_prefix> \
    --via-worker https://ndb-r2-upload.cicero-im.workers.dev

# check a prefix: every local file on the bucket with the same byte size
uv run --with httpx python scripts/publish/upload_r2.py <local_dir> <r2_prefix> --verify
```

Public URL of anything uploaded: `https://pub-92c80eda1059428394970066c8500eda.r2.dev/<prefix>/<path>`.

Direct object ops without the script:

```bash
bunx wrangler r2 object put neurotic-docx-bench-pages/<key> --file <local> --content-type application/pdf
bunx wrangler r2 object get neurotic-docx-bench-pages/<key> --file <out>
bunx wrangler r2 bucket list
```

### What is on the bucket today

Every package carries a `MANIFEST.sha256.txt` (and a README); all URLs are relative to
`https://pub-92c80eda1059428394970066c8500eda.r2.dev/`:

| Prefix | What |
|---|---|
| `d2p/`, `redlines/` | the review site's page images and per-case PDFs (2026-10-11 renewal; referenced by the gh-pages viewers) |
| `wordcraft-20261014/` | the wordcraft 400+400 cohort — oracles, every tool lane, scores, REPORT (12,034 objects) |
| `wordcraft-20261014-initial/` | the original 200+200 morning run (docxodus pre-12.6.5, jubarte-0.12.0-c551 lanes) |
| `jubarte-release/compare-regen/` | `bench jubarte-release` working evidence (Word compare regenerations vs old baseline) |
| `word-driver-ab/20261014/` | the Word-driver A/B report and runs (AGENTS.md "What the 2026-10-14 A/B found") |
| `d1-exports/jubarte-live-bench/2026-10-13/` | D1 export, schema and harvest-analysis records of the 2026-10-13 campaign |

### The sample picker (what reviewers use)

`scripts/pick_fixtures.py` is a colour, Typer-based CLI over the HF fixtures dataset:
`list` shows the corpus by state and set, `search` filters the two tables without
downloading any document bytes, `download` fetches exactly the picked samples
(sha256-verified, optionally with a comparison's base and next inputs):

```bash
uv run --with typer --with rich --with "huggingface_hub<2" python scripts/pick_fixtures.py list
uv run --with typer --with rich --with "huggingface_hub<2" python scripts/pick_fixtures.py search comparisons --set redlines_en_500
uv run --with typer --with rich --with "huggingface_hub<2" python scripts/pick_fixtures.py download documents --set sources_500 --sample 10 --seed 7 --what both
```

A second HF dataset, `arthrod/neurotic-docx-bench-artifacts`, holds the working
evidence that is not corpus (currently `really_broken/` — the Word-refusing fixtures
and tool redlines of the harvest, with `MANIFEST.sha256.txt`). `really_broken/` is
fetched back from there when a harvest or Word-driver session needs it (command in
`live-bench/harvest/README.md`).

Corpus DOCX/PDF are **not** tracked in git on purpose (the 2026-10-17 state): the
hub dataset is their only home; `bench fixtures download` or the picker brings them
back. Git carries the tables, manifests and READMEs only.

### The upload Worker (bulk path)

`scripts/publish/r2-upload-worker/` — a PUT-only proxy into the bucket: requires the
`x-secret` header, never overwrites, sets the cache header. Redeploy after edits:

```bash
cd scripts/publish/r2-upload-worker
openssl rand -hex 24 > ~/.ndb/upload-secret && chmod 600 ~/.ndb/upload-secret
bunx wrangler secret put UPLOAD_SECRET < ~/.ndb/upload-secret
bunx wrangler deploy          # → https://ndb-r2-upload.cicero-im.workers.dev
```

The secret file's default path (`~/.ndb/upload-secret`) is what
`upload_r2.py --secret-file` reads. Rotate by re-running `secret put` with a new file.

### Worked example: the wordcraft 400+400 cohort (2026-10-14)

What went up under `wordcraft-20261014/` (12,034 objects, 2.1 GB, manifest included):

- `compare/oracle*` — Word's compare redlines (PDF + DOCX), one per pair;
- `compare/<tool>/{docx,pdf}` — every tool lane's redline and its Word render;
- `convert/<tool>/pdf` and `convert/oracle/` — the conversion lanes and Word's PDFs;
- per-lane `scores.json` / `generate_failures.json` / `render_failures.json`;
- `README.md`, `REPORT.md`, `REPORT.json`, `tools.json`, `comparisons.csv`,
  `conversions.csv`, `PARTIALS.md`, `MANIFEST.sha256.txt`.

The inputs (base/next DOCX) are corpus files and stay on the HF hub; the two CSVs map
every id to its corpus path and sha256, so the package is complete once inputs are
fetched with `bench fixtures download`.

After the upload verified clean, the local docx/pdf trees under
`results/wordcraft_20261014_fresh/{compare,convert}` were deleted (they are
git-ignored); `REPORT.md`, the lane `scores.json` and the CSVs stayed — they are the
tracked record.

## Publish to D1 (live bench)

The live worker writes D1 itself through its bindings — you normally never push rows
by hand. Reading and one-off fixes:

```bash
npx -y wrangler d1 execute jubarte-live-bench --remote --json --command "SELECT count(*) FROM bench_results"
npx -y wrangler d1 execute jubarte-live-bench --remote --file fixes.sql
npx -y wrangler d1 export jubarte-live-bench --remote --output dump.sql    # snapshot
npx -y wrangler d1 inspect jubarte-live-bench --remote
```

`--local` runs the same statements against the dev copy in `.wrangler/state` instead of
production. The harvest loop that reads failing fixtures back out is
`live-bench/harvest/` (README there); its state lives in `live-bench/.work/`
(git-ignored).

Deploy the dashboard after changing `live-bench/frontend`:

```bash
cd live-bench/frontend && pnpm install --frozen-lockfile --filter jubarte-live-bench && pnpm run build && pnpm exec wrangler deploy
```

`wrangler.jsonc` there holds the routes, the D1/R2/KV bindings and the migrations dir;
`pnpm exec wrangler d1 migrations apply jubarte-live-bench --remote` after adding one.

## Publish the review website (gh-pages)

The site is this repo's `gh-pages` branch: two self-contained viewers
(`index.html` docx→PDF, `redlines/index.html` redlines vs Word) whose page images load
from the R2 bucket, plus `_build/<session>/` — the frozen scripts and data of every
renewal. The checkout is a **linked worktree at `site/`** (git-ignored, so main never
sees its files):

```bash
git worktree list                                  # site/ sits on gh-pages
cd site && git pull --ff-only                      # refresh before editing
# …edit / add a case renewal (scripts under _build/<session>/ document each one)
git add -A && git commit -m "Pages: <what changed>" && git push origin gh-pages
```

GitHub Pages serves `gh-pages` at
`https://jandira-tech.github.io/neurotic_docx_bench/` (legacy build type, root of the
branch). A renewal's page images go to R2 first (prefixes `d2p/`, `redlines/`), then
the viewer's `const DATA = …` JSON is patched to reference them —
`site/_build/site_1011/{process.py,patch_site.py}` is the reference implementation of
the 2026-10-11 renewal; read it before inventing a new one.

If `site/` is missing: `git worktree add site gh-pages`.

## Publish corpus fixtures (HF hub)

Corpus docx/PDF live in the public dataset, not in git (see AGENTS.md "Getting the
corpus files back"). The bench commands:

```bash
uv run bench fixtures download                 # into corpus/; sha256-checked against the manifest
uv run bench fixtures upload                   # writes the manifest (hub upload itself: scripts/hf_fixtures/)
uv run --with polars --with huggingface_hub python scripts/hf_fixtures/hf_fixtures.py build|upload|verify
```

## After every publish: reclaim the disk

The rule (AGENTS.md): record results with rasters deleted; the published copies above
replace the local bytes. A finished publish therefore ends with:

1. `upload_r2.py … --verify` clean (or the hub `verify` for corpus),
2. commit the tracked record (scores, reports, CSVs) and push,
3. delete the local heavy trees that were uploaded (and any `score/` raster folders),
4. `git worktree prune` if a worktree was removed.

Nothing under `results/` that is `.png/.pdf/.docx` is tracked — those patterns are
git-ignored — so deleting them loses nothing that git holds.

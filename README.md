> **See every page side by side: [jandira-tech.github.io/jubarte-redlines](https://jandira-tech.github.io/jubarte-redlines/)**  
> DOCX to PDF across engines, and redlines against Word ([/redlines/](https://jandira-tech.github.io/jubarte-redlines/redlines/)), scored per page.

# neurotic-docx-bench

Pixel scores of DOCX tools against Microsoft Word oracles.

| | |
| --- | --- |
| **Scores** | 0 to 100 per document |
| **Redline oracle** | Word tracked-change DOCX, rendered by LibreOffice 26.2.4.2 for oracle and candidates alike |
| **DOCX to PDF oracle** | SHA-pinned Word-export PDFs (`pdf_accepted_word`, `pdf_redlines_randomized`, `pdf_source`, `pdf_source_randomized`) |
| **Second lens** | `docxide_metrics`: docxide-pdf's own Jaccard / text-boundary metrics on the same fixtures, and the same two columns on every redline row |
| **Stores** | `results/bench.jsonl` (fidelity), `results/converters.jsonl` (DOCX to PDF), `results/speed.jsonl` + `results/redline_speed_bench/` (speed), `results/archive/` (history only) |
| **Results** | [`RESULTS.md`](RESULTS.md) (headline) and [`RESULTS_DETAILED.md`](RESULTS_DETAILED.md) (history, paired comparisons, methodology), both generated |
| **Visual report** | `runs/<run>/report.html` |
| **Speed** | [`docs/SPEED.md`](docs/SPEED.md) |

One row per tool in every headline table: its latest eligible run in the current comparability group (same document set, renderer and scorer). No best pin, no best-of-N. Author-affiliated tools (Jubarte) are marked and follow the same rules. Compare rows only within one table.

```bash
uv run bench report            # regenerates RESULTS.md, RESULTS_DETAILED.md and the vendor table below
uv run bench report --check    # exit 1 when the published views are stale (CI)
```

Candidate and oracle redline PDFs are both rendered with LibreOffice 26.2.4.2; re-rendering the same DOCX is byte-identical on one build (`results/noise_floor.json`). The `oracle-identity` calibration row (`bench calibrate`) is Word's own DOCX through the candidate pipeline and must score 100; the `null-baseline` row is the base document unchanged, the floor a redline tool must beat.

## Results visibility

[`RESULTS.md`](RESULTS.md) is the headline: one table per benchmark, intervals, calibration rows, and the reason for every row that is not ranked. [`RESULTS_DETAILED.md`](RESULTS_DETAILED.md) holds every row in the stores grouped by comparability group with its eligibility verdict, pairwise comparisons, lens-health alarms, and the methodology. Rows that predate provenance stamping, holdout-only runs and retracted runs live in `results/archive/` with a manifest and appear only in the history. The three-way [`renderer corpus`](corpus/no_comments_pdf_was_generated_by_word/renderer_corpus/README.md) contains Word, Jubarte, and docxide-pdf PDFs for the same 398 source DOCX files.

## Benchmarks

Compare vendors only within one table. LibreOffice scores and Playwright scores are separate measurements.

| Benchmark | Input | Oracle |
| --- | --- | --- |
| **`script_redlines`** | `base.docx` + `next.docx` → tool redline DOCX | Word redline PDF |
| **`accepted_changes`** | Accept all `w:ins`/`w:del` on the tool redline | Word redline with changes accepted |
| **`roundtrip`** | Self-diff or the tool’s roundtrip path | Original source PDF (identity = 100) |
| **`visual_rendering`** | Source DOCX in the vendor web editor | `pdf_source` |
| **`visual_redlines`** | Word redline DOCX in the vendor web editor | `pdf_redlines_word` |
| **`visual_accepted_changes`** | Accepted Word redline in the vendor web editor | `pdf_accepted_word` |
| **`docx_to_pdf`** | Accepted Word redline DOCX + randomized redline DOCX | SHA-pinned `pdf_accepted_word` + `pdf_redlines_randomized` |
| **`docx_to_pdf_no_redline_docs`** | Source DOCX + randomized source DOCX | SHA-pinned `pdf_source` + `pdf_source_randomized` |
| **`docxide_metrics`** | The `docx_to_pdf_no_redline_docs` inputs, scored with docxide-pdf's Jaccard / text-boundary metrics at 150 DPI | Same SHA-pinned `pdf_source` + `pdf_source_randomized` |

`visual_*` loads Word's DOCX in the editor, not the tool's own redline. Generator package and editor package are separate pins.

Pins: [`bench.yaml`](bench.yaml). Tool identities: [`bench.registry.yaml`](bench.registry.yaml) (the table below is generated from it).

<!-- VENDORS-START -->
| Tool | Role | Engine | Author-affiliated | Note |
| --- | --- | --- | --- | --- |
| [jubarte (lossless)](https://github.com/jandira-tech/jubarte-redlines) | generator | jubarte-final | yes |  |
| [jubarte (ast)](https://github.com/jandira-tech/jubarte-redlines) | generator | jubarte-final | yes |  |
| [jubarte-rust](https://github.com/jandira-tech/jubarte-redlines) | generator | jubarte-redlines | yes |  |
| [jubarte-wasm](https://github.com/jandira-tech/jubarte-redlines) | generator | jubarte-redlines | yes |  |
| [docxodus](https://github.com/JSv4/docxodus) | generator | docxodus |  |  |
| [docxodus (C#)](https://github.com/JSv4/docxodus) | generator | docxodus |  | C# build of docxodus; speed benchmark only. |
| [folio](https://github.com/stella/folio) | generator | @stll/folio-core |  |  |
| [superdoc](https://github.com/Harbour-Enterprises/SuperDoc) | generator | superdoc-sdk |  |  |
| [docx-redline-js](https://github.com/AnsonLai/docx-redline-js) | generator | docx-redline-js |  |  |
| [redlines](https://github.com/houfu/redlines) | generator | redlines |  |  |
| [superdoc-redlines](https://github.com/yuch85/superdoc-redlines) | generator | superdoc-redlines |  |  |
| [stemma](https://github.com/stemma-sh/stemma) | generator | stemma |  |  |
| [safe-docx](https://github.com/UseJunior/safe-docx) | generator | safe-docx |  |  |
| [docxodus (viewer)](https://github.com/JSv4/react-docxodus-viewer) | editor | react-docxodus-viewer |  |  |
| [folio (viewer)](https://github.com/stella/folio) | editor | @stll/folio-react |  |  |
| [superdoc (editor)](https://github.com/Harbour-Enterprises/SuperDoc) | editor | superdoc |  |  |
| [jubarte](https://github.com/jandira-tech/jubarte-redlines) | converter | jubarte-redlines | yes |  |
| [rdocx](https://github.com/tensorbee/rdocx) | converter | rdocx |  |  |
| [office2pdf](https://github.com/developer0hye/office2pdf) | converter | office2pdf (Typst) |  |  |
| [pdfitdown](https://github.com/AstraBert/PdfItDown) | converter | office2pdf (Typst) |  | Delegates Office formats to office2pdf; same engine, listed for completeness. |
| [doxx](https://github.com/bgreenwell/doxx) | converter | doxx |  | No PDF export; listed as not applicable, never ranked. |
| [libreoffice_convert_rust](https://gitcode.com/dnrops/libreoffice_convert_rust) | converter | LibreOffice |  |  |
| [soffice](https://www.libreoffice.org/) | converter | LibreOffice |  |  |
| [dxpdf](https://github.com/nerdy-pro/dxpdf) | converter | dxpdf |  |  |
| [docxide-pdf](https://github.com/sverrejb/docxide-pdf) | converter | docxide-pdf |  |  |
| [PyMuPDF Pro](https://pymupdf.io/pro) | converter | pymupdf-pro |  | Unlicensed (Restricted Mode): converts only the first 3 pages, so it is scored on the at-most-3-page set. |
<!-- VENDORS-END -->

---

## Quick start

Python 3.14 (`uv`), Bun or Node, LibreOffice 26.2.4.2 on `PATH`.

```bash
uv sync
bun install --frozen-lockfile
cd src/neurotic_docx_bench/utils/docxodus && bun install --frozen-lockfile && cd -
cd src/neurotic_docx_bench/utils/docx-redline-js && bun install --frozen-lockfile && cd -
cd src/neurotic_docx_bench/utils/folio && bun install --frozen-lockfile && cd -
cd src/neurotic_docx_bench/utils/superdoc && bun install --frozen-lockfile && cd -
cd harness/folio-viewer && bun install --frozen-lockfile && cd -

uv run bench run --only jubarte-final-lossless --limit 5
uv run bench run
uv run bench docx-to-pdf --tool jubarte --tool rdocx --tool office2pdf --tool pdfitdown --tool doxx
```

Each `bench run`: resolve `tool_version` → generate → render → score → append `results/bench.jsonl` → gate vs snapshot.

```bash
uv run bench run --only docxodus --limit 5 --no-emit
uv run bench accept-scores jubarte
uv run bench render <docx-dir> <work-dir> -b soffice
uv run bench compare <candidate-pdfs> <oracle-pdfs> --tool name
```

### Try one fixture with your own tool

`bench try` scores any tool on one fixture of the tryout set (100 pairs drawn from the Word-exported corpus, `corpus/tryout/tryout_100.csv`) against the Word oracle, next to jubarte's precomputed output for the same pair. Nothing is written under `results/`.

```bash
uv run bench try list
uv run bench try run --random --task redline --tool "mytool {base} {next} -o {out}" --json out/try.json
uv run bench try run --fixture <pair_stem> --task convert --tool "mytool {input} -o {out}" --renderer soffice
uv run bench try fetch <pair_stem> --dest tryout_dl && uv run bench try run --root tryout_dl --fixture <pair_stem> --tool "..."
```

`--renderer passthrough` (default) expects the tool to write the PDF itself; `soffice` and `word` render a `.docx` output first. `--against` takes another command template or a PDF path instead of jubarte. `--seed` repeats a random pick. `scripts/tryout_jubarte.py` regenerates jubarte's outputs for the set (`bench try build-set` redraws it).

### The Word corpus

Word is the source of truth for PDFs. Everything Word produced lives under `corpus/word/`, built by copy from Word's working folders (`grok_run/`, gitignored), from the July export under `corpus/no_comments_pdf_was_generated_by_word/`, from `corpus/word_based` and its siblings and, when `--fixtures` points at it, from the jubarte-first `_fixtures` folder; the origins stay where they are, nothing is moved or deleted. Only what Word finished is in: docx Word could not open, blacklisted stems and the compares touching them, rejected compares and, in the sets that are Word render runs, documents Word did not render to PDF are left out and listed per set in `PROVENANCE.json`. A PDF whose producer is not Word (LibreOffice, a tool's own writer) is refused.

The tree is laid out by provider and by the state of the docx, read from its XML:

```
corpus/word/
  clean/                      docx/  pdf/  pdf_prior/
  tracking_without_comments/  docx/  pdf/  pdf_prior/
  with_comments_clean/        docx/  pdf/  pdf_prior/
  with_comments_tracking/     docx/  pdf/  pdf_prior/
  documents.csv  comparisons.csv  pools/  notices/  PROVENANCE.json  README.md  MANIFEST.sha256.json
```

`pdf/` holds the current Word render of each docx, `pdf_prior/` the render an earlier Word build made of the same docx, under the same name. A comparison lives in the state of the compared docx.

Every file carries the id of the docx it represents, the first 10 hex digits of the sha256 of the docx bytes. A document is `<id>_<name>`; a Word compare of two documents is `<idA>_<a>__vs__<idB>_<b>_redline_<idC>`, idC being the compare's own id; the Word PDF shares its docx's stem. A tool's output for either is the Word stem plus `_<tool>`, and the scorer keys a candidate by stripping that suffix (`pipeline.redline_key`, `pipeline.render_key`). Names are lower-cased, folded to `[a-z0-9_-]` and cut at 48 characters; the original names are kept in `notices/RENAMED.csv` and in the `names` column of the tables. Byte-identical docx from several origins are one file with every origin name and set recorded on it; two different docx sharing an id fail the build.

| set | what |
| --- | --- |
| `sources_500` | docx-corpus documents with their Word PDF; the stems a later Word build re-rendered keep the earlier render under `pdf_prior/` |
| `en_pairs_500` | the English base/next documents; the first Word pass is the reference, the second pass only fills the stems the first lacks (`filled` in the provenance) |
| `redlines_a100_b10`, `redlines_en_500` | Word compares of those documents (`<base>__vs__<next>`) with the Word PDF of each compared document |
| `word_based`, `word_based_randomized`, `word_redlines_superdoc` | the documents of those folders and Word's compares of their pairs (resolved through `centralized_mapping.csv`) with the September 2026 Word renders of the compares |
| `word_based_0926`, `word_based_randomized_0926`, `word_redlines_superdoc_0926` | the September 2026 compare run: fresh compares of the same pairs with their Word PDFs, other bytes, so other documents |
| `nocomments`, `nocomments_randomized` | the July 2026 Word run with comments stripped: documents and compares with their Word PDFs |
| `fixtures_originals`, `fixtures_word_compares` | the jubarte-first fixtures and Word's compares of them (no Word PDF exists of either); built only with `--fixtures` |

`documents.csv` and `comparisons.csv` list every entry with its id, state, paths, sets, names, sha256 and PDF producer; `comparisons.csv` also carries `key`, `base_id` and `next_id`. `pools/<set>_pairs.csv` (key, base, next, docx, pdf, state) and `pools/<set>_renders.csv` are what `bench.yaml` points a run at. `notices/` holds the rename record, the naming note, the ODC-By-1.0 license and the origins' own notes and logs. `PROVENANCE.json` records origins, counts, what was left out and why, states and the docset id of each set; the tree is pinned by `MANIFEST.sha256.json`. docx and PDF files are gitignored and travel with `bench fixtures upload`; the tables, pools, notices, provenance and manifest are tracked.

```bash
uv run bench corpus build --dry-run     # plan against the origins, copy nothing
uv run bench corpus build               # copy (a clone on APFS), write tables, pools, notices, provenance, manifest
uv run bench corpus build --fixtures /path/to/jubarte-first/_fixtures   # the fixtures sets too
uv run bench corpus check               # verify corpus/word against its manifest (exit 1 on drift)
uv run bench corpus list                # the sets with counts, docset ids and what was left out
```

A destination file whose bytes changed is refused unless `--force`; `--only <set>` builds a subset (a comparison set needs its sources set in the selection).

---

## Scoring

1. Match candidate PDF to oracle PDF by `<base>_<next>` (redlines) or plain stem (`docx_to_pdf`, roundtrip). The denominator is the oracle document set (`results/docsets.json`); a document with no candidate output enters at 0 (intent-to-treat).
2. Raster each page at 144 DPI.
3. Score each page 0 to 100 as a weighted sum: SSIM 40, ink F1 20, edge IoU 15, colour 15, blob 10. A document scores 0.7 times its page mean plus 0.3 times its worst page; "Perfect (100)" counts documents within 1e-6 of 100.

Scoring core is a verbatim lift of [superdoc-visual-benchmarks](https://github.com/superdoc-dev/superdoc-visual-benchmarks); `tests/test_parity.py` checks byte-identical behaviour. Pages present on only one side enter at 0, ink-weighted (`pagefair-v2`), for script_redlines, accepted_changes and roundtrip; the visual_* benchmarks rank on the raw score because cross-engine repagination is expected there. Rank ties: adjacent rows tie when the paired bootstrap interval of their median difference includes 0.

Regression gate (CI tooling, not methodology): 100 always passes; a per-document drop vs the accepted snapshot warns; an aggregate mean or median drop beyond `eps = max(1e-4, 3 sigma)` from `results/noise_floor.json` fails. Promote with `uv run bench accept-scores <tool>`.

### Content cache

`bench run` reuses renders, page rasters and scored rows across runs from `.bench-cache/` (next to `results/`, git-ignored). Entries are keyed by content, never by path: candidate sha256, oracle sha256 (and base sha256 when a base PDF joins the row), DPI, renderer id, and a scorer fingerprint (sha256 over `score.py`, `score_v2.py`, `page_metrics.py`, `pipeline.py`, `raster.py`, the MuPDF build and the cache schema). Editing any scoring source or upgrading PyMuPDF invalidates every score entry on its own; nothing needs clearing by hand.

A row restored from the cache carries `cached: true` and no `raster_ns`/`score_ns`; a restored render has `cached: true` and no `duration_ns`. Timings (`render_s`, `raster_s`, `score_s`, the `visual_*` render-speed stats) therefore come only from fresh work. Rasters are still written under the run's work dir so galleries and diagnostics read them as before.

```bash
uv run bench run --no-cache        # score everything fresh (BENCH_NO_CACHE=1 does the same)
BENCH_CACHE_DIR=/fast/disk uv run bench run
uv run bench cache                 # root, entry counts, size, scorer fingerprint
uv run bench cache --clear
```

`bench compare` never reads the cache.

### Profiling the pipeline

`bench profile` times every stage (generate, render, raster, score) on a seeded sample of documents and prints, per run and benchmark, each stage's count, total, mean, median, p95, max and share of the run, plus the run's wall time and renderer. It is one uncached pass and never a result: nothing is appended to `results/bench.jsonl`, no gate runs, and recorded runs are not skipped.

```bash
uv run bench profile --run jubarte                     # 10 documents, seed 0
uv run bench profile --run jubarte --sample 25 --seed 3 --json out/profile.json
uv run bench profile --roundtrip --accept-compare      # time those stages too
```

The same `--sample` and `--seed` pick the same documents, so two profiles (before and after a scorer change, or CPU against a torch device) compare like for like.

### Torch backend for the scorer kernels

The scorer's two heaviest kernels, the CIEDE2000 colour distance and SSIM, have a torch port behind `--device` on `bench run`, `bench profile` and `bench compare` (the `gpu` extra: `uv sync --extra gpu`). The default is the skimage path, which the parity tests lock byte for byte; the torch path reproduces it within float32 tolerance and is checked against it by `tests/test_kernels.py`.

```bash
uv run bench profile --run jubarte --device mps      # Apple silicon
uv run bench run --device auto                       # cuda, then mps, else the numpy path
```

`auto` is silent when no GPU is present; `cpu`, `mps` and `cuda` fall back to the numpy path with one warning when torch or that device is unavailable. The device is exported as `BENCH_DEVICE` for the command's duration only, so worker processes inherit it; the backend id (`numpy`, `torch-mps`, ...) is part of the content-cache score key, the profile report (`scorer_backend`) and the hardware stamp on every result. On CPU the torch kernels are no faster per core than skimage (each pool worker is limited to its share of the cores), so `--device cpu` is for parity checks; the gain is on a GPU.

---

## Speed methodology

Data: `results/speed.jsonl`, `results/redline_speed_bench/`. Detail: [`docs/SPEED.md`](docs/SPEED.md).

| Mode | Measures |
| --- | --- |
| Warm in-process (`*-inproc`) | Compare work in one long-lived process |
| CLI | Process spawn + init + compare |
| WASM | In-process after load |
| Microbench | Small N × reps |

Large-N (`scripts/redline_speed_bench.ts`): up to 1000 unique `.docx` → 5000 pairs (Mulberry32 seed 42), warmup, `performance.now()`, failures excluded.

```bash
node --import tsx scripts/speed-bench.ts --pairs 30 --reps 3 --out results/speed.jsonl
bun run redline-speed-bench:warm
```

---

## Project map

```
bench.yaml                 # runs, pins, oracles
corpus/word/               # what Word produced, by document state (bench corpus build)
corpus/word_based/         # redline DOCX + LibreOffice oracle PDFs
corpus/no_comments_pdf_was_generated_by_word/  # Word-exported PDFs (docx_to_pdf)
corpus/no_comments_pdf_was_generated_by_word/renderer_corpus/  # Word/Jubarte/docxide PDFs
bench.registry.yaml        # tool identities (one id per spelling in every store)
results/bench.jsonl        # fidelity store (LFS)
results/converters.jsonl   # DOCX to PDF store (one line per report and tool)
results/docsets.json       # document set per benchmark (the ITT denominators)
results/retractions.jsonl  # runs that must never be ranked, with reasons
results/archive/           # legacy rows and their manifest (history only)
src/neurotic_docx_bench/
src/neurotic_docx_bench/ledger/         # registry, rows, policy, stats, tables, build (`bench report`)
scripts/
```

[`AGENTS.md`](AGENTS.md) · [`CONTRIBUTING.md`](CONTRIBUTING.md)

---

## Credits

- [balalofernandez/docx-revisions](https://github.com/balalofernandez/docx-revisions) — accept/reject (`bench accept` / `reject`)
- [superdoc-dev/superdoc-visual-benchmarks](https://github.com/superdoc-dev/superdoc-visual-benchmarks) — scoring core
- [sverrejb/docxide-pdf](https://github.com/sverrejb/docxide-pdf) (Apache-2.0): DOCX→PDF converter and the `docxide_metrics` scorer. Its Jaccard and text-boundary metrics (`tests/common/`) are ported to Python in `src/neurotic_docx_bench/page_metrics.py`, held to upstream's frozen numbers by `tests/test_page_metrics.py`.
- [jandira-tech/jubarte-redlines](https://github.com/jandira-tech/jubarte-redlines) (AGPL-3.0-only) — Jubarte DOCX redline and DOCX→PDF converter
- [JSv4/docxodus](https://github.com/JSv4/docxodus) and [react-docxodus-viewer](https://github.com/JSv4/react-docxodus-viewer) (MIT)
- [AnsonLai/docx-redline-js](https://github.com/AnsonLai/docx-redline-js) (MIT)
- [houfu/redlines](https://github.com/houfu/redlines) (MIT) and [nupunkt](https://github.com/JanWille/nupunkt) — text-level redline baseline
- [yuch85/superdoc-redlines](https://github.com/yuch85/superdoc-redlines) (Apache-2.0)
- [stella/folio](https://github.com/stella/folio) (Apache-2.0)
- [Harbour-Enterprises/SuperDoc](https://github.com/Harbour-Enterprises/SuperDoc) (AGPL-3.0)
- [stemma-sh/stemma](https://github.com/stemma-sh/stemma)
- [UseJunior/safe-docx](https://github.com/UseJunior/safe-docx)
- [tensorbee/rdocx](https://github.com/tensorbee/rdocx)
- [developer0hye/office2pdf](https://github.com/developer0hye/office2pdf)
- [AstraBert/PdfItDown](https://github.com/AstraBert/PdfItDown)
- [bgreenwell/doxx](https://github.com/bgreenwell/doxx)
- [dnrops/libreoffice_convert_rust](https://gitcode.com/dnrops/libreoffice_convert_rust) — LibreOffice-based converter
- [nerdy-pro/dxpdf](https://github.com/nerdy-pro/dxpdf) — Rust DOCX→PDF converter
- [LibreOffice](https://www.libreoffice.org/) (MPL-2.0/LGPL-3+) — pinned renderer used for redline comparisons
- Microsoft Word — proprietary reference renderer; Word is a Microsoft trademark

## License

Scoring core derived from [superdoc-visual-benchmarks](https://github.com/superdoc-dev/superdoc-visual-benchmarks). This repository is **AGPL-3.0-only**. See [`LICENSE`](LICENSE).

Published scores are measurements, not endorsements. Microsoft Word is a trademark of Microsoft.

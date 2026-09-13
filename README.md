# neurotic-docx-bench

Pixel scores of DOCX tools against Microsoft Word oracles.

| | |
| --- | --- |
| **Scores** | 0–100 per document |
| **Redline oracle** | Word tracked-change markup, rendered by LibreOffice 26.2.4.2 |
| **DOCX→PDF oracle** | SHA-pinned Word-export PDFs in `pdf_accepted_word` and `pdf_redlines_randomized` |
| **Second scorer** | `docxide_metrics` — docxide-pdf's own Jaccard / SSIM / text-boundary suite, same fixtures |
| **Trend log** | `results/bench.jsonl` |
| **Results** | [`RESULTS.md`](RESULTS.md) (medium) · [`RESULTS_DETAILED.md`](RESULTS_DETAILED.md) (detailed) · [`docs/RESULTS.md`](docs/RESULTS.md) (published report) |
| **Visual report** | `runs/<run>/report.html` |
| **Speed** | [`docs/SPEED.md`](docs/SPEED.md) |

Jubarte families list best and worst pin per fidelity table. Other vendors list each published pin. Compare rows only within one table and only when `ITT Docs` matches.

```bash
python3 scripts/export-results-md.py          # RESULTS_DETAILED.md + docs/RESULTS.md
bun run update-readme-ranking                 # medium tables in RESULTS.md
uv run bench docx-to-pdf --update-readme      # docx_to_pdf table
uv run bench docxide-metrics --update-readme  # docxide_metrics table (docxide-pdf's scorer)
```

Redline markup is Microsoft Word. Candidate and oracle redline PDFs are both rendered with LibreOffice 26.2.4.2. The oracle DOCX through that pipeline scores 100.

## Results visibility

The README is the minimum-publicity view. Use [`RESULTS.md`](RESULTS.md) for compact
rankings, [`RESULTS_DETAILED.md`](RESULTS_DETAILED.md) for full tables, provenance,
methodology, and benchmark-specific diagnostics, or the [`docs/RESULTS.md`](docs/RESULTS.md)
published report. Generated result scripts write to the appropriate result file rather
than expanding this README.

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
| **`docxide_metrics`** | The `docx_to_pdf_no_redline_docs` inputs, scored with docxide-pdf's Jaccard / SSIM / text-boundary suite at 150 DPI | Same SHA-pinned `pdf_source` + `pdf_source_randomized` |

`visual_*` loads Word’s DOCX in the editor, not the tool’s own redline. Generator package and editor package are separate pins.

Pins: [`bench.yaml`](bench.yaml).

| Vendor | What runs | Pin | Role |
| --- | --- | --- | --- |
| **jubarte** | `dist/jubarte-final` | content-hash | Generator |
| **jubarte-rust** / **jubarte** (`docx_to_pdf`) | `../jubarte-redlines` CLI | content-hash / 0.7.0 | Generator, converter |
| **jubarte-wasm** | wasm-bindgen over `../jubarte-redlines` | artifact + source commit | Generator |
| **docxodus** | npm `docxodus` `compareDocuments` | 9.8.0 | Generator + viewer |
| **folio** | `@stll/folio-core` `generateRedlineDocx` | 0.17.1 | Generator |
| **folio** (viewer) | `@stll/folio-react` | 0.13.4 | Editor |
| **superdoc** | `superdoc-sdk` | 2.0.0 | Generator |
| **superdoc** (editor) | npm `superdoc` | 2.3.0 | Editor |
| **docx-redline-js** | local TS migration of `@ansonlai/docx-redline-js` | dist pin | Generator |
| **redlines** | [houfu/redlines](https://github.com/houfu/redlines) + `nupunkt==0.6.0` | 0.6.1 | Generator |
| **superdoc-redlines** | [yuch85/superdoc-redlines](https://github.com/yuch85/superdoc-redlines) | 0.2.0 | Generator |
| **stemma** | [stemma-sh/stemma](https://github.com/stemma-sh/stemma) `stemma compare` | 0.5.0 | Generator |
| **safe-docx** | [UseJunior/safe-docx](https://github.com/UseJunior/safe-docx) at `7bd35c8` | content-hash | Generator |
| **rdocx** | [tensorbee/rdocx](https://github.com/tensorbee/rdocx) `convert --to pdf` | 0.7.0 | Converter |
| **office2pdf** | [developer0hye/office2pdf](https://github.com/developer0hye/office2pdf) | 0.6.7 | Converter |
| **pdfitdown** | [AstraBert/PdfItDown](https://github.com/AstraBert/PdfItDown) (`office2pdf` for Office) | 4.0.0 | Converter |
| **doxx** | [bgreenwell/doxx](https://github.com/bgreenwell/doxx) | 0.1.4 | Converter (no PDF export) |
| **libreoffice_convert_rust** | [dnrops/libreoffice_convert_rust](https://gitcode.com/dnrops/libreoffice_convert_rust) | 0.1.0 | Converter |
| **dxpdf** | [nerdy-pro/dxpdf](https://github.com/nerdy-pro/dxpdf) | 0.5.1 | Converter |
| **docxide-pdf** | [sverrejb/docxide-pdf](https://github.com/sverrejb/docxide-pdf) | 0.17.0 | Converter |

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

---

## Scoring

1. Match candidate PDF to oracle PDF by `<base>_<next>` (redlines) or plain stem (`docx_to_pdf`, roundtrip).
2. Raster each page at 144 DPI.
3. Score with SSIM, ink-F1, edge-IoU, colour ΔE, and blob metrics (0–100).

Scoring core is a verbatim lift of [superdoc-visual-benchmarks](https://github.com/superdoc-dev/superdoc-visual-benchmarks). `tests/test_parity.py` checks byte-identical behaviour. Page-count mismatch is recorded; only `min(pages)` is scored.

Gate: 100 always passes. Per-document drop vs snapshot → warning. Aggregate mean or median drop → fail. Promote with `uv run bench accept-scores <tool>`.

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
corpus/word_based/         # redline DOCX + LibreOffice oracle PDFs
corpus/no_comments_pdf_was_generated_by_word/  # Word-exported PDFs (docx_to_pdf)
results/bench.jsonl        # redline trend log
results/docx_to_pdf_500.json
src/neurotic_docx_bench/
src/neurotic_docx_bench/utils/docxide-metrics/  # vendored docxide-pdf scorer (Rust)
results/docxide_metrics.json
scripts/
```

[`AGENTS.md`](AGENTS.md) · [`CONTRIBUTING.md`](CONTRIBUTING.md)

---

## Credits

- [balalofernandez/docx-revisions](https://github.com/balalofernandez/docx-revisions) — accept/reject (`bench accept` / `reject`)
- [superdoc-dev/superdoc-visual-benchmarks](https://github.com/superdoc-dev/superdoc-visual-benchmarks) — scoring core
- [sverrejb/docxide-pdf](https://github.com/sverrejb/docxide-pdf) (Apache-2.0) — the `docxide_metrics`
  scorer. Its Jaccard / SSIM / text-boundary metrics are lifted verbatim from `tests/common/`
  into `src/neurotic_docx_bench/utils/docxide-metrics/`; `tests/test_docxide_metrics_parity.py`
  requires the same numbers as its own `page-metrics` binary. Also benchmarked as a converter.
- [JSv4/docxodus](https://github.com/JSv4/docxodus), [react-docxodus-viewer](https://github.com/JSv4/react-docxodus-viewer) (MIT)
- [AnsonLai/docx-redline-js](https://github.com/AnsonLai/docx-redline-js) (MIT)
- [houfu/redlines](https://github.com/houfu/redlines) (MIT)
- [yuch85/superdoc-redlines](https://github.com/yuch85/superdoc-redlines) (Apache-2.0)
- [stella/folio](https://github.com/stella/folio) (Apache-2.0)
- [Harbour-Enterprises/SuperDoc](https://github.com/Harbour-Enterprises/SuperDoc) (AGPL-3.0)
- [stemma-sh/stemma](https://github.com/stemma-sh/stemma)
- [UseJunior/safe-docx](https://github.com/UseJunior/safe-docx)
- [tensorbee/rdocx](https://github.com/tensorbee/rdocx)
- [developer0hye/office2pdf](https://github.com/developer0hye/office2pdf)
- [AstraBert/PdfItDown](https://github.com/AstraBert/PdfItDown)
- [bgreenwell/doxx](https://github.com/bgreenwell/doxx)

## License

Scoring core derived from [superdoc-visual-benchmarks](https://github.com/superdoc-dev/superdoc-visual-benchmarks). This repository is **AGPL-3.0-only**. See [`LICENSE`](LICENSE).

Published scores are measurements, not endorsements. Microsoft Word is a trademark of Microsoft.

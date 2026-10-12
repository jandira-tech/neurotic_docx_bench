# October 2026 renewal (2026-10-11)

How `index.html` (DOCX → PDF) and `redlines/index.html` got their new cases. Page images and the
per-engine PDFs live in the public R2 bucket `neurotic-docx-bench-pages`
(`https://pub-92c80eda1059428394970066c8500eda.r2.dev/`), not in this repo.

| step | script | what it does |
|---|---|---|
| sample | `inventory.py`, `sample.py` (seed 20261011) | language/type/pages inventory of neurotic_docx_bench `corpus/word` (`inv_*.csv`); 800 documents and 1000 compare pairs not shown before, stratified (half English, every Portuguese item) → `sample_docx_to_pdf.csv`, `sample_redlines.csv` |
| tools | `run_tools.py`, `run_docxodus.py` | jubarte 0.12.0 convert / compare, LibreOffice 26.8.0.3, docxodus 12.6.5 (one process per pair, 120 s, run last) |
| Word | neurotic_docx_bench `scripts/word_redline.py`, `scripts/word_pdf.py` | Word 16.115's compare of every pair; Word's PDF of every jubarte and docxodus redline |
| replace | `replace.py`, `chain_replace.sh`, `chain_new.sh` | the 57 pairs Word's compare failed on, replaced from the same stratum (`replace_plan.json`; first sample in `sample_redlines_v1.csv`) |
| score + encode | `process.py` | docxide-pdf page-metrics (J, SSIM, TB) at 150 DPI over every page; every page at 120 DPI as 16-colour WebP; whole-document PDFs (`all.pdf`, mutool clean -gggz); docxide fixtures keep their first 3 pages → `cases_*.json` |
| upload | `upload_r2.py` (R2 API, rate-limited), `upload_worker.py` (through a throwaway Worker with the bucket bound, deleted after use) | skips keys already in the bucket |
| patch | `patch_site.py`, `mark_dropped.py` | applied to the previous commit's HTML: drop the stale jubarte / LibreOffice / docxodus columns, add the new cases, version labels and notes; `dropped` hides a removed engine on the old cases |

`jubarte_redline_scores.json`: jubarte against Word's compare on the first 943 pairs, before the replacements.
The corpus inputs are on the Hugging Face dataset `arthrod/neurotic_docx_bench-fixtures`.

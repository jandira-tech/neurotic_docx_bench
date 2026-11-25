# redlines_winword_600 — set redline_600 against Word for Windows' compare

Run 2026-11-24 (`run_all.sh`, log in `run_all.log`), published 2026-11-25. The run was made in
`results/redline600_contabo/` of the main checkout and copied here under its published name, so
`run_all.sh`, `measure.py` and the log still name that folder: to rebuild here, set `R` in
`run_all.sh` to `results/redlines_winword_600`. Its own tables
(`redlines_vs_windows_word`, `redline_pdf_vs_windows_word`; `tables.SEPARATE_REDLINE_RUNS`):
the oracle is not the one of the other `results/redlines_*` runs, so its figures are never
merged with theirs.

## Oracle

Word 2024 on the Windows endpoint (`contabo_word.py`; endpoint and token from the environment
or the bench root's `.env`, never committed) compares each pair of `pairs.csv` (the 600 pairs of
set redline_600) and exports its own redline to PDF (`word/pdf`). 586 pairs have that reference;
the other 14 are listed under `no_reference` in each `scores_*.json` and are in no test.

## Tests

* redline: each tool's redline DOCX of the pair, exported to PDF by the same Word
  (`<lane>/pdf_by_word`). Word renders both sides, so the redline is the only difference.
  Tools: docxodus 16.1.0 (npm/WASM, `scripts/generate-native-redlines.ts --method docxodus`),
  jubarte 0.20.0 (`jubarte_lanes.py`), folio 0.70.0 with `onUnverified: "emit"`
  (`folio_redlines.ts`), superdoc-sdk 2.31.0 (`neurotic_docx_bench.superdoc_gen`).
  `word-mac` is not a tool: the set's committed oracle (Word for Mac's compare, exported by
  Word for Mac) scored against this one — how far the two Words are apart.
* convert: each converter's PDF of Word's own redline DOCX (`word/docx`) against Word's export
  of that DOCX: docxodus 16.1.0 (`docxodus_pdf.py`) and jubarte 0.20.0 (`jubarte_lanes.py`).

## Scoring

`measure.py`: the bench's verbatim scorer (`pipeline.score_folders_full`), 144 DPI, every page.
A pair with a reference and no candidate PDF counts 0 in the ITT figures. `to_scores_jsonl.py`
turns the seven `scores_<test>.json` summaries into `scores.jsonl` and `versions.json`
unchanged. The tool outputs and rasters are not committed.

Not published: `redline-docxodus-mac`, `word-mac-local` and `convert-word-mac` (`measure.py`
defines them; later diagnostics of the same run, 2026-11-24 evening), which are not in
`run_all.sh`.

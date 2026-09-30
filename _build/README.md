# How this site is built

Scripts run from a workspace holding a docxide-pdf clone (`docxide-pdf/`, built
`page-metrics`), its gh-pages clone (`site/`) and neurotic-docx-bench next to it.

1. `add_jubarte.py`: jubarte 0.9.3 (`convert --revisions word --compress`) on the 208
   docxide-pdf fixtures, scored with docxide-pdf `page-metrics` -> `local_scores.json`.
2. `add_pymupdf.py`: PyMuPDF Pro 1.28.2, unlicensed, fixtures whose Word PDF has at most
   3 pages -> `local_pymupdf.json`.
3. `score_corpus.py`: all 3554 neurotic-docx-bench corpus/word documents, every engine
   against Word's PDF -> `corpus_scores.json`.
4. `build_site.py`: stratified 600-document sample (`sample.json`, seed 20260928),
   MiniPdf / rdocx / office2pdf on it (`corpus_extra_scores.json`), first 3 pages at
   100 DPI as 16-colour lossless WebP, `index.html`.

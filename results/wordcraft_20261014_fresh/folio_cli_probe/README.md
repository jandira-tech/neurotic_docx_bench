# folio-cli 0.5.1 `compare -o` vs the bench's folio-core 0.60.0 lane (2026-10-14)

Three complex pairs from the frozen 400 (049d8405bc: 132 pages/44 tables; 0bc720e5fa: 153 pages/~5k revisions;
e83dabcd41: 4 pages, formatting-heavy). `folio compare BASE NEXT -o OUT --no-expect-version --author folio`.

- folio-cli calls `@stll/folio-agents/compare.generateRedlineDocx`, a pass-through to folio-core 0.60.0's
  `generateRedlineDocx` (the bench lane's call). Outputs are byte-identical per part after removing `w:date`,
  `w14:paraId/textId`, rsids and dcterms dates (`analyze.py`, `analysis.json`).
- Visual score of the lane's Word-rendered PDFs vs Word 16.115 (`folio_visual_scores.json`, torch-mps; these three
  rows were scored ad hoc, the lane's own scoring pass writes the official ones).

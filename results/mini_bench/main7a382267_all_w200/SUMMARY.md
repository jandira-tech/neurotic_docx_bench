# Mini-bench main7a382267_all_w200

200 worst + 50 spread documents of jubarte jubarte 0.9.3 (pixel, run `01a0e620-1acd-737e-b6f0-261fcb02e963`, 3554 documents). Rule: ascending (score, key); worst = first n; spread = midpoint of each of n//4 equal strata of the rest. The list is `selection.csv`.

Every column is intent-to-treat over the selection: a document a tool did not convert counts 0. Pixel is the bench scorer (144 DPI); Jaccard and text boundary are the docxide-pdf metrics (150 DPI).

| Tool | Version | PDFs /250 | Pixel mean | Pixel median | Jaccard mean | Text boundary mean | Pixel mean, worst | Pixel mean, spread |
|---|---|---|---|---|---|---|---|---|
| jubarte | jubarte 0.11.3@7a382267 | 250 | 67.40 | 68.87 | 52.63 | 72.32 | 63.49 | 83.05 |

Scores reused from earlier runs of the same tool version on the same corpus/word documents (pixel lens; the docxide lens reuses the same runs' docxide reports):

- jubarte: 70 of 250 documents reused from `results/mini_bench/main7a382267_le3_w200/reports/jubarte__pixel.json` (70)

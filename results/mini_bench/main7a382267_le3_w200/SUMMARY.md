# Mini-bench main7a382267_le3_w200

200 worst + 50 spread documents of jubarte jubarte 0.9.3 (pixel, run `01a0e901-afd3-7244-8910-9b1e4bb85dd9`, 2626 documents). Rule: ascending (score, key); worst = first n; spread = midpoint of each of n//4 equal strata of the rest. The list is `selection.csv`.

Every column is intent-to-treat over the selection: a document a tool did not convert counts 0. Pixel is the bench scorer (144 DPI); Jaccard and text boundary are the docxide-pdf metrics (150 DPI).

| Tool | Version | PDFs /250 | Pixel mean | Pixel median | Jaccard mean | Text boundary mean | Pixel mean, worst | Pixel mean, spread |
|---|---|---|---|---|---|---|---|---|
| jubarte | jubarte 0.11.3@7a382267 | 250 | 69.48 | 72.46 | 50.45 | 72.28 | 65.25 | 86.39 |

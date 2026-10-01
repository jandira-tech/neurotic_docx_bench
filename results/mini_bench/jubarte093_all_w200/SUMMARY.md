# Mini-bench jubarte093_all_w200

200 worst + 50 spread documents of jubarte jubarte 0.9.3 (pixel, run `01a0e620-1acd-737e-b6f0-261fcb02e963`, 3554 documents). Rule: ascending (score, key); worst = first n; spread = midpoint of each of n//4 equal strata of the rest. The list is `selection.csv`.

Every column is intent-to-treat over the selection: a document a tool did not convert counts 0. Pixel is the bench scorer (144 DPI); Jaccard and text boundary are the docxide-pdf metrics (150 DPI).

| Tool | Version | PDFs /250 | Pixel mean | Pixel median | Jaccard mean | Text boundary mean | Pixel mean, worst | Pixel mean, spread |
|---|---|---|---|---|---|---|---|---|
| libreoffice_convert_rust | LibreOffice Convert Rust v0.1.0 | 249 | 49.54 | 45.11 | 19.25 | 40.62 | 45.98 | 63.80 |
| soffice | LibreOffice 26.8.0.3 bce0998afefdbc355585ca324285661a2170ba77 | 249 | 49.54 | 45.11 | 19.25 | 40.62 | 45.98 | 63.80 |
| jubarte | jubarte 0.10.0@86b6b5d3 | 250 | 48.12 | 42.42 | 24.23 | 43.36 | 40.14 | 80.01 |
| docxide-pdf | docxide-pdf v0.17.1 | 250 | 39.92 | 38.50 | 11.82 | 25.82 | 37.00 | 51.60 |
| genoffice | genoffice 0.11.0 | 250 | 39.92 | 37.37 | 11.67 | 33.63 | 36.34 | 54.23 |
| pdfitdown | pdfitdown 4.0.0 | 250 | 36.72 | 35.25 | 6.69 | 9.50 | 33.13 | 51.07 |
| rdocx | rdocx 0.14.0 | 241 | 34.96 | 36.66 | 4.50 | 11.22 | 32.34 | 45.44 |
| office2pdf | office2pdf 0.8.0 | 250 | 33.83 | 33.99 | 7.31 | 10.32 | 29.75 | 50.15 |
| office2pdf-lib | office2pdf 0.8.0 (library, tools/d2p-warm) | 250 | 33.83 | 33.99 | 7.31 | 10.32 | 29.75 | 50.15 |
| pymupdf-pro (first 3 pages only) | pymupdf-pro 1.28.2 (unlicensed, first 3 pages) | 238 | 31.79 | 32.83 | 15.02 | 33.68 | 26.17 | 54.28 |
| dxpdf | dxpdf 0.8.1 | 160 | 26.39 | 36.65 | 6.11 | 16.44 | 22.72 | 41.05 |
| doxx | doxx 0.1.4 | 0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

pymupdf-pro (unlicensed) converts only the first 3 pages: 145 of 250 selected documents are longer, and on those it is scored on its 3 pages only.

Scores reused from earlier runs of the same tool version on the same corpus/word documents (pixel lens; the docxide lens reuses the same runs' docxide reports):

- jubarte: 70 of 250 documents reused from `results/mini_bench/jubarte093_le3_w200/reports/jubarte__pixel.json` (70)
- docxide-pdf: 250 of 250 documents reused from `01a0e8ac-134b-74b6-ac26-c4c4db671ad5 (results/docx_to_pdf_docxide_0.17.1.json)` (250)
- soffice: 250 of 250 documents reused from `01a0e900-ae28-746f-aa03-fbd7f6b98aab (results/docx_to_pdf_soffice_26.8.0.3.json)` (250)
- office2pdf: 70 of 250 documents reused from `results/mini_bench/jubarte093_le3_w200/reports/office2pdf__pixel.json` (70)
- office2pdf-lib: 70 of 250 documents reused from `results/mini_bench/jubarte093_le3_w200/reports/office2pdf-lib__pixel.json` (70)
- genoffice: 70 of 250 documents reused from `results/mini_bench/jubarte093_le3_w200/reports/genoffice__pixel.json` (70)
- rdocx: 70 of 250 documents reused from `results/mini_bench/jubarte093_le3_w200/reports/rdocx__pixel.json` (70)
- dxpdf: 70 of 250 documents reused from `results/mini_bench/jubarte093_le3_w200/reports/dxpdf__pixel.json` (70)
- pdfitdown: 70 of 250 documents reused from `results/mini_bench/jubarte093_le3_w200/reports/pdfitdown__pixel.json` (70)
- libreoffice_convert_rust: 70 of 250 documents reused from `results/mini_bench/jubarte093_le3_w200/reports/libreoffice_convert_rust__pixel.json` (70)
- doxx: 70 of 250 documents reused from `results/mini_bench/jubarte093_le3_w200/reports/doxx__pixel.json` (70)
- pymupdf-pro: 105 of 250 documents reused from `01a0e8f9-ee84-7370-a80a-facf0504133c (results/docx_to_pdf_le3pages_pymupdf-pro_1.28.2.json)` (105)

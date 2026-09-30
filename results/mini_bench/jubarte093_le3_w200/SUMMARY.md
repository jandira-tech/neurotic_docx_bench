# Mini-bench jubarte093_le3_w200

200 worst + 50 spread documents of jubarte jubarte 0.9.3 (pixel, run `01a0e901-afd3-7244-8910-9b1e4bb85dd9`, 2626 documents). Rule: ascending (score, key); worst = first n; spread = midpoint of each of n//4 equal strata of the rest. The list is `selection.csv`.

Every column is intent-to-treat over the selection: a document a tool did not convert counts 0. Pixel is the bench scorer (144 DPI); Jaccard and text boundary are the docxide-pdf metrics (150 DPI).

| Tool | Version | PDFs /250 | Pixel mean | Pixel median | Jaccard mean | Text boundary mean | Pixel mean, worst | Pixel mean, spread |
|---|---|---|---|---|---|---|---|---|
| jubarte | jubarte 0.10.0@86b6b5d3 | 250 | 55.28 | 50.69 | 32.22 | 48.51 | 48.08 | 84.10 |
| soffice | LibreOffice 26.8.0.3 bce0998afefdbc355585ca324285661a2170ba77 | 249 | 54.28 | 50.00 | 22.55 | 51.85 | 50.61 | 68.96 |
| libreoffice_convert_rust | LibreOffice Convert Rust v0.1.0 | 249 | 54.28 | 50.00 | 22.55 | 51.85 | 50.60 | 68.96 |
| pymupdf-pro | pymupdf-pro 1.28.2 (unlicensed, first 3 pages) | 246 | 48.83 | 46.85 | 18.38 | 31.59 | 44.91 | 64.53 |
| genoffice | genoffice 0.11.0 | 250 | 48.03 | 45.29 | 15.95 | 39.04 | 44.09 | 63.81 |
| docxide-pdf | docxide-pdf v0.17.1 | 250 | 46.52 | 44.86 | 15.33 | 27.88 | 43.47 | 58.73 |
| pdfitdown | pdfitdown 4.0.0 | 248 | 41.62 | 40.38 | 8.97 | 15.25 | 38.56 | 53.86 |
| office2pdf | office2pdf 0.8.0 | 250 | 41.20 | 39.51 | 9.36 | 16.91 | 37.77 | 54.91 |
| office2pdf-lib | office2pdf 0.8.0 (library, tools/d2p-warm) | 250 | 41.20 | 39.51 | 9.36 | 16.91 | 37.77 | 54.91 |
| rdocx | rdocx 0.14.0 | 242 | 40.82 | 41.16 | 8.19 | 18.64 | 38.25 | 51.10 |
| dxpdf | dxpdf 0.8.1 | 221 | 39.61 | 42.77 | 10.86 | 24.16 | 36.29 | 52.90 |
| doxx | doxx 0.1.4 | 0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

Scores reused from earlier runs of the same tool version on the same corpus/word documents (pixel lens; the docxide lens reuses the same runs' docxide reports):

- docxide-pdf: 250 of 250 documents reused from `01a0e8ac-134b-74b6-ac26-c4c4db671ad5 (results/docx_to_pdf_docxide_0.17.1.json)` (250)
- soffice: 250 of 250 documents reused from `01a0e900-ae28-746f-aa03-fbd7f6b98aab (results/docx_to_pdf_soffice_26.8.0.3.json)` (250)
- pymupdf-pro: 250 of 250 documents reused from `01a0e8f9-ee84-7370-a80a-facf0504133c (results/docx_to_pdf_le3pages_pymupdf-pro_1.28.2.json)` (250)

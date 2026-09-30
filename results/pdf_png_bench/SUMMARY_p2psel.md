# PDF->PNG bench: p2psel

Oracle: LibreOffice 26.8.0.3 bce0998afefdbc355585ca324285661a2170ba77 page PNGs of each Word PDF (144 DPI, PyMuPDF's pixel size per page). 3 of 3 documents have an oracle; the rest are listed below and not scored. Every column is intent-to-treat over those documents: a failed document counts 0. Pixel is the bench scorer, Jaccard the docxide-pdf ink Jaccard on the same rasters. ms per page is the median wall time on a shared machine (indicative only).

| Tool | Version | Input | OK | Pixel mean | Pixel median | Jaccard mean | ms per page | Pages resized |
|---|---|---|---|---|---|---|---|---|
| jubarte | jubarte 0.10.0@86b6b5d3 (from the DOCX) | docx | 3/3 | 60.22 | 66.25 | 28.10 | 125.9 | 0 |
| pymupdf | pymupdf 1.28.0 (MuPDF 1.29.0) | pdf | 3/3 | 57.16 | 51.09 | 38.38 | 116.8 | 0 |
| mutool | mutool version 1.28.5 | pdf | 3/3 | 57.16 | 51.09 | 38.38 | 120.4 | 0 |
| pdftoppm | pdftoppm version 26.09.0 | pdf | 3/3 | 56.88 | 50.87 | 35.74 | 512.2 | 0 |

The oracle itself: 3753.6 ms per page (median; one soffice call per page).

jubarte cannot read a PDF: it converts the DOCX each Word PDF was exported from. Its row measures its own layout plus rasterization against LibreOffice's raster of Word's layout, not PDF rasterization, so it is not comparable with the other rows.

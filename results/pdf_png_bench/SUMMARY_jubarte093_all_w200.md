# PDF->PNG bench: jubarte093_all_w200

250 Word PDFs of the mini-bench selection `jubarte093_all_w200`, rasterized at 144 DPI (PyMuPDF's pixel size per page). One table per oracle. Every column is intent-to-treat over the documents that oracle rendered: a failed document counts 0. Pixel is the bench scorer, Jaccard the docxide-pdf ink Jaccard (0 to 100) on the same rasters. ms per page is the median wall time on a shared machine (indicative only).

LibreOffice does not rasterize a PDF: it imports it as editable text boxes and lays the text out again with its own font metrics (justified lines get other word spacing). Against LibreOffice, a tool scores its closeness to that re-layout; the PyMuPDF table scores closeness to the PDF as MuPDF draws it, with LibreOffice as one of the candidates.

## Oracle: libreoffice (LibreOffice 26.8.0.3 bce0998afefdbc355585ca324285661a2170ba77)

250 of 250 documents have this oracle.

| Tool | Version | Input | OK | Pixel mean | Pixel median | Jaccard mean | ms per page | Pages resized |
|---|---|---|---|---|---|---|---|---|
| pymupdf | pymupdf 1.28.0 (MuPDF 1.29.0) | pdf | 250/250 | 48.46 | 44.90 | 23.08 | 44.7 | 0 |
| mutool | mutool version 1.28.5 | pdf | 250/250 | 48.46 | 44.90 | 23.08 | 56.3 | 0 |
| pdftoppm | pdftoppm version 26.09.0 | pdf | 250/250 | 48.18 | 44.72 | 21.29 | 323.5 | 0 |
| jubarte | jubarte 0.10.0@86b6b5d3 (from the DOCX) | docx | 250/250 | 44.20 | 40.48 | 13.84 | 42.3 | 24 |

libreoffice itself: 1411.6 ms per page (median).

## Oracle: pymupdf (pymupdf 1.28.0 (MuPDF 1.29.0))

250 of 250 documents have this oracle.

| Tool | Version | Input | OK | Pixel mean | Pixel median | Jaccard mean | ms per page | Pages resized |
|---|---|---|---|---|---|---|---|---|
| mutool | mutool version 1.28.5 | pdf | 250/250 | 100.00 | 100.00 | 100.00 | 56.3 | 0 |
| pdftoppm | pdftoppm version 26.09.0 | pdf | 250/250 | 87.10 | 86.83 | 77.55 | 323.5 | 0 |
| jubarte | jubarte 0.10.0@86b6b5d3 (from the DOCX) | docx | 250/250 | 48.82 | 43.61 | 24.24 | 42.3 | 24 |
| libreoffice | LibreOffice 26.8.0.3 bce0998afefdbc355585ca324285661a2170ba77 | pdf | 250/250 | 48.48 | 44.98 | 23.08 | 1411.6 | 0 |

pymupdf itself: 44.7 ms per page (median).

jubarte cannot read a PDF: it converts the DOCX each Word PDF was exported from. Its rows measure its own layout plus rasterization, not PDF rasterization, so they are not comparable with the other rows.

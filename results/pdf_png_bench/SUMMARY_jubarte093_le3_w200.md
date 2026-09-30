# PDF->PNG bench: jubarte093_le3_w200

250 Word PDFs of the mini-bench selection `jubarte093_le3_w200`, rasterized at 144 DPI (PyMuPDF's pixel size per page). One table per oracle. Every column is intent-to-treat over the documents that oracle rendered: a failed document counts 0. Pixel is the bench scorer, Jaccard the docxide-pdf ink Jaccard (0 to 100) on the same rasters. ms per page is the median wall time on a shared machine (indicative only).

LibreOffice does not rasterize a PDF: it imports it as editable text boxes and lays the text out again with its own font metrics (justified lines get other word spacing). Against LibreOffice, a tool scores its closeness to that re-layout; the PyMuPDF table scores closeness to the PDF as MuPDF draws it, with LibreOffice as one of the candidates.

## Oracle: libreoffice (LibreOffice 26.8.0.3 bce0998afefdbc355585ca324285661a2170ba77)

250 of 250 documents have this oracle.

| Tool | Version | Input | OK | Pixel mean | Pixel median | Jaccard mean | ms per page | Pages resized |
|---|---|---|---|---|---|---|---|---|
| pymupdf | pymupdf 1.28.0 (MuPDF 1.29.0) | pdf | 250/250 | 58.34 | 52.06 | 35.58 | 43.3 | 0 |
| mutool | mutool version 1.28.5 | pdf | 250/250 | 58.34 | 52.06 | 35.58 | 64.8 | 0 |
| pdftoppm | pdftoppm version 26.09.0 | pdf | 250/250 | 57.82 | 51.68 | 32.57 | 313.2 | 0 |
| jubarte | jubarte 0.10.0@86b6b5d3 (from the DOCX) | docx | 250/250 | 49.66 | 45.74 | 19.74 | 51.1 | 0 |

libreoffice itself: 1312.6 ms per page (median).

## Oracle: pymupdf (pymupdf 1.28.0 (MuPDF 1.29.0))

250 of 250 documents have this oracle.

| Tool | Version | Input | OK | Pixel mean | Pixel median | Jaccard mean | ms per page | Pages resized |
|---|---|---|---|---|---|---|---|---|
| mutool | mutool version 1.28.5 | pdf | 250/250 | 100.00 | 100.00 | 100.00 | 64.8 | 0 |
| pdftoppm | pdftoppm version 26.09.0 | pdf | 250/250 | 86.58 | 86.54 | 76.76 | 313.2 | 0 |
| libreoffice | LibreOffice 26.8.0.3 bce0998afefdbc355585ca324285661a2170ba77 | pdf | 250/250 | 58.14 | 52.08 | 35.58 | 1312.6 | 0 |
| jubarte | jubarte 0.10.0@86b6b5d3 (from the DOCX) | docx | 250/250 | 55.35 | 50.61 | 30.95 | 51.1 | 0 |

pymupdf itself: 43.3 ms per page (median).

jubarte cannot read a PDF: it converts the DOCX each Word PDF was exported from. Its rows measure its own layout plus rasterization, not PDF rasterization, so they are not comparable with the other rows.

# Outreach List — Tools to Open the Badge Issue Against

One GitHub issue per repository below, using [`ISSUE_TEMPLATE.md`](ISSUE_TEMPLATE.md) with the
tool's opener line pasted in. Never cite a tool's scores or ranking in an issue. Do **not**
open issues on jubarte (author-affiliated, marked `†` in every table) or on the calibration rows.

Badge image URLs are `raw.githubusercontent.com/jandira-tech/neurotic_docx_bench/main/docs/badges/<file>.svg`
and resolve as soon as `main` carries this folder.

## Redline / comparison generators

| # | Tool | Repository (open issue here) | Benched identities | Opener line (paste into the issue) | Badge options |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | docxodus | [JSv4/docxodus](https://github.com/JSv4/docxodus) | docxodus 12.6.5, 13.0.0, C# speed build | docxodus is the most-benched third-party tool in the suite — three generator lanes (12.6.5, 13.0.0 and a C# build) plus its own React viewer in the visual editor benchmarks. | **1–7 + 8 (Michigan maize & blue, custom)** |
| 2 | docxodus viewer | [JSv4/react-docxodus-viewer](https://github.com/JSv4/react-docxodus-viewer) | docxodus (viewer) | react-docxodus-viewer is the only third-party DOCX viewer with dedicated Playwright visual lanes — rendering, redlines and accepted changes. | 1–7 |
| 3 | SuperDoc | [Harbour-Enterprises/SuperDoc](https://github.com/Harbour-Enterprises/SuperDoc) | superdoc-sdk 2.20.0, superdoc (editor) | The bench stands on SuperDoc's shoulders: the public corpus is superdoc-dev/docx-corpus and the pixel-scoring core is a verbatim lift of superdoc-visual-benchmarks, held byte-identical by parity tests — and SuperDoc is benched both as an SDK and as a live editor. | 1–7 |
| 4 | folio | [stella/folio](https://github.com/stella/folio) | folio-core 0.60.0, folio, folio (viewer) | folio is benched twice over — as a generator (folio-core 0.60.0) and as a live editor rendering Word's own DOCX in the visual benchmarks. | 1–7 |
| 5 | stemma | [stemma-sh/stemma](https://github.com/stemma-sh/stemma) | stemma 0.6.0 | stemma 0.6.0 is part of the fresh 2026-10-14 cohort of 400 comparisons against newly generated Word 16.115 oracles. | 1–7 |
| 6 | Wordcraft | [storytold/wordcraft](https://github.com/storytold/wordcraft) | Wordcraft CLI 0.6.1, 0.7.0 | The 2026-10-14 fresh cohort (400 comparisons and 400 conversions) was built around Wordcraft, with both release lanes — 0.6.1 and 0.7.0 — followed side by side. | 1–7 |
| 8 | redlines | [houfu/redlines](https://github.com/houfu/redlines) | redlines | redlines (with nupunkt) serves as the suite's text-level redline baseline — the lane every XML-level engine sits next to. | 1–7 |
| 9 | superdoc-redlines | [yuch85/superdoc-redlines](https://github.com/yuch85/superdoc-redlines) | superdoc-redlines | superdoc-redlines is an Apache-2.0 generator in the ranked cohort. | 1–7 |
| 10 | safe-docx | [UseJunior/safe-docx](https://github.com/UseJunior/safe-docx) | safe-docx | safe-docx is one of the comparison generators in the ranked cohort. | 1–7 |

## DOCX → PDF converters

| # | Tool | Repository (open issue here) | Benched identities | Opener line (paste into the issue) | Badge options |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 11 | docxide-pdf | [sverrejb/docxide-pdf](https://github.com/sverrejb/docxide-pdf) | docxide-pdf 0.18.4 | docxide-pdf is not just a converter lane: the whole `docxide_metrics` second lens is built from its Jaccard and text-boundary metrics, ported to Python and held to upstream's frozen numbers by tests. | 1–7 |
| 12 | rdocx | [tensorbee/rdocx](https://github.com/tensorbee/rdocx) | rdocx 0.16.0 | rdocx 0.16.0 is part of the fresh 2026-10-14 conversion cohort. | 1–7 |
| 13 | office2pdf | [developer0hye/office2pdf](https://github.com/developer0hye/office2pdf) | office2pdf 0.8.1 | office2pdf 0.8.1 anchors the Typst-based lane of the conversion cohort. | 1–7 |
| 14 | pdfitdown | [AstraBert/PdfItDown](https://github.com/AstraBert/PdfItDown) | pdfitdown 4.2.0 | pdfitdown 4.2.0 is in the fresh conversion cohort (it delegates Office formats to office2pdf, and the registry says so for completeness). | 1–7 |
| 15 | dxpdf | [nerdy-pro/dxpdf](https://github.com/nerdy-pro/dxpdf) | dxpdf | dxpdf represents the Rust DOCX→PDF lane of the converter benchmark. | 1–7 |
| 16 | libreoffice_convert_rust | [dnrops/libreoffice_convert_rust](https://gitcode.com/dnrops/libreoffice_convert_rust) | libreoffice_convert_rust 0.1.0 | libreoffice_convert_rust 0.1.0 is in the fresh conversion cohort as the LibreOffice-backed Rust lane. ⚠ hosted on GitCode, not GitHub — check the repo has an issues tab before pasting the GitHub-style template. | 1–7 |

The `docx-redline-js` outreach row was removed: dropped in #88 on 2026-10-28;
its migration-kit sibling dependency is unavailable. Historical results remain.

## On hold (decide before sending)

| Tool | Where | Why held |
| :--- | :--- | :--- |
| doxx | [bgreenwell/doxx](https://github.com/bgreenwell/doxx) | Listed as not applicable (no PDF export), never ranked — participation is nominal; a "benched" badge would overstate it. Send only if a PDF path lands. |
| PyMuPDF Pro | [pymupdf.io/pro](https://pymupdf.io/pro) | Commercial product, benched in unlicensed Restricted Mode (first 3 pages); issues would land in the open-source pymupdf/PyMuPDF repo, which was not what was measured. |
| soffice / LibreOffice | [libreoffice.org](https://www.libreoffice.org/) | Bugzilla, not GitHub; also the bench's historical renderer, so a participant badge reads oddly. |

Excluded entirely: jubarte in every identity (author's own tool), the calibration rows
(`oracle-identity`, `null-baseline`) and retired identities (`ooxmlsdk`, `prebaked`, …).

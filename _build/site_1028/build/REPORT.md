# 2026-10-28 review-site build report

PARTIAL: missing redlines.

Assets: 55,385 files, 3.053 GiB. Build tree after temporary-file cleanup: 3.083 GiB.

Scores are percentages. Pixel is copied exactly from the recorded bench score, with recorded ITT zeros. J/SSIM/TB means use available upstream values (rounded to one decimal per case, as site_1011 does); each metric has its own n. All PDF pages are rasterized at 150 DPI; upstream ignores extra pages and skips incompatible page dimensions or text layouts. No missing metric is imputed as zero.

## v1 — 2,925 cases

| Group | Cases |
|---|---:|
| v1/clean | 2,478 |
| v1/tracking_without_comments | 237 |
| v1/with_comments_clean | 112 |
| v1/with_comments_tracking | 98 |

| Engine | PDFs | Failures | Unavailable | Pixel (n) | J (n) | SSIM (n) | TB (n) |
|---|---:|---:|---:|---:|---:|---:|---:|
| docxodus | 2750 | 175 | 0 | 57.5046 (2925) | 31.2721 (2714) | 47.1284 (2714) | 69.4379 (2576) |
| jubarte | 2925 | 0 | 0 | 84.4642 (2925) | 73.7951 (2925) | 87.5565 (2925) | 91.3593 (2893) |
| libreoffice | 2924 | 1 | 0 | 65.5113 (2925) | 29.6706 (2924) | 60.0239 (2924) | 75.4674 (2820) |

## wordcraft_compare — 400 cases

| Group | Cases |
|---|---:|
| wordcraft1014/compare | 400 |

| Engine | PDFs | Failures | Unavailable | Pixel (n) | J (n) | SSIM (n) | TB (n) |
|---|---:|---:|---:|---:|---:|---:|---:|
| docxodus-12.6.5 | 369 | 31 | 0 | 67.1946 (400) | 65.8312 (368) | 74.0177 (368) | 76.0868 (355) |
| docxodus-13.0.0 | 379 | 21 | 0 | 67.9066 (400) | 63.6740 (377) | 71.9767 (377) | 74.7744 (359) |
| folio-0.60.0 | 257 | 143 | 0 | 33.6951 (400) | 16.4943 (227) | 30.1335 (227) | 24.5140 (172) |
| jubarte-0.11.0 | 399 | 1 | 0 | 76.9008 (400) | 76.4068 (399) | 83.4216 (399) | 83.6670 (391) |
| jubarte-0.12.0 | 395 | 5 | 0 | 76.3373 (400) | 76.6506 (395) | 83.8671 (395) | 83.7541 (386) |
| stemma-0.5.0 | 0 | 0 | 400 | — (0) | — (0) | — (0) | — (0) |
| stemma-0.6.0 | 108 | 292 | 0 | 18.9496 (400) | 43.2759 (108) | 59.2500 (108) | 49.7207 (87) |
| superdoc-2.20.0 | 36 | 364 | 0 | 5.3312 (400) | 17.0167 (36) | 30.9944 (36) | 22.2250 (8) |
| wordcraft | 392 | 8 | 0 | 47.3221 (400) | 12.3432 (329) | 25.8982 (329) | 18.8808 (276) |
| wordcraft-0.7.0 | 392 | 8 | 0 | 47.3590 (400) | 12.3462 (329) | 25.8936 (329) | 18.8808 (276) |

## wordcraft_convert — 400 cases

| Group | Cases |
|---|---:|
| wordcraft1014/convert | 400 |

| Engine | PDFs | Failures | Unavailable | Pixel (n) | J (n) | SSIM (n) | TB (n) |
|---|---:|---:|---:|---:|---:|---:|---:|
| docxide-pdf-0.18.4 | 400 | 0 | 0 | 55.8975 (400) | 20.1348 (400) | 36.0860 (400) | 57.4290 (310) |
| jubarte-0.11.0 | 400 | 0 | 0 | 76.2386 (400) | 57.3850 (400) | 74.9412 (400) | 81.9443 (366) |
| jubarte-0.12.0 | 400 | 0 | 0 | 79.9301 (400) | 66.2090 (400) | 84.0333 (400) | 89.0325 (397) |
| libreoffice_convert_rust-0.1.0 | 398 | 2 | 0 | 54.8216 (400) | 17.7188 (398) | 38.7839 (398) | 62.7626 (366) |
| office2pdf-0.8.1 | 398 | 2 | 0 | 48.6600 (400) | 13.4771 (367) | 24.6842 (367) | 43.0675 (295) |
| pdfitdown-4.2.0 | 397 | 3 | 0 | 43.4833 (400) | 3.1918 (366) | 13.3904 (366) | 37.2805 (195) |
| pymupdf-pro-1.28.2 | 250 | 3 | 0 | 56.4786 (253) | 18.9696 (250) | 29.5452 (250) | 66.9047 (170) |
| rdocx-0.16.0 | 397 | 3 | 0 | 50.6879 (400) | 15.1272 (397) | 25.6879 (397) | 49.9297 (300) |
| soffice | 398 | 2 | 0 | 54.8173 (400) | 17.7085 (398) | 38.7842 (398) | 62.7626 (366) |
| wordcraft | 400 | 0 | 0 | 55.4605 (400) | 17.7133 (400) | 35.3855 (400) | 49.3795 (341) |
| wordcraft-0.7.0 | 400 | 0 | 0 | 56.5905 (400) | 19.8137 (400) | 37.9755 (400) | 51.0695 (341) |

## Source and preview boundaries

Upstream: docxide-pdf a72d91bca065be5c96b659e5daadc3cf3ffc9fb2. Wordcraft metadata and selected PDFs are checked against the public MANIFEST.sha256.txt and score-record hashes. No live viewer edits, uploads, commits, or pushes. Eight old accept/reject cases map to the same split pairs; the other five are distinct and remain.

The 800 split score records exist, but their candidate PDFs are absent locally and in the current `redlines-0929` hub preset. That preset has the older 100+100 run (598 candidate PDFs across four lanes), not the split run. Candidate sources are required to build this set without substituting different outputs.

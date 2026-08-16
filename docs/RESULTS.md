# Benchmark results

Source: `results/bench.jsonl` — **66** fidelity row(s) (one per vendor×benchmark×**version**; 40 distinct vendor×version pin(s). docxodus rows with n_docs ≤ 100 are dropped as smoke/partial).

Scores are 0–100 (higher = closer to the Microsoft Word oracle). Cross-renderer comparisons (LibreOffice vs Playwright) are **not** directly comparable — only compare within the same benchmark. Different **versions** of the same vendor are kept so you can compare pins (e.g. docxodus 6.4.0 vs 7.0.0).

## Rankings by benchmark

### `script_redlines`

script_redlines (LibreOffice render vs Word oracle)

**Current corpus** (newest `corpus_revision` stamp: `5ed816028d99`):

| # | vendor | version | mean | median | itt_mean | itt_median | skill_median | failures | n_docs | itt_n | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | jubarte-rust | jubarte-rust@17ea47e9a0d7+git.bf3d07ddd61180e55f327c8e891affd0f6c18d64 | 84.4662 | 92.6623 | 84.4662 | 92.6623 | 93.199 | 0 | 763 | 763 | 197 | 419 | 29 |
| 2 | jubarte | jubarte-final@951a6e6b453c+git.98e641b1f2ef3fa9b4416b197a4494cd6401fb9a | 81.9937 | 91.3062 | 81.9937 | 91.3062 | 83.7884 | 0 | 763 | 763 | 186 | 393 | 67 |
| 3 | docxodus | 9.8.0 | 80.5534 | 91.1892 | 80.2367 | 91.108 | 100 | 4 | 760 | 763 | 186 | 392 | 95 |
| 4 | jubarte | jubarte-final@2140d6727f0d+git.98e641b1f2ef3fa9b4416b197a4494cd6401fb9a | 81.9552 | 91.0482 | 81.9552 | 91.0482 | 82.7849 | 0 | 763 | 763 | 185 | 391 | 67 |
| 5 | jubarte | jubarte-final@c34fd18ff82b+git.98e641b1f2ef3fa9b4416b197a4494cd6401fb9a | 81.9545 | 91.0482 | 81.9545 | 91.0482 | 82.7849 | 0 | 763 | 763 | 185 | 391 | 67 |
| 6 | jubarte | jubarte-final@14094d7b65aa+git.98e641b1f2ef3fa9b4416b197a4494cd6401fb9a | 81.8985 | 90.7573 | 81.8985 | 90.7573 | 81.0457 | 0 | 763 | 763 | 184 | 388 | 67 |
| 7 | jubarte | jubarte-final@c437ad72f0d8+git.98e641b1f2ef3fa9b4416b197a4494cd6401fb9a | 81.7809 | 90.46 | 81.7809 | 90.46 | 80.6956 | 0 | 763 | 763 | 178 | 384 | 67 |
| 8 | jubarte | jubarte-final@c43ad9297820+git.98e641b1f2ef3fa9b4416b197a4494cd6401fb9a | 81.76 | 90.1976 | 81.76 | 90.1976 | 78.3932 | 0 | 763 | 763 | 180 | 382 | 67 |
| 9 | jubarte | jubarte-final@c4de03e2da52+git.98e641b1f2ef3fa9b4416b197a4494cd6401fb9a | 81.6772 | 89.4571 | 81.6772 | 89.4571 | 74.1998 | 0 | 763 | 763 | 160 | 377 | 67 |
| 10 | jubarte | jubarte-final@774e5a062abc+git.98e641b1f2ef3fa9b4416b197a4494cd6401fb9a | 81.647 | 89.3249 | 81.647 | 89.3249 | 80.6956 | 0 | 763 | 763 | 173 | 377 | 67 |
| 11 | jubarte | jubarte-final@700ad3b32181+git.98e641b1f2ef3fa9b4416b197a4494cd6401fb9a | 81.6469 | 89.3249 | 81.6469 | 89.3249 | 80.6956 | 0 | 763 | 763 | 172 | 377 | 67 |
| 12 | jubarte | jubarte-final@76e503aae6c0+git.98e641b1f2ef3fa9b4416b197a4494cd6401fb9a | 81.5594 | 89.1671 | 81.5594 | 89.1671 | 77.3519 | 0 | 763 | 763 | 181 | 376 | 67 |
| 13 | jubarte | jubarte-final@02df62305cf3+git.98e641b1f2ef3fa9b4416b197a4494cd6401fb9a | 81.5586 | 89.1671 | 81.5586 | 89.1671 | 78.3932 | 0 | 763 | 763 | 180 | 376 | 67 |
| 14 | jubarte | jubarte-final@e7bcd29bb5a9+git.98e641b1f2ef3fa9b4416b197a4494cd6401fb9a | 81.5698 | 89.1133 | 81.5698 | 89.1133 | 77.3519 | 0 | 763 | 763 | 182 | 375 | 66 |
| 15 | stemma | 0.5.0@2e7bdc832391+git.efaed0c1ecb41142b1465bbb124dd183c385a2b0 | 62.9106 | 61.8327 | 50.6253 | 56.6151 | 19.3181 | 149 | 614 | 763 | 9 | 39 | 131 |
| 16 | safe-docx | 0.19.1@e3f092da3639+git.7bd35c876493f2725b095f0190c28d2644962c78 | 53.6532 | 51.3113 | 48.3793 | 49.6861 | 4.2245 | 75 | 688 | 763 | 6 | 18 | 317 |
| 17 | redlines | 0.6.1 | 45.9391 | 47.1411 | 44.8554 | 47.0451 | -2.9557 | 18 | 745 | 763 | 0 | 0 | 488 |

**Legacy corpus** (older `corpus_revision` stamps and unstamped runs — not comparable with the rows above; kept for history until each tool re-runs):

| # | vendor | version | mean | median | itt_mean | itt_median | skill_median | failures | n_docs | itt_n | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | 9.0.0 | 80.5535 | 91.1892 | 80.2368 | 91.108 | 100 | 4 | 760 | 763 | 186 | 392 | 95 |
| 2 | jubarte-wasm | 0.1.0@4b36f4db1d2f+git.ebf1a7996df49f99fb40f4f67713e61cfd19c731 | 79.5678 | 84.8864 | 79.5678 | 84.8864 | 89.1943 | 0 | 763 | 763 | 182 | 344 | 72 |
| 3 | jubarte | jubarte-final@d43557e042c1 | 77.0151 | 78.5311 | 77.0151 | 78.5311 | 53.0737 | 0 | 763 | 763 | 142 | 277 | 80 |
| 4 | jubarte-wasm | 0.1.0 | 76.2072 | 77.9542 | 76.2072 | 77.9542 | 86.1884 | 0 | 763 | 763 | 158 | 307 | 108 |
| 5 | jubarte-ast | jubarte-final@a58157a9cd2d | 74.1962 | 76.1486 | 74.1962 | 76.1486 | 74.1998 | 0 | 763 | 763 | 96 | 236 | 114 |
| 6 | jubarte-rust | jubarte-rust@9457b6549b5d+git.ebf1a79 | 76.3953 | 76.0408 | 76.3953 | 76.0408 | 74.1998 | 0 | 763 | 763 | 144 | 301 | 90 |
| 7 | sanity-word | — | 68.1679 | 70.4845 | 68.1679 | 70.4845 | — | 0 | 230 | 230 | 0 | 0 | 38 |
| 8 | jubarte-ast | jubarte-final@d43557e042c1 | 70.5699 | 68.6678 | 69.83 | 68.2992 | 74.8855 | 9 | 755 | 763 | 84 | 178 | 142 |
| 9 | ooxmlsdk | — | 55.1866 | 55.2398 | 55.1866 | 55.2398 | — | 0 | 232 | 232 | 0 | 0 | 52 |
| 10 | docxodus | 6.4.0 | 58.7425 | 55.0306 | 58.1749 | 54.9959 | — | 2 | 205 | 207 | 3 | 7 | 66 |
| 11 | folio | 0.3.1 | 55.3092 | 53.7539 | 54.7748 | 53.525 | — | 2 | 205 | 207 | 0 | 1 | 75 |
| 12 | superdoc | 1.19.2 | 56.3218 | 54.8131 | 49.3898 | 52.9529 | -0.0027 | 33 | 171 | 195 | 2 | 3 | 51 |
| 13 | folio | 0.15.13 | 52.1299 | 50.4313 | 50.8318 | 50.2913 | 4.3275 | 19 | 744 | 763 | 0 | 5 | 354 |
| 14 | superdoc | 1.21.3 | 53.1281 | 51.5561 | 46.3043 | 50.1612 | -0.0027 | 115 | 665 | 763 | 3 | 14 | 278 |
| 15 | docx-redline-js | 0.3.0-ts-migration | 50.5319 | 50.2615 | 48.4264 | 50.09 | — | 7 | 161 | 168 | 0 | 0 | 73 |
| 16 | docxodus | 7.0.0 | 50.4935 | 49.6384 | 50.4935 | 49.6384 | — | 0 | 196 | 196 | 0 | 0 | 102 |
| 17 | superdoc-redlines | 0.2.0 | 51.4092 | 50.1062 | 47.3665 | 49.1564 | 1.4947 | 68 | 703 | 763 | 0 | 5 | 346 |
| 18 | docx-redline-js | 0.3.0 | 46.1928 | 47.4243 | 45.1636 | 47.2226 | -3.3472 | 17 | 746 | 763 | 0 | 0 | 517 |
| 19 | superdoc | 2.0.0 | 45.1946 | 46.7186 | 19.606 | 0 | -16.4745 | 432 | 331 | 763 | 1 | 4 | 269 |
| 20 | docx-redline-js | — | 55.1236 | 55.1236 | 12.2497 | 0 | — | 7 | 2 | 9 | 0 | 0 | 1 |

### Common-subset ranking (script_redlines)

Paired comparison on the **488** documents every full-map vendor below completed (largest score map per vendor; current-stamp smokes do not shrink the set). Keys: `results/common_subset_script_redlines.txt`. Unlike the aggregate tables, these medians are computed on the SAME documents.

| # | vendor | version | median | mean |
| --- | --- | --- | --- | --- |
| 1 | jubarte-rust | jubarte-rust@17ea47e9a0d7+git.bf3d07ddd61180e55f327c8e891affd0f6c18d64 | 97.25 | 88.89 |
| 2 | docxodus | 9.8.0 | 96.86 | 85.48 |
| 3 | jubarte | jubarte-final@951a6e6b453c+git.98e641b1f2ef3fa9b4416b197a4494cd6401fb9a | 95.47 | 85.72 |
| 4 | jubarte-wasm | 0.1.0@4b36f4db1d2f+git.ebf1a7996df49f99fb40f4f67713e61cfd19c731 | 92.84 | 84.27 |
| 5 | jubarte-ast | jubarte-final@a58157a9cd2d | 82.27 | 78.21 |
| 6 | stemma | 0.5.0@2e7bdc832391+git.efaed0c1ecb41142b1465bbb124dd183c385a2b0 | 63.47 | 64.20 |
| 7 | safe-docx | 0.19.1@e3f092da3639+git.7bd35c876493f2725b095f0190c28d2644962c78 | 52.72 | 55.64 |
| 8 | superdoc | 1.21.3 | 52.51 | 54.48 |
| 9 | folio | 0.15.13 | 52.42 | 55.30 |
| 10 | superdoc-redlines | 0.2.0 | 52.08 | 53.91 |
| 11 | redlines | 0.6.1 | 48.97 | 48.01 |
| 12 | docx-redline-js | 0.3.0 | 48.82 | 48.86 |

### Paired comparisons (script_redlines)

Per-doc paired deltas on shared documents (best pin per vendor); `win/loss/tie` counts docs where the FIRST vendor scores higher/lower/equal. Wilcoxon signed-rank p, zsplit zero method.

| vendor A | vendor B | docs | win/loss/tie | median Δ | p |
| --- | --- | --- | --- | --- | --- |
| docx-redline-js | docxodus | 743 | 22/721/0 | -41.10 | 3.54e-120 |
| docx-redline-js | folio | 735 | 160/561/14 | -2.43 | 8.45e-58 |
| docx-redline-js | jubarte | 746 | 22/722/2 | -42.83 | 3.70e-121 |
| docx-redline-js | jubarte-ast | 746 | 24/721/1 | -29.73 | 3.47e-117 |
| docx-redline-js | jubarte-rust | 746 | 8/736/2 | -43.90 | 4.02e-123 |
| docx-redline-js | jubarte-wasm | 746 | 18/726/2 | -37.24 | 8.70e-122 |
| docx-redline-js | ooxmlsdk | 152 | 30/122/0 | -8.11 | 1.77e-13 |
| docx-redline-js | redlines | 736 | 368/367/1 | +0.01 | 8.11e-01 |
| docx-redline-js | safe-docx | 684 | 214/469/1 | -2.91 | 2.30e-35 |
| docx-redline-js | sanity-word | 151 | 12/139/0 | -23.41 | 5.12e-23 |
| docx-redline-js | stemma | 606 | 85/517/4 | -12.98 | 8.87e-79 |
| docx-redline-js | superdoc | 657 | 172/485/0 | -4.01 | 1.92e-43 |
| docx-redline-js | superdoc-redlines | 689 | 208/468/13 | -2.05 | 1.20e-32 |
| docxodus | folio | 741 | 703/38/0 | +29.90 | 2.60e-117 |
| docxodus | jubarte | 760 | 309/352/99 | +0.00 | 6.37e-02 |
| docxodus | jubarte-ast | 760 | 466/198/96 | +1.46 | 2.37e-28 |
| docxodus | jubarte-rust | 760 | 267/366/127 | +0.00 | 7.92e-08 |
| docxodus | jubarte-wasm | 760 | 343/286/131 | +0.00 | 2.55e-02 |
| docxodus | ooxmlsdk | 155 | 154/1/0 | +38.36 | 3.54e-27 |
| docxodus | redlines | 745 | 727/18/0 | +40.19 | 1.15e-121 |
| docxodus | safe-docx | 685 | 631/49/5 | +33.89 | 2.06e-102 |
| docxodus | sanity-word | 154 | 151/3/0 | +22.80 | 6.28e-27 |
| docxodus | stemma | 612 | 507/96/9 | +23.07 | 1.37e-64 |
| docxodus | superdoc | 662 | 616/44/2 | +35.15 | 1.31e-103 |
| docxodus | superdoc-redlines | 700 | 662/38/0 | +31.15 | 8.06e-113 |
| folio | jubarte | 744 | 40/702/2 | -32.87 | 3.69e-117 |
| folio | jubarte-ast | 744 | 58/685/1 | -21.52 | 9.26e-110 |
| folio | jubarte-rust | 744 | 18/724/2 | -34.10 | 1.74e-122 |
| folio | jubarte-wasm | 744 | 39/703/2 | -28.28 | 1.78e-119 |
| folio | ooxmlsdk | 154 | 85/69/0 | +1.65 | 3.53e-03 |
| folio | redlines | 734 | 571/162/1 | +3.86 | 3.34e-60 |
| folio | safe-docx | 679 | 369/309/1 | +0.43 | 1.58e-01 |
| folio | sanity-word | 153 | 34/119/0 | -11.62 | 3.78e-13 |
| folio | stemma | 605 | 153/448/4 | -6.15 | 2.31e-46 |
| folio | superdoc | 657 | 350/306/1 | +0.30 | 1.67e-01 |
| folio | superdoc-redlines | 685 | 412/233/40 | +0.19 | 4.69e-15 |
| jubarte | jubarte-ast | 763 | 459/222/82 | +2.23 | 1.19e-27 |
| jubarte | jubarte-rust | 763 | 247/331/185 | +0.00 | 5.51e-05 |
| jubarte | jubarte-wasm | 763 | 344/248/171 | +0.00 | 1.23e-05 |
| jubarte | ooxmlsdk | 155 | 149/6/0 | +34.01 | 7.68e-27 |
| jubarte | redlines | 745 | 729/16/0 | +40.85 | 2.96e-122 |
| jubarte | safe-docx | 688 | 636/48/4 | +34.42 | 1.87e-104 |
| jubarte | sanity-word | 154 | 135/19/0 | +18.91 | 2.35e-22 |
| jubarte | stemma | 614 | 520/85/9 | +21.63 | 6.96e-75 |
| jubarte | superdoc | 665 | 620/41/4 | +36.24 | 4.86e-104 |
| jubarte | superdoc-redlines | 703 | 672/29/2 | +33.52 | 7.64e-113 |
| jubarte-ast | jubarte-rust | 763 | 156/529/78 | -5.14 | 8.73e-57 |
| jubarte-ast | jubarte-wasm | 763 | 217/455/91 | -1.95 | 9.02e-24 |
| jubarte-ast | ooxmlsdk | 155 | 153/2/0 | +31.91 | 3.82e-27 |
| jubarte-ast | redlines | 745 | 717/28/0 | +30.38 | 2.44e-120 |
| jubarte-ast | safe-docx | 688 | 603/79/6 | +20.08 | 5.90e-92 |
| jubarte-ast | sanity-word | 154 | 143/11/0 | +18.17 | 1.35e-25 |
| jubarte-ast | stemma | 614 | 475/131/8 | +9.85 | 3.76e-45 |
| jubarte-ast | superdoc | 665 | 593/67/5 | +23.27 | 7.06e-95 |
| jubarte-ast | superdoc-redlines | 703 | 652/50/1 | +21.57 | 1.13e-106 |
| jubarte-rust | jubarte-wasm | 763 | 318/87/358 | +0.00 | 6.24e-34 |
| jubarte-rust | ooxmlsdk | 155 | 154/1/0 | +35.77 | 3.54e-27 |
| jubarte-rust | redlines | 745 | 740/5/0 | +42.33 | 1.76e-123 |
| jubarte-rust | safe-docx | 688 | 660/22/6 | +35.90 | 4.58e-112 |
| jubarte-rust | sanity-word | 154 | 150/4/0 | +20.64 | 1.22e-26 |
| jubarte-rust | stemma | 614 | 557/48/9 | +24.01 | 4.65e-91 |
| jubarte-rust | superdoc | 665 | 642/18/5 | +37.06 | 7.60e-109 |
| jubarte-rust | superdoc-redlines | 703 | 685/16/2 | +35.37 | 5.77e-116 |
| jubarte-wasm | ooxmlsdk | 155 | 153/2/0 | +35.52 | 3.68e-27 |
| jubarte-wasm | redlines | 745 | 726/19/0 | +38.47 | 5.58e-122 |
| jubarte-wasm | safe-docx | 688 | 629/53/6 | +30.17 | 2.15e-104 |
| jubarte-wasm | sanity-word | 154 | 149/5/0 | +20.21 | 2.50e-26 |
| jubarte-wasm | stemma | 614 | 515/92/7 | +19.47 | 3.42e-69 |
| jubarte-wasm | superdoc | 665 | 622/38/5 | +33.16 | 1.12e-103 |
| jubarte-wasm | superdoc-redlines | 703 | 671/30/2 | +29.54 | 1.90e-113 |
| ooxmlsdk | redlines | 153 | 117/36/0 | +5.77 | 1.04e-16 |
| ooxmlsdk | safe-docx | 149 | 63/86/0 | -1.26 | 7.56e-02 |
| ooxmlsdk | sanity-word | 230 | 15/215/0 | -14.02 | 3.48e-35 |
| ooxmlsdk | stemma | 113 | 25/88/0 | -10.43 | 2.27e-09 |
| ooxmlsdk | superdoc | 146 | 82/64/0 | +2.00 | 2.59e-01 |
| ooxmlsdk | superdoc-redlines | 146 | 74/72/0 | +0.10 | 2.96e-01 |
| redlines | safe-docx | 685 | 182/503/0 | -3.25 | 4.43e-49 |
| redlines | sanity-word | 152 | 7/145/0 | -19.63 | 3.01e-26 |
| redlines | stemma | 612 | 62/550/0 | -13.11 | 1.66e-89 |
| redlines | superdoc | 661 | 166/495/0 | -4.08 | 3.76e-48 |
| redlines | superdoc-redlines | 685 | 196/489/0 | -2.91 | 3.59e-35 |
| safe-docx | sanity-word | 148 | 32/116/0 | -13.68 | 4.02e-15 |
| safe-docx | stemma | 564 | 118/438/8 | -5.89 | 7.56e-45 |
| safe-docx | superdoc | 628 | 308/313/7 | +0.00 | 8.98e-01 |
| safe-docx | superdoc-redlines | 644 | 358/283/3 | +0.53 | 5.68e-03 |
| sanity-word | stemma | 113 | 71/42/0 | +4.35 | 2.50e-02 |
| sanity-word | superdoc | 145 | 120/25/0 | +15.73 | 1.52e-17 |
| sanity-word | superdoc-redlines | 145 | 121/24/0 | +13.41 | 3.07e-16 |
| stemma | superdoc | 546 | 443/101/2 | +7.67 | 1.85e-52 |
| stemma | superdoc-redlines | 573 | 453/112/8 | +6.77 | 4.63e-56 |
| superdoc | superdoc-redlines | 629 | 345/284/0 | +0.60 | 3.61e-02 |

### Lens health (script_redlines)

Docs where the pixel lens and a judging lens (functional accept/reject invariant, WV-1 word-validate) conflict — the bench is measuring the wrong thing on those docs. A bench-health alarm, not a ranking signal.

- **docx-redline-js** 0.3.0: 2 doc(s) where the lenses disagree (0.5% of two-lens docs)
- **docxodus** 9.0.0: 86 doc(s) where the lenses disagree (25.4% of two-lens docs)
- **docxodus** 9.8.0: 17 doc(s) where the lenses disagree (4.5% of two-lens docs)
- **folio** 0.15.13: 106 doc(s) where the lenses disagree (28.8% of two-lens docs)
- **jubarte** jubarte-final@02df62305cf3+git.98e641b1f2ef3fa9b4416b197a4494cd6401fb9a: 44 doc(s) where the lenses disagree (11.7% of two-lens docs)
- **jubarte** jubarte-final@14094d7b65aa+git.98e641b1f2ef3fa9b4416b197a4494cd6401fb9a: 45 doc(s) where the lenses disagree (11.9% of two-lens docs)
- **jubarte** jubarte-final@2140d6727f0d+git.98e641b1f2ef3fa9b4416b197a4494cd6401fb9a: 45 doc(s) where the lenses disagree (11.9% of two-lens docs)
- **jubarte** jubarte-final@700ad3b32181+git.98e641b1f2ef3fa9b4416b197a4494cd6401fb9a: 45 doc(s) where the lenses disagree (11.9% of two-lens docs)
- **jubarte** jubarte-final@76e503aae6c0+git.98e641b1f2ef3fa9b4416b197a4494cd6401fb9a: 43 doc(s) where the lenses disagree (11.4% of two-lens docs)
- **jubarte** jubarte-final@774e5a062abc+git.98e641b1f2ef3fa9b4416b197a4494cd6401fb9a: 45 doc(s) where the lenses disagree (11.9% of two-lens docs)
- **jubarte** jubarte-final@951a6e6b453c+git.98e641b1f2ef3fa9b4416b197a4494cd6401fb9a: 45 doc(s) where the lenses disagree (11.9% of two-lens docs)
- **jubarte** jubarte-final@c34fd18ff82b+git.98e641b1f2ef3fa9b4416b197a4494cd6401fb9a: 46 doc(s) where the lenses disagree (12.2% of two-lens docs)
- **jubarte** jubarte-final@c437ad72f0d8+git.98e641b1f2ef3fa9b4416b197a4494cd6401fb9a: 45 doc(s) where the lenses disagree (11.9% of two-lens docs)
- **jubarte** jubarte-final@c43ad9297820+git.98e641b1f2ef3fa9b4416b197a4494cd6401fb9a: 44 doc(s) where the lenses disagree (11.7% of two-lens docs)
- **jubarte** jubarte-final@c4de03e2da52+git.98e641b1f2ef3fa9b4416b197a4494cd6401fb9a: 44 doc(s) where the lenses disagree (11.7% of two-lens docs)
- **jubarte** jubarte-final@d43557e042c1: 20 doc(s) where the lenses disagree (5.3% of two-lens docs)
- **jubarte** jubarte-final@e7bcd29bb5a9+git.98e641b1f2ef3fa9b4416b197a4494cd6401fb9a: 43 doc(s) where the lenses disagree (11.4% of two-lens docs)
- **jubarte-ast** jubarte-final@a58157a9cd2d: 25 doc(s) where the lenses disagree (6.6% of two-lens docs)
- **jubarte-ast** jubarte-final@d43557e042c1: 36 doc(s) where the lenses disagree (9.8% of two-lens docs)
- **jubarte-rust** jubarte-rust@17ea47e9a0d7+git.bf3d07ddd61180e55f327c8e891affd0f6c18d64: 41 doc(s) where the lenses disagree (10.9% of two-lens docs)
- **jubarte-rust** jubarte-rust@9457b6549b5d+git.ebf1a79: 26 doc(s) where the lenses disagree (6.9% of two-lens docs)
- **jubarte-wasm** 0.1.0: 25 doc(s) where the lenses disagree (6.6% of two-lens docs)
- **jubarte-wasm** 0.1.0@4b36f4db1d2f+git.ebf1a7996df49f99fb40f4f67713e61cfd19c731: 25 doc(s) where the lenses disagree (6.6% of two-lens docs)
- **redlines** 0.6.1: 64 doc(s) where the lenses disagree (17.6% of two-lens docs)
- **safe-docx** 0.19.1@e3f092da3639+git.7bd35c876493f2725b095f0190c28d2644962c78: 70 doc(s) where the lenses disagree (20.8% of two-lens docs)
- **stemma** 0.5.0@2e7bdc832391+git.efaed0c1ecb41142b1465bbb124dd183c385a2b0: 16 doc(s) where the lenses disagree (5.5% of two-lens docs)
- **superdoc** 1.19.2: 25 doc(s) where the lenses disagree (15.9% of two-lens docs)
- **superdoc** 1.21.3: 53 doc(s) where the lenses disagree (16.9% of two-lens docs)
- **superdoc-redlines** 0.2.0: 38 doc(s) where the lenses disagree (11.2% of two-lens docs)

### `accepted_changes`

`accepted_changes`

**Current corpus** (newest `corpus_revision` stamp: `5ed816028d99`):

| # | vendor | version | mean | median | itt_mean | itt_median | skill_median | failures | n_docs | itt_n | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | 9.8.0 | 90.1868 | 100 | 88.8203 | 100 | — | 4 | 195 | 198 | 119 | 145 | 18 |
| 2 | stemma | 0.5.0@2e7bdc832391+git.efaed0c1ecb41142b1465bbb124dd183c385a2b0 | 79.1041 | 80.7673 | 77.4561 | 80.6255 | — | 3 | 141 | 144 | 19 | 48 | 13 |
| 3 | safe-docx | 0.19.1@e3f092da3639+git.7bd35c876493f2725b095f0190c28d2644962c78 | 64.0903 | 60.2244 | 63.7302 | 59.7051 | — | 1 | 177 | 178 | 9 | 27 | 55 |

**Legacy corpus** (older `corpus_revision` stamps and unstamped runs — not comparable with the rows above; kept for history until each tool re-runs):

| # | vendor | version | mean | median | itt_mean | itt_median | skill_median | failures | n_docs | itt_n | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | 6.4.0 | 68.9994 | 77.1882 | 68.9994 | 77.1882 | — | 0 | 164 | 164 | 14 | 22 | 43 |
| 2 | docxodus | 7.0.0 | 70.1963 | 74.9182 | 70.1963 | 74.9182 | — | 0 | 164 | 164 | 17 | 44 | 49 |
| 3 | superdoc | 1.19.2 | 63.818 | 61.1184 | 57.6669 | 55.8213 | — | 16 | 150 | 166 | 2 | 3 | 33 |
| 4 | folio | 0.3.1 | 57.9094 | 55.608 | 54.5813 | 53.9618 | — | 10 | 164 | 174 | 3 | 4 | 61 |

### `roundtrip`

roundtrip (self-diff → pdf_source)

**Current corpus** (newest `corpus_revision` stamp: `5ed816028d99`):

| # | vendor | version | mean | median | itt_mean | itt_median | skill_median | failures | n_docs | itt_n | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | safe-docx | 0.19.1@e3f092da3639+git.7bd35c876493f2725b095f0190c28d2644962c78 | 100 | 100 | 100 | 100 | — | 0 | 166 | 166 | 166 | 166 | 0 |
| 2 | docxodus | 9.8.0 | 99.9949 | 100 | 99.9949 | 100 | — | 0 | 166 | 166 | 163 | 166 | 0 |
| 3 | stemma | 0.5.0@2e7bdc832391+git.efaed0c1ecb41142b1465bbb124dd183c385a2b0 | 99.9494 | 100 | 99.9494 | 100 | — | 0 | 166 | 166 | 161 | 166 | 0 |

**Legacy corpus** (older `corpus_revision` stamps and unstamped runs — not comparable with the rows above; kept for history until each tool re-runs):

| # | vendor | version | mean | median | itt_mean | itt_median | skill_median | failures | n_docs | itt_n | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | folio | 0.3.1 | 98.0712 | 100 | 98.0712 | 100 | — | 0 | 198 | 198 | 185 | 190 | 4 |
| 2 | docxodus | 7.0.0 | 97.4281 | 100 | 97.4281 | 100 | — | 0 | 166 | 166 | 148 | 157 | 4 |
| 3 | docxodus | 6.4.0 | 92.2445 | 100 | 92.2445 | 100 | — | 0 | 198 | 198 | 144 | 161 | 13 |
| 4 | superdoc | 1.19.2 | 93.0017 | 100 | 91.5854 | 100 | — | 3 | 194 | 197 | 144 | 158 | 8 |

### `visual_rendering`

visual_rendering (Playwright viewer)

**Current corpus** (newest `corpus_revision` stamp: `5ed816028d99`):

| # | vendor | version | mean | median | itt_mean | itt_median | skill_median | failures | n_docs | itt_n | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | 9.8.0 | 65.2677 | 67.8808 | 65.2677 | 67.8808 | — | 0 | 199 | 199 | 1 | 7 | 30 |

**Legacy corpus** (older `corpus_revision` stamps and unstamped runs — not comparable with the rows above; kept for history until each tool re-runs):

| # | vendor | version | mean | median | itt_mean | itt_median | skill_median | failures | n_docs | itt_n | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | superdoc | 1.44.1 | 58.7798 | 61.2486 | 58.7798 | 61.2486 | — | 0 | 199 | 199 | 0 | 0 | 38 |
| 2 | folio | 0.5.0 | 59.6494 | 55.0967 | 59.6494 | 55.0967 | — | 0 | 198 | 198 | 0 | 3 | 56 |
| 3 | docxodus | 6.4.0-local.1 | 56.5017 | 49.7216 | 53.9463 | 49.2363 | — | 9 | 190 | 199 | 0 | 0 | 97 |
| 4 | docxodus | 7.0.0 | 56.5017 | 49.7216 | 53.9463 | 49.2363 | — | 9 | 190 | 199 | 0 | 0 | 97 |

### `visual_redlines`

visual_redlines (Playwright)

**Current corpus** (newest `corpus_revision` stamp: `5ed816028d99`):

| # | vendor | version | mean | median | itt_mean | itt_median | skill_median | failures | n_docs | itt_n | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | 9.8.0 | 61.0993 | 62.44 | 61.0993 | 62.44 | — | 0 | 155 | 155 | 0 | 0 | 26 |

**Legacy corpus** (older `corpus_revision` stamps and unstamped runs — not comparable with the rows above; kept for history until each tool re-runs):

| # | vendor | version | mean | median | itt_mean | itt_median | skill_median | failures | n_docs | itt_n | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | 6.4.0 | 60.9207 | 61.2232 | 48.5357 | 58.9198 | — | 37 | 145 | 182 | 0 | 0 | 13 |
| 2 | superdoc | 1.44.1 | 55.3334 | 56.4237 | 54.998 | 56.3376 | — | 1 | 164 | 165 | 0 | 0 | 44 |
| 3 | docxodus | 9.0.0 | 60.1462 | 57.5572 | 54.3453 | 55.3917 | — | 19 | 178 | 197 | 1 | 4 | 48 |
| 4 | folio | 0.5.0 | 51.5494 | 51.6497 | 50.9283 | 51.4809 | — | 2 | 164 | 166 | 0 | 0 | 68 |
| 5 | docxodus | 7.0.0 | 48.2275 | 48.0758 | 47.6464 | 48.0337 | — | 2 | 164 | 166 | 0 | 0 | 122 |

### `visual_accepted_changes`

visual_accepted_changes (Playwright)

**Current corpus** (newest `corpus_revision` stamp: `5ed816028d99`):

| # | vendor | version | mean | median | itt_mean | itt_median | skill_median | failures | n_docs | itt_n | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | 9.8.0 | 64.631 | 65.7934 | 64.631 | 65.7934 | — | 0 | 155 | 155 | 0 | 7 | 19 |

**Legacy corpus** (older `corpus_revision` stamps and unstamped runs — not comparable with the rows above; kept for history until each tool re-runs):

| # | vendor | version | mean | median | itt_mean | itt_median | skill_median | failures | n_docs | itt_n | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | 6.4.0 | 62.3235 | 62.7622 | 62.3235 | 62.7622 | — | 0 | 152 | 152 | 0 | 1 | 21 |
| 2 | superdoc | 1.44.1 | 59.3354 | 60.971 | 59.3354 | 60.971 | — | 0 | 165 | 165 | 0 | 0 | 35 |
| 3 | folio | 0.5.0 | 59.671 | 54.9489 | 59.671 | 54.9489 | — | 0 | 164 | 164 | 0 | 0 | 42 |

## All fidelity runs (flat)

| vendor | version | datetime | benchmark | mean | median | n_docs |
| --- | --- | --- | --- | --- | --- | --- |
| docx-redline-js | 0.3.0 | 2026-08-04T14:16:57.600170+00:00 | script_redlines | 46.1928 | 47.4243 | 746 |
| docx-redline-js | 0.3.0-ts-migration | 2026-07-15T23:24:01.804490+00:00 | script_redlines | 50.5319 | 50.2615 | 161 |
| docx-redline-js | — | 2026-07-15T23:21:34.805527+00:00 | script_redlines | 55.1236 | 55.1236 | 2 |
| docxodus | 6.4.0 | 2026-07-09T15:58:38.145555+00:00 | accepted_changes | 68.9994 | 77.1882 | 164 |
| docxodus | 6.4.0 | 2026-07-10T00:12:10.214778+00:00 | roundtrip | 92.2445 | 100 | 198 |
| docxodus | 6.4.0 | 2026-07-09T15:48:47.581159+00:00 | script_redlines | 58.7425 | 55.0306 | 205 |
| docxodus | 6.4.0 | 2026-07-09T17:19:51.161639+00:00 | visual_accepted_changes | 62.3235 | 62.7622 | 152 |
| docxodus | 6.4.0 | 2026-07-09T16:57:22.200205+00:00 | visual_redlines | 60.9207 | 61.2232 | 145 |
| docxodus | 6.4.0-local.1 | 2026-07-10T20:58:07.916380+00:00 | visual_rendering | 56.5017 | 49.7216 | 190 |
| docxodus | 7.0.0 | 2026-07-10T21:37:40.839901+00:00 | accepted_changes | 70.1963 | 74.9182 | 164 |
| docxodus | 7.0.0 | 2026-07-10T21:37:40.839901+00:00 | roundtrip | 97.4281 | 100 | 166 |
| docxodus | 7.0.0 | 2026-07-11T02:25:04.610761+00:00 | script_redlines | 50.4935 | 49.6384 | 196 |
| docxodus | 7.0.0 | 2026-07-10T21:59:48.076126+00:00 | visual_redlines | 48.2275 | 48.0758 | 164 |
| docxodus | 7.0.0 | 2026-07-10T21:55:37.514080+00:00 | visual_rendering | 56.5017 | 49.7216 | 190 |
| docxodus | 9.0.0 | 2026-08-04T14:30:46.167624+00:00 | script_redlines | 80.5535 | 91.1892 | 760 |
| docxodus | 9.0.0 | 2026-08-04T13:11:19.057858+00:00 | visual_redlines | 60.1462 | 57.5572 | 178 |
| docxodus | 9.8.0 | 2026-08-12T23:42:30.397782+00:00 | accepted_changes | 90.1868 | 100 | 195 |
| docxodus | 9.8.0 | 2026-08-12T23:42:30.397782+00:00 | roundtrip | 99.9949 | 100 | 166 |
| docxodus | 9.8.0 | 2026-08-12T23:42:30.397782+00:00 | script_redlines | 80.5534 | 91.1892 | 760 |
| docxodus | 9.8.0 | 2026-08-13T02:19:03.018138+00:00 | visual_accepted_changes | 64.631 | 65.7934 | 155 |
| docxodus | 9.8.0 | 2026-08-13T02:15:21.827989+00:00 | visual_redlines | 61.0993 | 62.44 | 155 |
| docxodus | 9.8.0 | 2026-08-13T02:07:50.495893+00:00 | visual_rendering | 65.2677 | 67.8808 | 199 |
| folio | 0.15.13 | 2026-08-04T14:51:49.763490+00:00 | script_redlines | 52.1299 | 50.4313 | 744 |
| folio | 0.3.1 | 2026-07-09T13:48:42.309993+00:00 | accepted_changes | 57.9094 | 55.608 | 164 |
| folio | 0.3.1 | 2026-07-10T00:18:18.365930+00:00 | roundtrip | 98.0712 | 100 | 198 |
| folio | 0.3.1 | 2026-07-09T13:01:34.270204+00:00 | script_redlines | 55.3092 | 53.7539 | 205 |
| folio | 0.5.0 | 2026-07-08T20:35:26.466209+00:00 | visual_accepted_changes | 59.671 | 54.9489 | 164 |
| folio | 0.5.0 | 2026-07-08T20:20:25.117836+00:00 | visual_redlines | 51.5494 | 51.6497 | 164 |
| folio | 0.5.0 | 2026-07-08T20:14:38.167302+00:00 | visual_rendering | 59.6494 | 55.0967 | 198 |
| jubarte | jubarte-final@02df62305cf3+git.98e641b1f2ef3fa9b4416b197a4494cd6401fb9a | 2026-08-14T10:15:55.237109+00:00 | script_redlines | 81.5586 | 89.1671 | 763 |
| jubarte | jubarte-final@14094d7b65aa+git.98e641b1f2ef3fa9b4416b197a4494cd6401fb9a | 2026-08-14T13:02:00.690937+00:00 | script_redlines | 81.8985 | 90.7573 | 763 |
| jubarte | jubarte-final@2140d6727f0d+git.98e641b1f2ef3fa9b4416b197a4494cd6401fb9a | 2026-08-14T13:50:05.579598+00:00 | script_redlines | 81.9552 | 91.0482 | 763 |
| jubarte | jubarte-final@700ad3b32181+git.98e641b1f2ef3fa9b4416b197a4494cd6401fb9a | 2026-08-14T11:18:03.674556+00:00 | script_redlines | 81.6469 | 89.3249 | 763 |
| jubarte | jubarte-final@76e503aae6c0+git.98e641b1f2ef3fa9b4416b197a4494cd6401fb9a | 2026-08-14T09:49:24.680414+00:00 | script_redlines | 81.5594 | 89.1671 | 763 |
| jubarte | jubarte-final@774e5a062abc+git.98e641b1f2ef3fa9b4416b197a4494cd6401fb9a | 2026-08-14T11:38:07.168458+00:00 | script_redlines | 81.647 | 89.3249 | 763 |
| jubarte | jubarte-final@951a6e6b453c+git.98e641b1f2ef3fa9b4416b197a4494cd6401fb9a | 2026-08-14T14:11:30.524650+00:00 | script_redlines | 81.9937 | 91.3062 | 763 |
| jubarte | jubarte-final@c34fd18ff82b+git.98e641b1f2ef3fa9b4416b197a4494cd6401fb9a | 2026-08-14T13:28:46.182985+00:00 | script_redlines | 81.9545 | 91.0482 | 763 |
| jubarte | jubarte-final@c437ad72f0d8+git.98e641b1f2ef3fa9b4416b197a4494cd6401fb9a | 2026-08-14T11:59:07.252134+00:00 | script_redlines | 81.7809 | 90.46 | 763 |
| jubarte | jubarte-final@c43ad9297820+git.98e641b1f2ef3fa9b4416b197a4494cd6401fb9a | 2026-08-14T10:46:54.510626+00:00 | script_redlines | 81.76 | 90.1976 | 763 |
| jubarte | jubarte-final@c4de03e2da52+git.98e641b1f2ef3fa9b4416b197a4494cd6401fb9a | 2026-08-14T12:26:35.586172+00:00 | script_redlines | 81.6772 | 89.4571 | 763 |
| jubarte | jubarte-final@d43557e042c1 | 2026-08-04T11:01:14.552442+00:00 | script_redlines | 77.0151 | 78.5311 | 763 |
| jubarte | jubarte-final@e7bcd29bb5a9+git.98e641b1f2ef3fa9b4416b197a4494cd6401fb9a | 2026-08-14T09:13:10.968938+00:00 | script_redlines | 81.5698 | 89.1133 | 763 |
| jubarte-ast | jubarte-final@a58157a9cd2d | 2026-08-11T10:49:32.739563+00:00 | script_redlines | 74.1962 | 76.1486 | 763 |
| jubarte-ast | jubarte-final@d43557e042c1 | 2026-08-04T11:15:42.562625+00:00 | script_redlines | 70.5699 | 68.6678 | 755 |
| jubarte-rust | jubarte-rust@17ea47e9a0d7+git.bf3d07ddd61180e55f327c8e891affd0f6c18d64 | 2026-08-13T20:58:50.595888+00:00 | script_redlines | 84.4662 | 92.6623 | 763 |
| jubarte-rust | jubarte-rust@9457b6549b5d+git.ebf1a79 | 2026-08-06T08:22:07.009758+00:00 | script_redlines | 76.3953 | 76.0408 | 763 |
| jubarte-wasm | 0.1.0 | 2026-08-04T13:32:06.568520+00:00 | script_redlines | 76.2072 | 77.9542 | 763 |
| jubarte-wasm | 0.1.0@4b36f4db1d2f+git.ebf1a7996df49f99fb40f4f67713e61cfd19c731 | 2026-08-05T22:59:39.181670+00:00 | script_redlines | 79.5678 | 84.8864 | 763 |
| ooxmlsdk | — | 2026-07-13T17:24:50.712941+00:00 | script_redlines | 55.1866 | 55.2398 | 232 |
| redlines | 0.6.1 | 2026-08-15T15:53:42.204313+00:00 | script_redlines | 45.9391 | 47.1411 | 745 |
| safe-docx | 0.19.1@e3f092da3639+git.7bd35c876493f2725b095f0190c28d2644962c78 | 2026-08-15T15:08:16.344882+00:00 | accepted_changes | 64.0903 | 60.2244 | 177 |
| safe-docx | 0.19.1@e3f092da3639+git.7bd35c876493f2725b095f0190c28d2644962c78 | 2026-08-15T15:08:16.344882+00:00 | roundtrip | 100 | 100 | 166 |
| safe-docx | 0.19.1@e3f092da3639+git.7bd35c876493f2725b095f0190c28d2644962c78 | 2026-08-15T15:08:16.344882+00:00 | script_redlines | 53.6532 | 51.3113 | 688 |
| sanity-word | — | 2026-07-13T18:06:21.529826+00:00 | script_redlines | 68.1679 | 70.4845 | 230 |
| stemma | 0.5.0@2e7bdc832391+git.efaed0c1ecb41142b1465bbb124dd183c385a2b0 | 2026-08-15T14:40:31.132906+00:00 | accepted_changes | 79.1041 | 80.7673 | 141 |
| stemma | 0.5.0@2e7bdc832391+git.efaed0c1ecb41142b1465bbb124dd183c385a2b0 | 2026-08-15T14:40:31.132906+00:00 | roundtrip | 99.9494 | 100 | 166 |
| stemma | 0.5.0@2e7bdc832391+git.efaed0c1ecb41142b1465bbb124dd183c385a2b0 | 2026-08-15T14:40:31.132906+00:00 | script_redlines | 62.9106 | 61.8327 | 614 |
| superdoc | 1.19.2 | 2026-07-09T15:38:31.872437+00:00 | accepted_changes | 63.818 | 61.1184 | 150 |
| superdoc | 1.19.2 | 2026-07-09T18:25:24.395459+00:00 | roundtrip | 93.0017 | 100 | 194 |
| superdoc | 1.19.2 | 2026-08-04T12:22:11.089004+00:00 | script_redlines | 56.3218 | 54.8131 | 171 |
| superdoc | 1.21.3 | 2026-08-04T13:48:05.360659+00:00 | script_redlines | 53.1281 | 51.5561 | 665 |
| superdoc | 1.44.1 | 2026-07-09T18:25:37.273372+00:00 | visual_accepted_changes | 59.3354 | 60.971 | 165 |
| superdoc | 1.44.1 | 2026-07-09T18:22:07.033240+00:00 | visual_redlines | 55.3334 | 56.4237 | 164 |
| superdoc | 1.44.1 | 2026-07-09T18:16:46.431642+00:00 | visual_rendering | 58.7798 | 61.2486 | 199 |
| superdoc | 2.0.0 | 2026-08-04T13:58:56.768817+00:00 | script_redlines | 45.1946 | 46.7186 | 331 |
| superdoc-redlines | 0.2.0 | 2026-08-04T15:03:29.049566+00:00 | script_redlines | 51.4092 | 50.1062 | 703 |

## Holdout gap

Sealed holdout (`corpus/holdout_combined.txt`) vs the visible corpus, per vendor: the latest holdout-only run (`bench run --holdout`) next to the latest COMPARABLE main run — same tool_version, `holdout_mode=excluded` (disjoint from the sealed set), full corpus (n > 100). `gap = holdout − main`; a strongly negative gap flags overfitting to the visible corpus.

_no holdout runs recorded yet (`bench run --holdout`)_

## docx_to_pdf

Source: `results/docx_to_pdf_500.json`.

docx_to_pdf — DOCX to PDF vs Word export

428 unique stems. Oracle: pinned Word-export PDFs (`pdf_accepted_word`, `pdf_redlines_randomized`). Failed converts score 0 (ITT). Mean and median are ITT.

| Rank | Tool | Version | n scored | ITT n | ITT Mean | ITT Median | Perfect (100) | Failures |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | jubarte | jubarte 0.7.0 | 428 | 428 | 60.70 | 62.54 | 0 | 0 |
| 2 | office2pdf | office2pdf 0.6.7 | 413 | 428 | 60.26 | 57.01 | 0 | 15 |
| 3 | pdfitdown | pdfitdown 4.0.0 | 413 | 428 | 60.26 | 57.01 | 0 | 15 |
| 4 | rdocx | rdocx 0.7.0 | 428 | 428 | 50.30 | 48.79 | 0 | 0 |
| 5 | doxx | doxx 0.1.4 | 0 | 428 | 0.00 | 0.00 | 0 | 428 |

## Redline generation speed

Source: `results/speed.jsonl` (+ `results/redline_speed_bench/**/summary.json` when present). **19** generation row(s) after dedupe (one per tool×kind; prefer larger `n`, then lower median). Unit: **ms per redline** (lower = faster). See [`docs/SPEED.md`](docs/SPEED.md) for methodology.

**Fairness (read before citing):**

- **`*-inproc` / Node engines** — warm process, algorithm cost (thesis-grade).
- **CLI tools** (`docxodus-csharp`, `jubarte-rust`) — spawn + I/O + compare per sample. C# cold-start dominates; do **not** cite CLI as algorithm cost.
- **WASM `docxodus`** — Mono/.NET WASM in-process after one-time init; fat tail.

### Microbench (`kind: speed`)

Classic `scripts/speed-bench.ts` / SuperDoc speed harness (typically ~30–40 pairs × 3 reps, in-memory for Node).

| # | tool | runtime | median ms | mean ms | p95 | p99 | /s | n | fail |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | node | 75.27 | 236.569 | 1499.68 | 2262.59 | 4.2 | 90 | 0 |
| 2 | superdoc | python | 40.888 | 94.191 | 619.931 | 885.366 | 10.6 | 90 | 0 |
| 3 | jubarte-final-lossless | node | 18.128 | 52.764 | 311.108 | 558.05 | 19 | 90 | 0 |
| 4 | jubarte-final-native | node | 6.758 | 18.89 | 115.966 | 191.954 | 52.9 | 90 | 0 |
| 5 | jubarte-native | node | 4.5 | 7.671 | 33.267 | 47.434 | 130.4 | 90 | 0 |
| 6 | jubarte-third-native | node | 4.469 | 7.55 | 33.212 | 45.323 | 132.4 | 90 | 0 |
| 7 | jubarte-second-native | node | 4.46 | 7.485 | 31.96 | 44.696 | 133.6 | 90 | 0 |
| 8 | jubarte-lossless | node | 2.457 | 6.596 | 37.579 | 58.256 | 151.6 | 90 | 0 |
| 9 | jubarte-third-docxodus | node | 2.364 | 6.031 | 33.763 | 53.804 | 165.8 | 90 | 0 |
| 10 | jubarte-second-docxodus | node | 2.39 | 5.891 | 31.351 | 52.839 | 169.8 | 90 | 0 |
| 11 | docx-redline-js | node | 1.451 | 2.791 | 6.907 | 45.976 | 358.4 | 90 | 0 |

### Large-N `speed_redlines` (`scripts/redline_speed_bench.ts`)

Large fixture pools (often **1000 unique** docs → **5000 pairs**), including native C# Docxodus, jubarte-rust CLI/warm, WASM. Warm workers: `docxodus-csharp-inproc`, `jubarte-rust-inproc`.

| # | tool | runtime | fixtures | pairs | median ms | mean ms | p95 | p99 | /s | n | fail | profile |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | dotnet-wasm | 1000 | 5000 | 74.595 | 428.227 | 922.477 | 3970.72 | 2.3 | 5000 | 0 | v8-inspector |
| 2 | docxodus-csharp | dotnet | 50 | 50 | 208.388 | 441.646 | 911.873 | 1154.008 | 2.3 | 50 | 0 | — |
| 3 | jubarte-lossless | node | 1000 | 5000 | 56.465 | 168.791 | 609.005 | 1049.093 | 5.9 | 4997 | 3 | v8-inspector |
| 4 | jubarte-native | node | 1000 | 5000 | 14.43 | 57.145 | 175.709 | 578.45 | 17.5 | 5000 | 0 | — |
| 5 | jubarte-wasm | rust-wasm | 1000 | 5000 | 9.667 | 41.493 | 174.035 | 265.818 | 24.1 | 5000 | 0 | v8-inspector |
| 6 | jubarte-rust | rust | 1000 | 5000 | 9.656 | 31.022 | 123.386 | 195.751 | 32.2 | 5000 | 0 | — |
| 7 | docxodus-csharp-inproc | dotnet | 1000 | 5000 | 7.888 | 25.832 | 101.854 | 206.808 | 38.7 | 4880 | 120 | samply |
| 8 | jubarte-rust-inproc | rust | 1000 | 5000 | 6.201 | 25.337 | 110.764 | 182.306 | 39.5 | 5000 | 0 | samply |

### Speed methodology notes

- Dedup key: `(kind, tool, unit)`. Best re-run by `(n, −median, run_ts)`.
- `speed_redlines` rows with **n < 10** are dropped as trivial smokes.
- Profiles (when present): samply `.profile.json.gz` for native CLIs/workers; V8 `.cpuprofile` for in-process Node (e.g. jubarte-lossless).
- Regenerate after a run: `python3 scripts/export-results-md.py`.

## Methodology notes (fidelity)

- Deduplication: one line per `(vendor, benchmark, tool_version)`. Re-runs of the **same** triple keep the best by `(render_fit, full_corpus_bucket, timestamp, overall_mean)` — prefer playwright for `visual_*` and soffice for script/accepted/roundtrip, then full-corpus lines (n > 100) over smokes, then the newest line (so a 383-doc post-holdout line supersedes a stale 403-doc one).
- **Versions are not collapsed.** docxodus `6.4.0` and `7.0.0` both appear so pins can be compared directly.
- **docxodus** filter: rows with **`n_docs ≤ 100`** are dropped (smoke / partial runs such as `visual_rendering` with n=21 or n=2). Full-corpus pins (typically n ≳ 145) are kept for every version.
- **jubarte-*** filter: rows with **ITT docs < 760** are dropped. A 164-doc subset is not the same measurement as the 763-doc ITT corpus.
- Other vendors keep every version even if n is small (e.g. `prebaked` sanity).
- Scores isolate *redline-markup fidelity vs Word* when candidates and the oracle share the same renderer (LibreOffice 26.2.4.2 for `script_redlines` / `accepted_changes` / `roundtrip`). Playwright `visual_*` scores are not cross-comparable with soffice scores.

## Licensing & legal considerations

These numbers are **independent engineering measurements**, not endorsements, certifications, or claims of compliance with any third-party product.

- **This repository** (scoring core derived from [superdoc-visual-benchmarks](https://github.com/superdoc-dev/superdoc-visual-benchmarks)) is licensed under **AGPL-3.0-only**. See `LICENSE`.
- **Microsoft Word** is a proprietary product of Microsoft. The Word oracle redlines are produced by Word for measurement only; Microsoft is not affiliated with this benchmark and does not endorse these results. Trademarks remain the property of their owners.
- **Benchmarked engines** remain under their own licenses and copyrights; publishing a score does not change their terms:
  - jubarte / in-repo ports — see their package licenses
  - [docxodus](https://github.com/JSv4/docxodus) (MIT)
  - [docx-redline-js](https://github.com/AnsonLai/docx-redline-js) (MIT)
  - [folio](https://github.com/stella/folio) (Apache-2.0)
  - [SuperDoc](https://github.com/Harbour-Enterprises/SuperDoc) (AGPL-3.0) and related SuperDoc tooling
- **LibreOffice** is used only as a pinned PDF renderer for fair comparison; it is not a redline generator in this bench.
- Redistributing or reusing scores, corpus fixtures, or generated redlines must still respect the licenses of the underlying tools and any corpus rights.

- **docx_to_pdf** and **docx_to_pdf_no_redline_docs** are Word-export measurements (`results/docx_to_pdf_500.json`, `results/docx_to_pdf_no_redline.json`), not `bench.jsonl` lines.

Regenerate: `python3 scripts/export-results-md.py` (reads `results/bench.jsonl` + `results/speed.jsonl` + the DOCX→PDF JSON artifacts).

<!-- DUAL_PATH_QUALITY:BEGIN -->
## jubarte-first dual-path redline quality (lossless vs via-AST)

_Generated by `scripts/redline_dual_path_report.mjs` from `runs/dual-path-403`. jubarte-first `1d33330` · corpus `64d2f609` · bench `b04b8b5` · Node v26.6.0._

Acceptance gate over the same pairs, judged identically for both engines with the
package-level accept/reject: a pair is `ok` only when every XML part of the redline is
well-formed AND `text(accept(redline)) == text(next)` AND `text(reject(redline)) == text(base)`.
Malformed XML is counted as a hard fail because Word reports it as unreadable content.

| engine | pairs | ok | ok % | well-formed | accept ok | reject ok | compare threw |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| jubarte-first-lossless | 403 | 368 | 91.3% | 403 | 390 | 378 | 0 |
| jubarte-first-via-ast | 403 | 352 | 87.3% | 396 | 368 | 365 | 0 |
<!-- DUAL_PATH_QUALITY:END -->

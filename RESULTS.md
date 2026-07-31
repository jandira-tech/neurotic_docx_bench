# Benchmark results

Source: `results/bench.jsonl` — **160** fidelity row(s) (one per vendor×benchmark×**version**; 126 distinct vendor×version pin(s). docxodus rows with n_docs ≤ 100 are dropped as smoke/partial).

Scores are 0–100 (higher = closer to the Microsoft Word oracle). Cross-renderer comparisons (LibreOffice vs Playwright) are **not** directly comparable — only compare within the same benchmark. Different **versions** of the same vendor are kept so you can compare pins (e.g. docxodus 6.4.0 vs 7.0.0).

## Rankings by benchmark

### `script_redlines`

script_redlines (LibreOffice render vs Word oracle)

| # | vendor | version | mean | median | n_docs | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | prebaked | — | 100 | 100 | 1 | 1 | 1 | 0 |
| 2 | jubarte-rust | jubarte-rust@63e57d122c83 | 92.2148 | 99.9187 | 164 | 80 | 122 | 3 |
| 3 | jubarte-rust | jubarte-rust@cbbcefb724a7 | 92.2147 | 99.9187 | 164 | 80 | 122 | 3 |
| 4 | jubarte-wasm | 0.1.0 | 92.2147 | 99.9187 | 164 | 80 | 122 | 3 |
| 5 | jubarte-rust | jubarte-rust@07493ca50fd6 | 92.1039 | 99.9187 | 164 | 80 | 122 | 5 |
| 6 | jubarte-rust | jubarte-rust@4ab62a18cf7a | 91.9831 | 99.904 | 164 | 79 | 121 | 3 |
| 7 | jubarte-rust | jubarte-rust@7eca5f3f80f7 | 91.9831 | 99.904 | 164 | 79 | 121 | 3 |
| 8 | jubarte-rust | jubarte-rust@9882dd52cc11 | 91.9831 | 99.904 | 164 | 79 | 121 | 3 |
| 9 | jubarte-rust | jubarte-rust@cf12c65f1204 | 91.9831 | 99.904 | 164 | 79 | 121 | 3 |
| 10 | jubarte-rust | jubarte-rust@f46f60951d28 | 91.9831 | 99.904 | 164 | 79 | 121 | 3 |
| 11 | jubarte-rust | jubarte-rust@d269742c1397 | 91.9075 | 99.904 | 164 | 79 | 121 | 3 |
| 12 | jubarte-rust | jubarte-rust@f6cc3a6a7eb8 | 91.8526 | 99.9187 | 164 | 80 | 120 | 3 |
| 13 | jubarte-rust | jubarte-rust@f7960f5be6f3 | 91.8328 | 99.9187 | 164 | 80 | 120 | 2 |
| 14 | jubarte-rust | jubarte-rust@4f964f7612f5 | 90.4602 | 95.6735 | 164 | 62 | 110 | 5 |
| 15 | jubarte-rust | jubarte-rust@3ad02b0cd59e | 90.1694 | 98.7613 | 164 | 69 | 111 | 3 |
| 16 | jubarte | jubarte-final@3995702f73ed | 90.0433 | 91.9856 | 163 | 44 | 92 | 0 |
| 17 | jubarte | jubarte-final@983daed413e2 | 89.694 | 91.9481 | 163 | 43 | 91 | 0 |
| 18 | jubarte | jubarte-final@1d02711eb646 | 89.6394 | 91.9481 | 163 | 43 | 91 | 0 |
| 19 | jubarte | jubarte-final@ca31e561ca95 | 89.5095 | 91.9481 | 163 | 43 | 91 | 0 |
| 20 | jubarte | jubarte-final@c7771d920f75 | 89.4468 | 91.9836 | 163 | 43 | 93 | 0 |
| 21 | jubarte | jubarte-final@9fdd4b0b75bd | 89.3794 | 91.9481 | 163 | 43 | 90 | 0 |
| 22 | jubarte | jubarte-final@b0f6fcbfb69f | 89.263 | 91.9836 | 163 | 43 | 93 | 0 |
| 23 | jubarte | jubarte-final@e5877596422c | 89.0074 | 91.9836 | 163 | 43 | 93 | 0 |
| 24 | jubarte | jubarte-final@6e909b7b4408 | 88.9047 | 91.9836 | 163 | 43 | 93 | 0 |
| 25 | jubarte | jubarte-final@9d7adf85bd3b | 88.6992 | 91.8424 | 163 | 43 | 91 | 0 |
| 26 | jubarte | jubarte-final@d6601413148f | 88.568 | 91.727 | 163 | 42 | 90 | 0 |
| 27 | jubarte | jubarte-final@218fbf85cc92 | 88.2694 | 91.5066 | 163 | 42 | 89 | 0 |
| 28 | jubarte | jubarte-final@bdad6a0a16a8 | 88.1228 | 91.3598 | 163 | 41 | 87 | 0 |
| 29 | jubarte | jubarte-final@074c4727e65d | 87.9968 | 91.5066 | 163 | 41 | 88 | 0 |
| 30 | jubarte | jubarte-final@1e9ac33b7ca8 | 87.5086 | 90.6342 | 163 | 38 | 85 | 0 |
| 31 | jubarte | jubarte-final@28f85285d077 | 87.4732 | 90.6342 | 163 | 38 | 84 | 0 |
| 32 | jubarte | jubarte-final@52e796946879 | 87.3192 | 90.5514 | 163 | 40 | 83 | 0 |
| 33 | jubarte | jubarte-final@a3f3744cd0c4 | 87.3174 | 90.5514 | 163 | 40 | 83 | 0 |
| 34 | jubarte | jubarte-final@bac9423e07f0 | 87.0779 | 90.2449 | 163 | 40 | 82 | 0 |
| 35 | jubarte | jubarte-final@a383f41fcf20 | 86.5619 | 89.6075 | 163 | 39 | 81 | 0 |
| 36 | jubarte | jubarte-final@5778f88898ac | 86.3437 | 89.4587 | 163 | 39 | 80 | 0 |
| 37 | jubarte | jubarte-final@3a492480108b | 86.3084 | 89.4587 | 163 | 38 | 80 | 0 |
| 38 | jubarte | jubarte-final@cd25600d93c2 | 85.4334 | 89.4571 | 163 | 38 | 79 | 0 |
| 39 | jubarte | jubarte-final@37789c3f7619 | 85.3131 | 89.4571 | 163 | 38 | 79 | 0 |
| 40 | jubarte-rust | jubarte-rust@3838e1a2c0ae | 85.2628 | 89.4719 | 164 | 48 | 79 | 6 |
| 41 | jubarte-rust | jubarte-rust@8a970b82f860 | 85.0487 | 89.3449 | 164 | 48 | 78 | 6 |
| 42 | jubarte-rust | jubarte-rust@aad3e04cebbd | 84.9762 | 89.3449 | 164 | 48 | 78 | 6 |
| 43 | jubarte | jubarte-final@453850c8087b | 84.8877 | 88.6191 | 163 | 34 | 76 | 0 |
| 44 | jubarte | jubarte-final@e51a749ffed3 | 84.8799 | 89.4571 | 163 | 38 | 79 | 0 |
| 45 | jubarte-rust | jubarte-rust@980adfca2fc6 | 84.8331 | 89.3449 | 164 | 48 | 78 | 6 |
| 46 | jubarte | jubarte-final@45e96376aa20 | 84.8108 | 89.4571 | 163 | 38 | 79 | 1 |
| 47 | jubarte-rust | jubarte-rust@27b57358b1c3 | 84.7354 | 89.3449 | 164 | 47 | 78 | 6 |
| 48 | jubarte | jubarte-final@15ed9cf09abd | 84.617 | 89.3249 | 163 | 38 | 78 | 2 |
| 49 | jubarte-rust | jubarte-rust@267e2e589504 | 84.4755 | 89.4719 | 164 | 47 | 79 | 6 |
| 50 | jubarte | jubarte-final@f3ac233ba2cb | 84.3075 | 89.3249 | 163 | 38 | 78 | 3 |
| 51 | jubarte-rust | jubarte-rust@01ed1fac181e | 84.2081 | 93.0906 | 196 | 68 | 107 | 9 |
| 52 | jubarte-rust | jubarte-rust@21f394cb95d8 | 84.2081 | 93.0906 | 196 | 68 | 107 | 9 |
| 53 | jubarte-rust | jubarte-rust@a8ff27ccff8f | 84.2078 | 93.0906 | 196 | 68 | 107 | 9 |
| 54 | jubarte-rust | jubarte-rust@ae865542c28f | 84.2078 | 93.0906 | 196 | 68 | 107 | 9 |
| 55 | jubarte-rust | jubarte-rust@e12c880586ec | 84.2078 | 93.0906 | 196 | 68 | 107 | 9 |
| 56 | jubarte-rust | jubarte-rust@5e1d044ac048 | 84.1728 | 93.0906 | 196 | 69 | 107 | 9 |
| 57 | jubarte-rust | jubarte-rust@9190265c69a2 | 84.1728 | 93.0906 | 196 | 69 | 107 | 9 |
| 58 | jubarte-rust | jubarte-rust@653876af82d6 | 84.172 | 93.0906 | 196 | 68 | 107 | 9 |
| 59 | jubarte-rust | jubarte-rust@6b5740328b0a | 84.172 | 93.0906 | 196 | 68 | 107 | 9 |
| 60 | jubarte-rust | jubarte-rust@28c41564723b | 84.009 | 93.0906 | 196 | 69 | 107 | 9 |
| 61 | jubarte | jubarte-final@e3e8440fde33 | 83.7754 | 84.4032 | 163 | 32 | 66 | 1 |
| 62 | jubarte-rust | jubarte-rust@8e77f696f091 | 83.7652 | 88.5162 | 164 | 44 | 75 | 8 |
| 63 | jubarte-rust | jubarte-rust@fc29f56fd31d | 83.7652 | 88.5162 | 164 | 44 | 75 | 8 |
| 64 | jubarte | jubarte-final@70986060934f | 83.7379 | 89.2047 | 164 | 36 | 76 | 8 |
| 65 | jubarte | jubarte-final@da95efff703e | 83.668 | 89.0844 | 163 | 38 | 76 | 6 |
| 66 | jubarte | jubarte-final@4f003998b8fa | 83.6628 | 88.8518 | 164 | 37 | 75 | 8 |
| 67 | jubarte | jubarte-final@be0804dde638+git.4518f52ab32ae788012a7446471043fb51674c20 | 83.6291 | 88.9633 | 164 | 53 | 78 | 8 |
| 68 | jubarte | jubarte-final@d5bd12d173d6+git.aaa85454f569b7174dd99d5244877d29819a99b9 | 83.6291 | 88.9633 | 164 | 53 | 78 | 8 |
| 69 | jubarte | jubarte-final@a57e820404f3 | 83.5609 | 88.8518 | 164 | 36 | 76 | 10 |
| 70 | jubarte | jubarte-final@3a499185d2a6 | 83.546 | 88.6089 | 163 | 38 | 73 | 5 |
| 71 | jubarte | jubarte-final@5e534b75b66a | 83.5133 | 88.8518 | 164 | 36 | 76 | 10 |
| 72 | jubarte | jubarte-final@138efcf0b70b | 83.4424 | 88.614 | 164 | 34 | 73 | 8 |
| 73 | jubarte | jubarte-final@591b7504a890 | 83.4375 | 88.8518 | 164 | 36 | 76 | 11 |
| 74 | jubarte | jubarte-final@8b2e9bf2522a | 83.4234 | 88.6547 | 164 | 53 | 77 | 8 |
| 75 | jubarte | 0.1.0 | 83.4039 | 88.6547 | 164 | 53 | 77 | 8 |
| 76 | jubarte | jubarte-final@2f41358dbc2c | 83.4039 | 88.6547 | 164 | 53 | 77 | 8 |
| 77 | jubarte | jubarte-final@576b0f787e47+git.885b34c2da64df79ab7f82017e13ad53313b217b | 83.4039 | 88.6547 | 164 | 53 | 77 | 8 |
| 78 | jubarte | jubarte-final@d7599c91e4d5 | 83.4039 | 88.6547 | 164 | 53 | 77 | 8 |
| 79 | jubarte | jubarte-final@dbc8db9ef551 | 83.4037 | 88.6547 | 164 | 53 | 77 | 8 |
| 80 | jubarte | jubarte-final@9650d0f6fd09 | 83.2401 | 88.614 | 164 | 34 | 73 | 8 |
| 81 | jubarte | jubarte-final@9e40ef84f1f0 | 83.2014 | 88.614 | 164 | 35 | 75 | 11 |
| 82 | jubarte-rust | jubarte-rust@9fcc4289e375 | 83.1887 | 93.0906 | 196 | 69 | 107 | 16 |
| 83 | jubarte | jubarte-final@c27e3f635094 | 83.1808 | 88.614 | 164 | 35 | 75 | 11 |
| 84 | jubarte | jubarte-final@757360aba6a2 | 82.6342 | 88.0854 | 164 | 35 | 73 | 12 |
| 85 | jubarte | jubarte-final@af5279d4ff9d | 82.5623 | 88.0854 | 164 | 35 | 73 | 12 |
| 86 | jubarte-rust | jubarte-rust@cdfef70a7156 | 81.0444 | 84.7199 | 207 | 42 | 84 | 17 |
| 87 | jubarte | jubarte-final@77d67f774b3e | 80.7225 | 84.8619 | 164 | 32 | 68 | 15 |
| 88 | jubarte-rust | jubarte-rust@51a93adf52ca | 80.2389 | 83.1955 | 207 | 41 | 79 | 17 |
| 89 | jubarte | jubarte-final@dd16ad8fbcf3 | 79.4364 | 79.9471 | 207 | 54 | 77 | 13 |
| 90 | jubarte | jubarte-final@8b23cdc7eca8 | 79.2696 | 79.9471 | 207 | 54 | 77 | 13 |
| 91 | jubarte | jubarte-final@6481c2fdbfc0 | 79.2475 | 78.8195 | 207 | 45 | 68 | 9 |
| 92 | jubarte | jubarte-final@4f56a39e78ef | 79.2153 | 78.8195 | 207 | 45 | 68 | 10 |
| 93 | jubarte | jubarte-final@755ee30d148c | 79.2153 | 78.8195 | 207 | 45 | 68 | 10 |
| 94 | jubarte | jubarte-final@a764898a424c | 79.1583 | 78.7802 | 207 | 46 | 69 | 9 |
| 95 | jubarte | jubarte-final@a56814ce307c | 79.1225 | 78.7802 | 207 | 46 | 68 | 9 |
| 96 | jubarte | jubarte-final@310289c069e0 | 79.0409 | 80.8419 | 164 | 32 | 59 | 15 |
| 97 | jubarte | jubarte-final@ca80b3e3cbea | 78.185 | 80.8419 | 164 | 33 | 59 | 16 |
| 98 | jubarte | jubarte-final@037857ee3c92 | 78.078 | 80.2213 | 164 | 32 | 56 | 16 |
| 99 | jubarte | jubarte-final@b28f7c2cea39 | 78.0647 | 80.5247 | 164 | 31 | 56 | 15 |
| 100 | jubarte | jubarte-final@04dabff1cfaf | 77.824 | 78.6169 | 207 | 34 | 54 | 10 |
| 101 | jubarte | jubarte-final@ac1fcea44646 | 77.824 | 78.6169 | 207 | 34 | 54 | 10 |
| 102 | jubarte | jubarte-final@db8fcec5450c | 77.6222 | 80.0003 | 164 | 29 | 56 | 16 |
| 103 | jubarte | jubarte-final@089b9fd5a592 | 76.7878 | 79.9407 | 164 | 29 | 55 | 21 |
| 104 | jubarte | jubarte-final@1348076d3f43 | 76.4512 | 79.7617 | 164 | 29 | 54 | 22 |
| 105 | jubarte | jubarte-final@9cd65cfcd695 | 76.4087 | 79.7617 | 164 | 29 | 54 | 23 |
| 106 | jubarte | jubarte-final@55d2ba9dde27 | 75.386 | 78.5677 | 164 | 30 | 54 | 27 |
| 107 | jubarte | jubarte-final@a2f96a5ea5a5 | 75.386 | 78.5677 | 164 | 30 | 54 | 27 |
| 108 | jubarte | jubarte-final@efe615504e85 | 74.1128 | 74.3749 | 164 | 21 | 42 | 26 |
| 109 | jubarte | jubarte-final@717311c03d4f | 73.4761 | 73.1343 | 207 | 25 | 47 | 26 |
| 110 | sanity-word | — | 68.1679 | 70.4845 | 230 | 0 | 0 | 38 |
| 111 | jubarte-rust | jubarte-rust@6233a48e4ac8 | 66.3055 | 64.1705 | 196 | 0 | 21 | 32 |
| 112 | jubarte | jubarte-final@b4f90acaa85e | 64.6926 | 63.481 | 196 | 0 | 5 | 31 |
| 113 | jubarte-rust | jubarte-rust@b834d6e49fdb | 61.7832 | 59.2784 | 172 | 2 | 6 | 39 |
| 114 | docxodus | 7.0.0 | 58.7507 | 55.0306 | 205 | 3 | 7 | 66 |
| 115 | docxodus | 6.4.0 | 58.7425 | 55.0306 | 205 | 3 | 7 | 66 |
| 116 | superdoc-redlines | 0.2.0 | 57.6297 | 55.8997 | 192 | 0 | 1 | 63 |
| 117 | superdoc | 1.19.2 | 57.1871 | 55.5996 | 182 | 2 | 4 | 52 |
| 118 | folio | 0.3.1 | 55.3092 | 53.7539 | 205 | 0 | 1 | 75 |
| 119 | ooxmlsdk | — | 55.1866 | 55.2398 | 232 | 0 | 0 | 52 |
| 120 | docx-redline-js | — | 55.1236 | 55.1236 | 2 | 0 | 0 | 1 |
| 121 | redlines | 0.6.1 | 51.284 | 51.7682 | 200 | 0 | 0 | 84 |
| 122 | docx-redline-js | 0.3.0-ts-migration | 50.5319 | 50.2615 | 161 | 0 | 0 | 73 |
| 123 | jubarte | jubarte-final@9991b783a190 | 48.9496 | 49.8858 | 164 | 0 | 0 | 84 |

### `accepted_changes`

`accepted_changes`

| # | vendor | version | mean | median | n_docs | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | jubarte-rust | jubarte-rust@653876af82d6 | 89.5841 | 99.8896 | 164 | 78 | 105 | 5 |
| 2 | jubarte-rust | jubarte-rust@e12c880586ec | 89.5838 | 99.8896 | 164 | 78 | 105 | 5 |
| 3 | jubarte-rust | jubarte-rust@07493ca50fd6 | 89.5096 | 99.8896 | 164 | 78 | 105 | 6 |
| 4 | jubarte-rust | jubarte-rust@cbbcefb724a7 | 89.4476 | 99.7477 | 164 | 76 | 103 | 5 |
| 5 | jubarte-rust | jubarte-rust@f6cc3a6a7eb8 | 89.3128 | 99.8896 | 164 | 78 | 103 | 5 |
| 6 | jubarte-rust | jubarte-rust@28c41564723b | 87.1054 | 95.3936 | 164 | 69 | 95 | 8 |
| 7 | jubarte-rust | jubarte-rust@9fcc4289e375 | 87.0018 | 95.3936 | 164 | 69 | 95 | 9 |
| 8 | jubarte | jubarte-final@dd16ad8fbcf3 | 86.534 | 94.4179 | 164 | 63 | 87 | 7 |
| 9 | jubarte-rust | jubarte-rust@cdfef70a7156 | 84.2733 | 88.7405 | 164 | 54 | 80 | 7 |
| 10 | jubarte-rust | jubarte-rust@8e77f696f091 | 83.7563 | 87.9669 | 164 | 52 | 77 | 7 |
| 11 | jubarte | jubarte-final@717311c03d4f | 78.1534 | 80.639 | 166 | 26 | 43 | 14 |
| 12 | docxodus | 7.0.0 | 70.1963 | 74.9182 | 164 | 17 | 44 | 49 |
| 13 | docxodus | 6.4.0 | 68.9994 | 77.1882 | 164 | 14 | 22 | 43 |
| 14 | superdoc | 1.19.2 | 63.818 | 61.1184 | 150 | 2 | 3 | 33 |
| 15 | jubarte-rust | jubarte-rust@b834d6e49fdb | 63.499 | 54.4541 | 147 | 13 | 15 | 72 |
| 16 | folio | 0.3.1 | 57.9094 | 55.608 | 164 | 3 | 4 | 61 |

### `roundtrip`

roundtrip (self-diff → pdf_source)

| # | vendor | version | mean | median | n_docs | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | jubarte-rust | jubarte-rust@cbbcefb724a7 | 99.1706 | 100 | 166 | 157 | 161 | 1 |
| 2 | jubarte-rust | jubarte-rust@cdfef70a7156 | 99.1699 | 100 | 166 | 157 | 161 | 1 |
| 3 | jubarte-rust | jubarte-rust@fc29f56fd31d | 99.1697 | 100 | 166 | 157 | 161 | 1 |
| 4 | folio | 0.3.1 | 98.0712 | 100 | 198 | 185 | 190 | 4 |
| 5 | jubarte | jubarte-final@dd16ad8fbcf3 | 97.6313 | 100 | 166 | 152 | 156 | 3 |
| 6 | docxodus | 7.0.0 | 97.4281 | 100 | 166 | 148 | 157 | 4 |
| 7 | jubarte | jubarte-final@717311c03d4f | 94.4868 | 100 | 199 | 149 | 165 | 3 |
| 8 | jubarte-rust | jubarte-rust@b834d6e49fdb | 93.1152 | 100 | 171 | 120 | 137 | 6 |
| 9 | superdoc | 1.19.2 | 93.0017 | 100 | 194 | 144 | 158 | 8 |
| 10 | docxodus | 6.4.0 | 92.2445 | 100 | 198 | 144 | 161 | 13 |

### `visual_rendering`

visual_rendering (Playwright viewer)

| # | vendor | version | mean | median | n_docs | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | folio | 0.5.0 | 59.6494 | 55.0967 | 198 | 0 | 3 | 56 |
| 2 | superdoc | 1.44.1 | 58.7798 | 61.2486 | 199 | 0 | 0 | 38 |
| 3 | docxodus | 6.4.0-local.1 | 56.5017 | 49.7216 | 190 | 0 | 0 | 97 |
| 4 | docxodus | 7.0.0 | 56.5017 | 49.7216 | 190 | 0 | 0 | 97 |

### `visual_redlines`

visual_redlines (Playwright)

| # | vendor | version | mean | median | n_docs | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | 6.4.0 | 60.9207 | 61.2232 | 145 | 0 | 0 | 13 |
| 2 | superdoc | 1.44.1 | 55.3334 | 56.4237 | 164 | 0 | 0 | 44 |
| 3 | folio | 0.5.0 | 51.5494 | 51.6497 | 164 | 0 | 0 | 68 |
| 4 | docxodus | 7.0.0 | 48.2275 | 48.0758 | 164 | 0 | 0 | 122 |

### `visual_accepted_changes`

visual_accepted_changes (Playwright)

| # | vendor | version | mean | median | n_docs | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | 6.4.0 | 62.3235 | 62.7622 | 152 | 0 | 1 | 21 |
| 2 | folio | 0.5.0 | 59.671 | 54.9489 | 164 | 0 | 0 | 42 |
| 3 | superdoc | 1.44.1 | 59.3354 | 60.971 | 165 | 0 | 0 | 35 |

## All fidelity runs (flat)

| vendor | version | datetime | benchmark | mean | median | n_docs |
| --- | --- | --- | --- | --- | --- | --- |
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
| docxodus | 7.0.0 | 2026-07-10T21:37:40.839901+00:00 | script_redlines | 58.7507 | 55.0306 | 205 |
| docxodus | 7.0.0 | 2026-07-10T21:59:48.076126+00:00 | visual_redlines | 48.2275 | 48.0758 | 164 |
| docxodus | 7.0.0 | 2026-07-10T21:55:37.514080+00:00 | visual_rendering | 56.5017 | 49.7216 | 190 |
| folio | 0.3.1 | 2026-07-09T13:48:42.309993+00:00 | accepted_changes | 57.9094 | 55.608 | 164 |
| folio | 0.3.1 | 2026-07-10T00:18:18.365930+00:00 | roundtrip | 98.0712 | 100 | 198 |
| folio | 0.3.1 | 2026-07-09T13:01:34.270204+00:00 | script_redlines | 55.3092 | 53.7539 | 205 |
| folio | 0.5.0 | 2026-07-08T20:35:26.466209+00:00 | visual_accepted_changes | 59.671 | 54.9489 | 164 |
| folio | 0.5.0 | 2026-07-08T20:20:25.117836+00:00 | visual_redlines | 51.5494 | 51.6497 | 164 |
| folio | 0.5.0 | 2026-07-08T20:14:38.167302+00:00 | visual_rendering | 59.6494 | 55.0967 | 198 |
| jubarte | 0.1.0 | 2026-07-18T03:54:08.020820+00:00 | script_redlines | 83.4039 | 88.6547 | 164 |
| jubarte | jubarte-final@037857ee3c92 | 2026-07-30T11:35:09.023358+00:00 | script_redlines | 78.078 | 80.2213 | 164 |
| jubarte | jubarte-final@04dabff1cfaf | 2026-07-11T00:05:44.072714+00:00 | script_redlines | 77.824 | 78.6169 | 207 |
| jubarte | jubarte-final@074c4727e65d | 2026-07-31T05:51:19.092773+00:00 | script_redlines | 87.9968 | 91.5066 | 163 |
| jubarte | jubarte-final@089b9fd5a592 | 2026-07-30T06:02:04.657030+00:00 | script_redlines | 76.7878 | 79.9407 | 164 |
| jubarte | jubarte-final@1348076d3f43 | 2026-07-30T05:40:54.600019+00:00 | script_redlines | 76.4512 | 79.7617 | 164 |
| jubarte | jubarte-final@138efcf0b70b | 2026-07-30T15:40:23.260121+00:00 | script_redlines | 83.4424 | 88.614 | 164 |
| jubarte | jubarte-final@15ed9cf09abd | 2026-07-30T21:21:11.870475+00:00 | script_redlines | 84.617 | 89.3249 | 163 |
| jubarte | jubarte-final@1d02711eb646 | 2026-07-31T11:38:16.368658+00:00 | script_redlines | 89.6394 | 91.9481 | 163 |
| jubarte | jubarte-final@1e9ac33b7ca8 | 2026-07-31T09:28:47.859105+00:00 | script_redlines | 87.5086 | 90.6342 | 163 |
| jubarte | jubarte-final@218fbf85cc92 | 2026-07-31T10:02:28.471192+00:00 | script_redlines | 88.2694 | 91.5066 | 163 |
| jubarte | jubarte-final@28f85285d077 | 2026-07-31T09:37:52.209821+00:00 | script_redlines | 87.4732 | 90.6342 | 163 |
| jubarte | jubarte-final@2f41358dbc2c | 2026-07-15T12:21:54.426896+00:00 | script_redlines | 83.4039 | 88.6547 | 164 |
| jubarte | jubarte-final@310289c069e0 | 2026-07-30T11:57:05.680767+00:00 | script_redlines | 79.0409 | 80.8419 | 164 |
| jubarte | jubarte-final@37789c3f7619 | 2026-07-30T23:15:53.775791+00:00 | script_redlines | 85.3131 | 89.4571 | 163 |
| jubarte | jubarte-final@3995702f73ed | 2026-07-31T12:24:01.065048+00:00 | script_redlines | 90.0433 | 91.9856 | 163 |
| jubarte | jubarte-final@3a492480108b | 2026-07-31T04:21:46.044954+00:00 | script_redlines | 86.3084 | 89.4587 | 163 |
| jubarte | jubarte-final@3a499185d2a6 | 2026-07-30T19:13:37.987453+00:00 | script_redlines | 83.546 | 88.6089 | 163 |
| jubarte | jubarte-final@453850c8087b | 2026-07-31T02:23:21.188303+00:00 | script_redlines | 84.8877 | 88.6191 | 163 |
| jubarte | jubarte-final@45e96376aa20 | 2026-07-30T21:41:26.590878+00:00 | script_redlines | 84.8108 | 89.4571 | 163 |
| jubarte | jubarte-final@4f003998b8fa | 2026-07-30T17:39:44.029508+00:00 | script_redlines | 83.6628 | 88.8518 | 164 |
| jubarte | jubarte-final@4f56a39e78ef | 2026-07-11T00:30:15.977616+00:00 | script_redlines | 79.2153 | 78.8195 | 207 |
| jubarte | jubarte-final@52e796946879 | 2026-07-31T05:32:22.262741+00:00 | script_redlines | 87.3192 | 90.5514 | 163 |
| jubarte | jubarte-final@55d2ba9dde27 | 2026-07-30T05:02:38.532218+00:00 | script_redlines | 75.386 | 78.5677 | 164 |
| jubarte | jubarte-final@576b0f787e47+git.885b34c2da64df79ab7f82017e13ad53313b217b | 2026-07-18T06:19:47.066261+00:00 | script_redlines | 83.4039 | 88.6547 | 164 |
| jubarte | jubarte-final@5778f88898ac | 2026-07-31T03:21:01.755273+00:00 | script_redlines | 86.3437 | 89.4587 | 163 |
| jubarte | jubarte-final@591b7504a890 | 2026-07-30T13:32:07.986651+00:00 | script_redlines | 83.4375 | 88.8518 | 164 |
| jubarte | jubarte-final@5e534b75b66a | 2026-07-30T14:32:09.349466+00:00 | script_redlines | 83.5133 | 88.8518 | 164 |
| jubarte | jubarte-final@6481c2fdbfc0 | 2026-07-11T00:38:01.460324+00:00 | script_redlines | 79.2475 | 78.8195 | 207 |
| jubarte | jubarte-final@6e909b7b4408 | 2026-07-31T10:33:31.259889+00:00 | script_redlines | 88.9047 | 91.9836 | 163 |
| jubarte | jubarte-final@70986060934f | 2026-07-30T15:46:45.680104+00:00 | script_redlines | 83.7379 | 89.2047 | 164 |
| jubarte | jubarte-final@717311c03d4f | 2026-07-09T00:19:24.490489+00:00 | accepted_changes | 78.1534 | 80.639 | 166 |
| jubarte | jubarte-final@717311c03d4f | 2026-07-10T00:06:11.537044+00:00 | roundtrip | 94.4868 | 100 | 199 |
| jubarte | jubarte-final@717311c03d4f | 2026-07-09T00:28:15.005270+00:00 | script_redlines | 73.4761 | 73.1343 | 207 |
| jubarte | jubarte-final@755ee30d148c | 2026-07-11T00:22:44.799718+00:00 | script_redlines | 79.2153 | 78.8195 | 207 |
| jubarte | jubarte-final@757360aba6a2 | 2026-07-30T12:45:09.842662+00:00 | script_redlines | 82.6342 | 88.0854 | 164 |
| jubarte | jubarte-final@77d67f774b3e | 2026-07-30T12:13:33.635147+00:00 | script_redlines | 80.7225 | 84.8619 | 164 |
| jubarte | jubarte-final@8b23cdc7eca8 | 2026-07-13T16:52:37.466270+00:00 | script_redlines | 79.2696 | 79.9471 | 207 |
| jubarte | jubarte-final@8b2e9bf2522a | 2026-07-13T23:45:59.667934+00:00 | script_redlines | 83.4234 | 88.6547 | 164 |
| jubarte | jubarte-final@9650d0f6fd09 | 2026-07-30T15:31:09.495686+00:00 | script_redlines | 83.2401 | 88.614 | 164 |
| jubarte | jubarte-final@983daed413e2 | 2026-07-31T11:42:28.864666+00:00 | script_redlines | 89.694 | 91.9481 | 163 |
| jubarte | jubarte-final@9991b783a190 | 2026-07-16T00:25:00.606780+00:00 | script_redlines | 48.9496 | 49.8858 | 164 |
| jubarte | jubarte-final@9cd65cfcd695 | 2026-07-30T05:19:06.323862+00:00 | script_redlines | 76.4087 | 79.7617 | 164 |
| jubarte | jubarte-final@9d7adf85bd3b | 2026-07-31T10:22:40.702135+00:00 | script_redlines | 88.6992 | 91.8424 | 163 |
| jubarte | jubarte-final@9e40ef84f1f0 | 2026-07-30T13:19:07.468413+00:00 | script_redlines | 83.2014 | 88.614 | 164 |
| jubarte | jubarte-final@9fdd4b0b75bd | 2026-07-31T11:26:44.144802+00:00 | script_redlines | 89.3794 | 91.9481 | 163 |
| jubarte | jubarte-final@a2f96a5ea5a5 | 2026-07-30T04:50:07.524053+00:00 | script_redlines | 75.386 | 78.5677 | 164 |
| jubarte | jubarte-final@a383f41fcf20 | 2026-07-31T03:48:06.024869+00:00 | script_redlines | 86.5619 | 89.6075 | 163 |
| jubarte | jubarte-final@a3f3744cd0c4 | 2026-07-31T04:47:11.875061+00:00 | script_redlines | 87.3174 | 90.5514 | 163 |
| jubarte | jubarte-final@a56814ce307c | 2026-07-11T01:10:08.212708+00:00 | script_redlines | 79.1225 | 78.7802 | 207 |
| jubarte | jubarte-final@a57e820404f3 | 2026-07-30T13:46:04.424550+00:00 | script_redlines | 83.5609 | 88.8518 | 164 |
| jubarte | jubarte-final@a764898a424c | 2026-07-11T01:22:46.221863+00:00 | script_redlines | 79.1583 | 78.7802 | 207 |
| jubarte | jubarte-final@ac1fcea44646 | 2026-07-10T23:54:03.912780+00:00 | script_redlines | 77.824 | 78.6169 | 207 |
| jubarte | jubarte-final@af5279d4ff9d | 2026-07-30T12:40:47.288583+00:00 | script_redlines | 82.5623 | 88.0854 | 164 |
| jubarte | jubarte-final@b0f6fcbfb69f | 2026-07-31T10:55:24.260583+00:00 | script_redlines | 89.263 | 91.9836 | 163 |
| jubarte | jubarte-final@b28f7c2cea39 | 2026-07-30T11:21:58.513083+00:00 | script_redlines | 78.0647 | 80.5247 | 164 |
| jubarte | jubarte-final@b4f90acaa85e | 2026-07-11T02:12:18.691781+00:00 | script_redlines | 64.6926 | 63.481 | 196 |
| jubarte | jubarte-final@bac9423e07f0 | 2026-07-31T04:36:41.662278+00:00 | script_redlines | 87.0779 | 90.2449 | 163 |
| jubarte | jubarte-final@bdad6a0a16a8 | 2026-07-31T09:43:13.612070+00:00 | script_redlines | 88.1228 | 91.3598 | 163 |
| jubarte | jubarte-final@be0804dde638+git.4518f52ab32ae788012a7446471043fb51674c20 | 2026-07-18T07:34:58.171870+00:00 | script_redlines | 83.6291 | 88.9633 | 164 |
| jubarte | jubarte-final@c27e3f635094 | 2026-07-30T12:49:39.325736+00:00 | script_redlines | 83.1808 | 88.614 | 164 |
| jubarte | jubarte-final@c7771d920f75 | 2026-07-31T11:02:14.600896+00:00 | script_redlines | 89.4468 | 91.9836 | 163 |
| jubarte | jubarte-final@ca31e561ca95 | 2026-07-31T11:33:32.455722+00:00 | script_redlines | 89.5095 | 91.9481 | 163 |
| jubarte | jubarte-final@ca80b3e3cbea | 2026-07-30T11:49:51.297099+00:00 | script_redlines | 78.185 | 80.8419 | 164 |
| jubarte | jubarte-final@cd25600d93c2 | 2026-07-31T00:53:47.162619+00:00 | script_redlines | 85.4334 | 89.4571 | 163 |
| jubarte | jubarte-final@d5bd12d173d6+git.aaa85454f569b7174dd99d5244877d29819a99b9 | 2026-07-18T06:36:02.529856+00:00 | script_redlines | 83.6291 | 88.9633 | 164 |
| jubarte | jubarte-final@d6601413148f | 2026-07-31T10:08:54.664051+00:00 | script_redlines | 88.568 | 91.727 | 163 |
| jubarte | jubarte-final@d7599c91e4d5 | 2026-07-15T12:32:02.889171+00:00 | script_redlines | 83.4039 | 88.6547 | 164 |
| jubarte | jubarte-final@da95efff703e | 2026-07-30T19:38:51.611512+00:00 | script_redlines | 83.668 | 89.0844 | 163 |
| jubarte | jubarte-final@db8fcec5450c | 2026-07-30T06:25:36.438288+00:00 | script_redlines | 77.6222 | 80.0003 | 164 |
| jubarte | jubarte-final@dbc8db9ef551 | 2026-07-15T12:17:34.829279+00:00 | script_redlines | 83.4037 | 88.6547 | 164 |
| jubarte | jubarte-final@dd16ad8fbcf3 | 2026-07-12T07:58:10.784184+00:00 | accepted_changes | 86.534 | 94.4179 | 164 |
| jubarte | jubarte-final@dd16ad8fbcf3 | 2026-07-12T07:58:10.784184+00:00 | roundtrip | 97.6313 | 100 | 166 |
| jubarte | jubarte-final@dd16ad8fbcf3 | 2026-07-12T07:58:10.784184+00:00 | script_redlines | 79.4364 | 79.9471 | 207 |
| jubarte | jubarte-final@e3e8440fde33 | 2026-07-31T03:43:21.089703+00:00 | script_redlines | 83.7754 | 84.4032 | 163 |
| jubarte | jubarte-final@e51a749ffed3 | 2026-07-30T22:07:13.930242+00:00 | script_redlines | 84.8799 | 89.4571 | 163 |
| jubarte | jubarte-final@e5877596422c | 2026-07-31T10:46:38.882847+00:00 | script_redlines | 89.0074 | 91.9836 | 163 |
| jubarte | jubarte-final@efe615504e85 | 2026-07-30T04:38:34.990709+00:00 | script_redlines | 74.1128 | 74.3749 | 164 |
| jubarte | jubarte-final@f3ac233ba2cb | 2026-07-30T21:10:46.398529+00:00 | script_redlines | 84.3075 | 89.3249 | 163 |
| jubarte-rust | jubarte-rust@01ed1fac181e | 2026-07-16T22:55:02.140625+00:00 | script_redlines | 84.2081 | 93.0906 | 196 |
| jubarte-rust | jubarte-rust@07493ca50fd6 | 2026-07-16T16:52:48.692756+00:00 | accepted_changes | 89.5096 | 99.8896 | 164 |
| jubarte-rust | jubarte-rust@07493ca50fd6 | 2026-07-16T16:52:48.692756+00:00 | script_redlines | 92.1039 | 99.9187 | 164 |
| jubarte-rust | jubarte-rust@21f394cb95d8 | 2026-07-16T22:25:56.821511+00:00 | script_redlines | 84.2081 | 93.0906 | 196 |
| jubarte-rust | jubarte-rust@267e2e589504 | 2026-07-15T17:33:08.665862+00:00 | script_redlines | 84.4755 | 89.4719 | 164 |
| jubarte-rust | jubarte-rust@27b57358b1c3 | 2026-07-15T17:38:41.179863+00:00 | script_redlines | 84.7354 | 89.3449 | 164 |
| jubarte-rust | jubarte-rust@28c41564723b | 2026-07-16T14:48:33.227946+00:00 | accepted_changes | 87.1054 | 95.3936 | 164 |
| jubarte-rust | jubarte-rust@28c41564723b | 2026-07-16T14:57:29.076498+00:00 | script_redlines | 84.009 | 93.0906 | 196 |
| jubarte-rust | jubarte-rust@3838e1a2c0ae | 2026-07-15T18:13:36.622865+00:00 | script_redlines | 85.2628 | 89.4719 | 164 |
| jubarte-rust | jubarte-rust@3ad02b0cd59e | 2026-07-16T22:15:20.559801+00:00 | script_redlines | 90.1694 | 98.7613 | 164 |
| jubarte-rust | jubarte-rust@4ab62a18cf7a | 2026-07-18T03:49:20.923395+00:00 | script_redlines | 91.9831 | 99.904 | 164 |
| jubarte-rust | jubarte-rust@4f964f7612f5 | 2026-07-16T15:04:52.289384+00:00 | script_redlines | 90.4602 | 95.6735 | 164 |
| jubarte-rust | jubarte-rust@51a93adf52ca | 2026-07-13T01:57:49.073008+00:00 | script_redlines | 80.2389 | 83.1955 | 207 |
| jubarte-rust | jubarte-rust@5e1d044ac048 | 2026-07-16T15:51:29.108735+00:00 | script_redlines | 84.1728 | 93.0906 | 196 |
| jubarte-rust | jubarte-rust@6233a48e4ac8 | 2026-07-11T02:17:46.130799+00:00 | script_redlines | 66.3055 | 64.1705 | 196 |
| jubarte-rust | jubarte-rust@63e57d122c83 | 2026-07-17T01:25:59.934705+00:00 | script_redlines | 92.2148 | 99.9187 | 164 |
| jubarte-rust | jubarte-rust@653876af82d6 | 2026-07-16T17:07:18.689291+00:00 | accepted_changes | 89.5841 | 99.8896 | 164 |
| jubarte-rust | jubarte-rust@653876af82d6 | 2026-07-16T17:20:21.134814+00:00 | script_redlines | 84.172 | 93.0906 | 196 |
| jubarte-rust | jubarte-rust@6b5740328b0a | 2026-07-16T16:33:52.098131+00:00 | script_redlines | 84.172 | 93.0906 | 196 |
| jubarte-rust | jubarte-rust@7eca5f3f80f7 | 2026-07-17T06:20:16.532124+00:00 | script_redlines | 91.9831 | 99.904 | 164 |
| jubarte-rust | jubarte-rust@8a970b82f860 | 2026-07-15T18:08:21.829429+00:00 | script_redlines | 85.0487 | 89.3449 | 164 |
| jubarte-rust | jubarte-rust@8e77f696f091 | 2026-07-15T15:36:32.217189+00:00 | accepted_changes | 83.7563 | 87.9669 | 164 |
| jubarte-rust | jubarte-rust@8e77f696f091 | 2026-07-15T15:36:32.217189+00:00 | script_redlines | 83.7652 | 88.5162 | 164 |
| jubarte-rust | jubarte-rust@9190265c69a2 | 2026-07-16T16:13:12.470936+00:00 | script_redlines | 84.1728 | 93.0906 | 196 |
| jubarte-rust | jubarte-rust@980adfca2fc6 | 2026-07-15T17:48:46.133050+00:00 | script_redlines | 84.8331 | 89.3449 | 164 |
| jubarte-rust | jubarte-rust@9882dd52cc11 | 2026-07-17T02:19:40.108625+00:00 | script_redlines | 91.9831 | 99.904 | 164 |
| jubarte-rust | jubarte-rust@9fcc4289e375 | 2026-07-16T05:49:13.232283+00:00 | accepted_changes | 87.0018 | 95.3936 | 164 |
| jubarte-rust | jubarte-rust@9fcc4289e375 | 2026-07-16T05:55:25.022684+00:00 | script_redlines | 83.1887 | 93.0906 | 196 |
| jubarte-rust | jubarte-rust@a8ff27ccff8f | 2026-07-16T21:56:23.579662+00:00 | script_redlines | 84.2078 | 93.0906 | 196 |
| jubarte-rust | jubarte-rust@aad3e04cebbd | 2026-07-15T18:02:55.334087+00:00 | script_redlines | 84.9762 | 89.3449 | 164 |
| jubarte-rust | jubarte-rust@ae865542c28f | 2026-07-16T22:05:44.488927+00:00 | script_redlines | 84.2078 | 93.0906 | 196 |
| jubarte-rust | jubarte-rust@b834d6e49fdb | 2026-07-09T17:43:37.147567+00:00 | accepted_changes | 63.499 | 54.4541 | 147 |
| jubarte-rust | jubarte-rust@b834d6e49fdb | 2026-07-10T00:21:53.149640+00:00 | roundtrip | 93.1152 | 100 | 171 |
| jubarte-rust | jubarte-rust@b834d6e49fdb | 2026-07-09T17:36:04.577266+00:00 | script_redlines | 61.7832 | 59.2784 | 172 |
| jubarte-rust | jubarte-rust@cbbcefb724a7 | 2026-07-24T15:00:45.969613+00:00 | accepted_changes | 89.4476 | 99.7477 | 164 |
| jubarte-rust | jubarte-rust@cbbcefb724a7 | 2026-07-24T15:00:45.969613+00:00 | roundtrip | 99.1706 | 100 | 166 |
| jubarte-rust | jubarte-rust@cbbcefb724a7 | 2026-07-24T15:00:45.969613+00:00 | script_redlines | 92.2147 | 99.9187 | 164 |
| jubarte-rust | jubarte-rust@cdfef70a7156 | 2026-07-12T08:09:01.073181+00:00 | accepted_changes | 84.2733 | 88.7405 | 164 |
| jubarte-rust | jubarte-rust@cdfef70a7156 | 2026-07-12T08:09:01.073181+00:00 | roundtrip | 99.1699 | 100 | 166 |
| jubarte-rust | jubarte-rust@cdfef70a7156 | 2026-07-12T08:09:01.073181+00:00 | script_redlines | 81.0444 | 84.7199 | 207 |
| jubarte-rust | jubarte-rust@cf12c65f1204 | 2026-07-17T03:15:59.269689+00:00 | script_redlines | 91.9831 | 99.904 | 164 |
| jubarte-rust | jubarte-rust@d269742c1397 | 2026-07-16T21:44:15.795654+00:00 | script_redlines | 91.9075 | 99.904 | 164 |
| jubarte-rust | jubarte-rust@e12c880586ec | 2026-07-16T17:44:52.569983+00:00 | accepted_changes | 89.5838 | 99.8896 | 164 |
| jubarte-rust | jubarte-rust@e12c880586ec | 2026-07-16T17:55:16.787714+00:00 | script_redlines | 84.2078 | 93.0906 | 196 |
| jubarte-rust | jubarte-rust@f46f60951d28 | 2026-07-17T04:59:32.591233+00:00 | script_redlines | 91.9831 | 99.904 | 164 |
| jubarte-rust | jubarte-rust@f6cc3a6a7eb8 | 2026-07-16T17:34:35.369086+00:00 | accepted_changes | 89.3128 | 99.8896 | 164 |
| jubarte-rust | jubarte-rust@f6cc3a6a7eb8 | 2026-07-16T17:34:35.369086+00:00 | script_redlines | 91.8526 | 99.9187 | 164 |
| jubarte-rust | jubarte-rust@f7960f5be6f3 | 2026-07-16T21:49:58.768940+00:00 | script_redlines | 91.8328 | 99.9187 | 164 |
| jubarte-rust | jubarte-rust@fc29f56fd31d | 2026-07-15T15:50:15.935561+00:00 | roundtrip | 99.1697 | 100 | 166 |
| jubarte-rust | jubarte-rust@fc29f56fd31d | 2026-07-15T15:50:15.935561+00:00 | script_redlines | 83.7652 | 88.5162 | 164 |
| jubarte-wasm | 0.1.0 | 2026-07-24T15:13:19.462654+00:00 | script_redlines | 92.2147 | 99.9187 | 164 |
| ooxmlsdk | — | 2026-07-13T17:24:50.712941+00:00 | script_redlines | 55.1866 | 55.2398 | 232 |
| prebaked | — | 2026-07-18T03:38:23.898589+00:00 | script_redlines | 100 | 100 | 1 |
| redlines | 0.6.1 | 2026-07-12T07:38:29.295760+00:00 | script_redlines | 51.284 | 51.7682 | 200 |
| sanity-word | — | 2026-07-13T18:06:21.529826+00:00 | script_redlines | 68.1679 | 70.4845 | 230 |
| superdoc | 1.19.2 | 2026-07-09T15:38:31.872437+00:00 | accepted_changes | 63.818 | 61.1184 | 150 |
| superdoc | 1.19.2 | 2026-07-09T18:25:24.395459+00:00 | roundtrip | 93.0017 | 100 | 194 |
| superdoc | 1.19.2 | 2026-07-09T15:34:17.469383+00:00 | script_redlines | 57.1871 | 55.5996 | 182 |
| superdoc | 1.44.1 | 2026-07-09T18:25:37.273372+00:00 | visual_accepted_changes | 59.3354 | 60.971 | 165 |
| superdoc | 1.44.1 | 2026-07-09T18:22:07.033240+00:00 | visual_redlines | 55.3334 | 56.4237 | 164 |
| superdoc | 1.44.1 | 2026-07-09T18:16:46.431642+00:00 | visual_rendering | 58.7798 | 61.2486 | 199 |
| superdoc-redlines | 0.2.0 | 2026-07-12T08:32:43.871610+00:00 | script_redlines | 57.6297 | 55.8997 | 192 |

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
| 1 | docxodus | dotnet-wasm | 200 | 500 | 148.753 | 607.385 | 3212.297 | 7017.889 | 1.6 | 496 | 4 | — |
| 2 | docxodus-csharp | dotnet | 50 | 50 | 208.388 | 441.646 | 911.873 | 1154.008 | 2.3 | 50 | 0 | — |
| 3 | jubarte-lossless | node | 1000 | 5000 | 54.642 | 168.184 | 592.49 | 1191.719 | 5.9 | 4997 | 3 | — |
| 4 | jubarte-native | node | 1000 | 5000 | 14.43 | 57.145 | 175.709 | 578.45 | 17.5 | 5000 | 0 | — |
| 5 | jubarte-wasm | rust-wasm | 1000 | 5000 | 9.717 | 41.44 | 180.492 | 273.407 | 24.1 | 5000 | 0 | — |
| 6 | jubarte-rust-inproc | rust | 1000 | 5000 | 8.54 | 33.049 | 138.572 | 231.746 | 30.3 | 5000 | 0 | — |
| 7 | jubarte-rust | rust | 1000 | 5000 | 9.656 | 31.022 | 123.386 | 195.751 | 32.2 | 5000 | 0 | — |
| 8 | docxodus-csharp-inproc | dotnet | 1000 | 5000 | 9.431 | 29.903 | 110.731 | 234.991 | 33.4 | 4880 | 120 | v8-inspector |

### Speed methodology notes

- Dedup key: `(kind, tool, unit)`. Best re-run by `(n, −median, run_ts)`.
- `speed_redlines` rows with **n < 10** are dropped as trivial smokes.
- Profiles (when present): samply `.profile.json.gz` for native CLIs/workers; V8 `.cpuprofile` for in-process Node (e.g. jubarte-lossless).
- Regenerate after a run: `python3 scripts/export-results-md.py`.

## Methodology notes (fidelity)

- Deduplication: one line per `(vendor, benchmark, tool_version)`. Re-runs of the **same** triple keep the best by `(render_fit, n_docs, overall_mean, timestamp)` — prefer playwright for `visual_*` and soffice for script/accepted/roundtrip, then higher n / mean.
- **Versions are not collapsed.** docxodus `6.4.0` and `7.0.0` both appear so pins can be compared directly.
- **docxodus** filter: rows with **`n_docs ≤ 100`** are dropped (smoke / partial runs such as `visual_rendering` with n=21 or n=2). Full-corpus pins (typically n ≳ 145) are kept for every version.
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

Regenerate: `python3 scripts/export-results-md.py` (reads `results/bench.jsonl` + `results/speed.jsonl`).


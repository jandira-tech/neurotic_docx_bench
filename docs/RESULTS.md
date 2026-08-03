# Benchmark results

Source: `results/bench.jsonl` — **162** fidelity row(s) (one per vendor×benchmark×**version**; 128 distinct vendor×version pin(s). docxodus rows with n_docs ≤ 100 are dropped as smoke/partial).

Scores are 0–100 (higher = closer to the Microsoft Word oracle). Cross-renderer comparisons (LibreOffice vs Playwright) are **not** directly comparable — only compare within the same benchmark. Different **versions** of the same vendor are kept so you can compare pins (e.g. docxodus 6.4.0 vs 7.0.0).

## Rankings by benchmark

### `script_redlines`

script_redlines (LibreOffice render vs Word oracle)

| # | vendor | version | mean | median | itt_mean | itt_median | skill_median | failures | n_docs | itt_n | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | jubarte-rust | jubarte-rust@01ed1fac181e | 92.2148 | 99.9187 | 92.2148 | 99.9187 | — | 0 | 164 | 164 | 80 | 122 | 3 |
| 2 | jubarte-rust | jubarte-rust@63e57d122c83 | 92.2148 | 99.9187 | 92.2148 | 99.9187 | — | 0 | 164 | 164 | 80 | 122 | 3 |
| 3 | jubarte-rust | jubarte-rust@cbbcefb724a7 | 92.2147 | 99.9187 | 92.2147 | 99.9187 | — | 0 | 164 | 164 | 80 | 122 | 3 |
| 4 | jubarte-wasm | 0.1.0 | 92.2147 | 99.9187 | 92.2147 | 99.9187 | — | 0 | 164 | 164 | 80 | 122 | 3 |
| 5 | jubarte-rust | jubarte-rust@07493ca50fd6 | 92.1039 | 99.9187 | 92.1039 | 99.9187 | — | 0 | 164 | 164 | 80 | 122 | 5 |
| 6 | jubarte-rust | jubarte-rust@f6cc3a6a7eb8 | 91.8526 | 99.9187 | 91.8526 | 99.9187 | — | 0 | 164 | 164 | 80 | 120 | 3 |
| 7 | jubarte-rust | jubarte-rust@f7960f5be6f3 | 91.8328 | 99.9187 | 91.8328 | 99.9187 | — | 0 | 164 | 164 | 80 | 120 | 2 |
| 8 | jubarte-rust | jubarte-rust@4ab62a18cf7a | 91.9831 | 99.904 | 91.9831 | 99.904 | — | 0 | 164 | 164 | 79 | 121 | 3 |
| 9 | jubarte-rust | jubarte-rust@7eca5f3f80f7 | 91.9831 | 99.904 | 91.9831 | 99.904 | — | 0 | 164 | 164 | 79 | 121 | 3 |
| 10 | jubarte-rust | jubarte-rust@9882dd52cc11 | 91.9831 | 99.904 | 91.9831 | 99.904 | — | 0 | 164 | 164 | 79 | 121 | 3 |
| 11 | jubarte-rust | jubarte-rust@cf12c65f1204 | 91.9831 | 99.904 | 91.9831 | 99.904 | — | 0 | 164 | 164 | 79 | 121 | 3 |
| 12 | jubarte-rust | jubarte-rust@f46f60951d28 | 91.9831 | 99.904 | 91.9831 | 99.904 | — | 0 | 164 | 164 | 79 | 121 | 3 |
| 13 | jubarte-rust | jubarte-rust@d269742c1397 | 91.9075 | 99.904 | 91.9075 | 99.904 | — | 0 | 164 | 164 | 79 | 121 | 3 |
| 14 | jubarte-rust | jubarte-rust@3ad02b0cd59e | 90.1694 | 98.7613 | 90.1694 | 98.7613 | — | 0 | 164 | 164 | 69 | 111 | 3 |
| 15 | jubarte-rust | jubarte-rust@4f964f7612f5 | 90.4602 | 95.6735 | 90.4602 | 95.6735 | — | 0 | 164 | 164 | 62 | 110 | 5 |
| 16 | jubarte-rust | jubarte-rust@9fcc4289e375 | 90.0375 | 95.6735 | 90.0375 | 95.6735 | — | 0 | 164 | 164 | 62 | 110 | 8 |
| 17 | jubarte-rust | jubarte-rust@fcea02da49f4 | 85.0239 | 93.3681 | 85.0239 | 93.3681 | 86.1884 | 0 | 383 | 383 | 126 | 220 | 21 |
| 18 | jubarte-rust | jubarte-rust@21f394cb95d8 | 84.2081 | 93.0906 | 84.2081 | 93.0906 | — | 0 | 196 | 196 | 68 | 107 | 9 |
| 19 | jubarte-rust | jubarte-rust@a8ff27ccff8f | 84.2078 | 93.0906 | 84.2078 | 93.0906 | — | 0 | 196 | 196 | 68 | 107 | 9 |
| 20 | jubarte-rust | jubarte-rust@ae865542c28f | 84.2078 | 93.0906 | 84.2078 | 93.0906 | — | 0 | 196 | 196 | 68 | 107 | 9 |
| 21 | jubarte-rust | jubarte-rust@e12c880586ec | 84.2078 | 93.0906 | 84.2078 | 93.0906 | — | 0 | 196 | 196 | 68 | 107 | 9 |
| 22 | jubarte-rust | jubarte-rust@5e1d044ac048 | 84.1728 | 93.0906 | 84.1728 | 93.0906 | — | 0 | 196 | 196 | 69 | 107 | 9 |
| 23 | jubarte-rust | jubarte-rust@9190265c69a2 | 84.1728 | 93.0906 | 84.1728 | 93.0906 | — | 0 | 196 | 196 | 69 | 107 | 9 |
| 24 | jubarte-rust | jubarte-rust@653876af82d6 | 84.172 | 93.0906 | 84.172 | 93.0906 | — | 0 | 196 | 196 | 68 | 107 | 9 |
| 25 | jubarte-rust | jubarte-rust@6b5740328b0a | 84.172 | 93.0906 | 84.172 | 93.0906 | — | 0 | 196 | 196 | 68 | 107 | 9 |
| 26 | jubarte-rust | jubarte-rust@28c41564723b | 84.009 | 93.0906 | 84.009 | 93.0906 | — | 0 | 196 | 196 | 69 | 107 | 9 |
| 27 | jubarte | jubarte-final@3995702f73ed | 90.0433 | 91.9856 | 87.8866 | 91.8424 | — | 4 | 163 | 167 | 44 | 92 | 0 |
| 28 | jubarte | jubarte-final@c7771d920f75 | 89.4468 | 91.9836 | 87.3043 | 91.8424 | — | 4 | 163 | 167 | 43 | 93 | 0 |
| 29 | jubarte | jubarte-final@b0f6fcbfb69f | 89.263 | 91.9836 | 87.1249 | 91.8424 | — | 4 | 163 | 167 | 43 | 93 | 0 |
| 30 | jubarte | jubarte-final@e5877596422c | 89.0074 | 91.9836 | 86.8755 | 91.8424 | — | 4 | 163 | 167 | 43 | 93 | 0 |
| 31 | jubarte | jubarte-final@6e909b7b4408 | 88.9047 | 91.9836 | 86.7753 | 91.8424 | — | 4 | 163 | 167 | 43 | 93 | 0 |
| 32 | jubarte | jubarte-final@983daed413e2 | 89.694 | 91.9481 | 87.5456 | 91.727 | — | 4 | 163 | 167 | 43 | 91 | 0 |
| 33 | jubarte | jubarte-final@1d02711eb646 | 89.6394 | 91.9481 | 87.4924 | 91.727 | — | 4 | 163 | 167 | 43 | 91 | 0 |
| 34 | jubarte | jubarte-final@ca31e561ca95 | 89.5095 | 91.9481 | 87.3655 | 91.727 | — | 4 | 163 | 167 | 43 | 91 | 0 |
| 35 | jubarte | jubarte-final@9fdd4b0b75bd | 89.3794 | 91.9481 | 87.2386 | 91.727 | — | 4 | 163 | 167 | 43 | 90 | 0 |
| 36 | jubarte | jubarte-final@9d7adf85bd3b | 88.6992 | 91.8424 | 86.5746 | 91.692 | — | 4 | 163 | 167 | 43 | 91 | 0 |
| 37 | jubarte | jubarte-final@d6601413148f | 88.568 | 91.727 | 86.4466 | 91.5066 | — | 4 | 163 | 167 | 42 | 90 | 0 |
| 38 | jubarte | jubarte-final@218fbf85cc92 | 88.2694 | 91.5066 | 86.1552 | 91.3515 | — | 4 | 163 | 167 | 42 | 89 | 0 |
| 39 | jubarte | jubarte-final@074c4727e65d | 87.9968 | 91.5066 | 85.8891 | 91.1957 | — | 4 | 163 | 167 | 41 | 88 | 0 |
| 40 | jubarte | jubarte-final@bdad6a0a16a8 | 88.1228 | 91.3598 | 86.0121 | 91.1601 | — | 4 | 163 | 167 | 41 | 87 | 0 |
| 41 | jubarte | jubarte-final@1e9ac33b7ca8 | 87.5086 | 90.6342 | 85.4125 | 90.5177 | — | 4 | 163 | 167 | 38 | 85 | 0 |
| 42 | jubarte | jubarte-final@28f85285d077 | 87.4732 | 90.6342 | 85.378 | 90.2449 | — | 4 | 163 | 167 | 38 | 84 | 0 |
| 43 | jubarte | jubarte-final@52e796946879 | 87.3192 | 90.5514 | 85.2277 | 89.6075 | — | 4 | 163 | 167 | 40 | 83 | 0 |
| 44 | jubarte | jubarte-final@a3f3744cd0c4 | 87.3174 | 90.5514 | 85.226 | 89.6075 | — | 4 | 163 | 167 | 40 | 83 | 0 |
| 45 | jubarte-rust | jubarte-rust@3838e1a2c0ae | 85.2628 | 89.4719 | 85.2628 | 89.4719 | — | 0 | 164 | 164 | 48 | 79 | 6 |
| 46 | jubarte-rust | jubarte-rust@267e2e589504 | 84.4755 | 89.4719 | 84.4755 | 89.4719 | — | 0 | 164 | 164 | 47 | 79 | 6 |
| 47 | jubarte | jubarte-final@bac9423e07f0 | 87.0779 | 90.2449 | 84.9922 | 89.4587 | — | 4 | 163 | 167 | 40 | 82 | 0 |
| 48 | jubarte | jubarte-final@a383f41fcf20 | 86.5619 | 89.6075 | 84.4886 | 89.4571 | — | 4 | 163 | 167 | 39 | 81 | 0 |
| 49 | jubarte-rust | jubarte-rust@8a970b82f860 | 85.0487 | 89.3449 | 85.0487 | 89.3449 | — | 0 | 164 | 164 | 48 | 78 | 6 |
| 50 | jubarte-rust | jubarte-rust@aad3e04cebbd | 84.9762 | 89.3449 | 84.9762 | 89.3449 | — | 0 | 164 | 164 | 48 | 78 | 6 |
| 51 | jubarte-rust | jubarte-rust@980adfca2fc6 | 84.8331 | 89.3449 | 84.8331 | 89.3449 | — | 0 | 164 | 164 | 48 | 78 | 6 |
| 52 | jubarte-rust | jubarte-rust@27b57358b1c3 | 84.7354 | 89.3449 | 84.7354 | 89.3449 | — | 0 | 164 | 164 | 47 | 78 | 6 |
| 53 | jubarte | jubarte-final@5778f88898ac | 86.3437 | 89.4587 | 84.2756 | 89.3249 | — | 4 | 163 | 167 | 39 | 80 | 0 |
| 54 | jubarte | jubarte-final@3a492480108b | 86.3084 | 89.4587 | 84.2411 | 89.3249 | — | 4 | 163 | 167 | 38 | 80 | 0 |
| 55 | jubarte | jubarte-final@cd25600d93c2 | 85.4334 | 89.4571 | 83.3871 | 89.0844 | — | 4 | 163 | 167 | 38 | 79 | 0 |
| 56 | jubarte | jubarte-final@37789c3f7619 | 85.3131 | 89.4571 | 83.2696 | 89.0844 | — | 4 | 163 | 167 | 38 | 79 | 0 |
| 57 | jubarte | jubarte-final@70986060934f | 83.7379 | 89.2047 | 83.2304 | 89.0844 | — | 1 | 164 | 165 | 36 | 76 | 8 |
| 58 | jubarte | jubarte-final@e51a749ffed3 | 84.8799 | 89.4571 | 82.8469 | 89.0844 | — | 4 | 163 | 167 | 38 | 79 | 0 |
| 59 | jubarte | jubarte-final@45e96376aa20 | 84.8108 | 89.4571 | 82.7794 | 89.0844 | — | 4 | 163 | 167 | 38 | 79 | 1 |
| 60 | jubarte | jubarte-final@be0804dde638+git.4518f52ab32ae788012a7446471043fb51674c20 | 83.6291 | 88.9633 | 83.6291 | 88.9633 | — | 0 | 164 | 164 | 53 | 78 | 8 |
| 61 | jubarte | jubarte-final@d5bd12d173d6+git.aaa85454f569b7174dd99d5244877d29819a99b9 | 83.6291 | 88.9633 | 83.6291 | 88.9633 | — | 0 | 164 | 164 | 53 | 78 | 8 |
| 62 | jubarte | jubarte-final@8b2e9bf2522a | 83.4234 | 88.6547 | 83.4234 | 88.6547 | — | 0 | 164 | 164 | 53 | 77 | 8 |
| 63 | jubarte | jubarte-final@8b23cdc7eca8 | 83.4166 | 88.6547 | 83.4166 | 88.6547 | — | 0 | 164 | 164 | 53 | 77 | 8 |
| 64 | jubarte | 0.1.0 | 83.4039 | 88.6547 | 83.4039 | 88.6547 | — | 0 | 164 | 164 | 53 | 77 | 8 |
| 65 | jubarte | jubarte-final@2f41358dbc2c | 83.4039 | 88.6547 | 83.4039 | 88.6547 | — | 0 | 164 | 164 | 53 | 77 | 8 |
| 66 | jubarte | jubarte-final@576b0f787e47+git.885b34c2da64df79ab7f82017e13ad53313b217b | 83.4039 | 88.6547 | 83.4039 | 88.6547 | — | 0 | 164 | 164 | 53 | 77 | 8 |
| 67 | jubarte | jubarte-final@d7599c91e4d5 | 83.4039 | 88.6547 | 83.4039 | 88.6547 | — | 0 | 164 | 164 | 53 | 77 | 8 |
| 68 | jubarte | jubarte-final@dbc8db9ef551 | 83.4037 | 88.6547 | 83.4037 | 88.6547 | — | 0 | 164 | 164 | 53 | 77 | 8 |
| 69 | jubarte | jubarte-final@4f003998b8fa | 83.6628 | 88.8518 | 83.1557 | 88.6191 | — | 1 | 164 | 165 | 37 | 75 | 8 |
| 70 | jubarte | jubarte-final@a57e820404f3 | 83.5609 | 88.8518 | 83.0545 | 88.6191 | — | 1 | 164 | 165 | 36 | 76 | 10 |
| 71 | jubarte | jubarte-final@5e534b75b66a | 83.5133 | 88.8518 | 83.0071 | 88.6191 | — | 1 | 164 | 165 | 36 | 76 | 10 |
| 72 | jubarte | jubarte-final@591b7504a890 | 83.4375 | 88.8518 | 82.9318 | 88.6191 | — | 1 | 164 | 165 | 36 | 76 | 11 |
| 73 | jubarte | jubarte-final@15ed9cf09abd | 84.617 | 89.3249 | 82.5902 | 88.6191 | — | 4 | 163 | 167 | 38 | 78 | 2 |
| 74 | jubarte | jubarte-final@f3ac233ba2cb | 84.3075 | 89.3249 | 82.2881 | 88.6191 | — | 4 | 163 | 167 | 38 | 78 | 3 |
| 75 | jubarte | jubarte-final@138efcf0b70b | 83.4424 | 88.614 | 82.9367 | 88.6089 | — | 1 | 164 | 165 | 34 | 73 | 8 |
| 76 | jubarte | jubarte-final@9650d0f6fd09 | 83.2401 | 88.614 | 82.7356 | 88.6089 | — | 1 | 164 | 165 | 34 | 73 | 8 |
| 77 | jubarte | jubarte-final@9e40ef84f1f0 | 83.2014 | 88.614 | 82.6971 | 88.6089 | — | 1 | 164 | 165 | 35 | 75 | 11 |
| 78 | jubarte | jubarte-final@c27e3f635094 | 83.1808 | 88.614 | 82.6767 | 88.6089 | — | 1 | 164 | 165 | 35 | 75 | 11 |
| 79 | jubarte | jubarte-final@da95efff703e | 83.668 | 89.0844 | 81.664 | 88.6089 | — | 4 | 163 | 167 | 38 | 76 | 6 |
| 80 | jubarte-rust | jubarte-rust@8e77f696f091 | 83.7652 | 88.5162 | 83.7652 | 88.5162 | — | 0 | 164 | 164 | 44 | 75 | 8 |
| 81 | jubarte-rust | jubarte-rust@fc29f56fd31d | 83.7652 | 88.5162 | 83.7652 | 88.5162 | — | 0 | 164 | 164 | 44 | 75 | 8 |
| 82 | jubarte | jubarte-final@453850c8087b | 84.8877 | 88.6191 | 82.8544 | 88.4236 | — | 4 | 163 | 167 | 34 | 76 | 0 |
| 83 | jubarte | jubarte-final@757360aba6a2 | 82.6342 | 88.0854 | 82.1334 | 87.7471 | — | 1 | 164 | 165 | 35 | 73 | 12 |
| 84 | jubarte | jubarte-final@af5279d4ff9d | 82.5623 | 88.0854 | 82.0619 | 87.7471 | — | 1 | 164 | 165 | 35 | 73 | 12 |
| 85 | jubarte | jubarte-final@3a499185d2a6 | 83.546 | 88.6089 | 81.5449 | 87.7471 | — | 4 | 163 | 167 | 38 | 73 | 5 |
| 86 | jubarte | jubarte-final@d43557e042c1 | 82.2668 | 86.051 | 82.2668 | 86.051 | 53.0737 | 0 | 383 | 383 | 109 | 170 | 16 |
| 87 | jubarte-rust | jubarte-rust@cdfef70a7156 | 81.0444 | 84.7199 | 81.0444 | 84.7199 | — | 0 | 207 | 207 | 42 | 84 | 17 |
| 88 | jubarte | jubarte-final@77d67f774b3e | 80.7225 | 84.8619 | 80.2333 | 84.4032 | — | 1 | 164 | 165 | 32 | 68 | 15 |
| 89 | jubarte | jubarte-final@e3e8440fde33 | 83.7754 | 84.4032 | 81.7688 | 84.0751 | — | 4 | 163 | 167 | 32 | 66 | 1 |
| 90 | jubarte-rust | jubarte-rust@51a93adf52ca | 80.2389 | 83.1955 | 80.2389 | 83.1955 | — | 0 | 207 | 207 | 41 | 79 | 17 |
| 91 | jubarte | jubarte-final@310289c069e0 | 79.0409 | 80.8419 | 78.5618 | 80.5417 | — | 1 | 164 | 165 | 32 | 59 | 15 |
| 92 | jubarte | jubarte-final@ca80b3e3cbea | 78.185 | 80.8419 | 77.7112 | 80.5417 | — | 1 | 164 | 165 | 33 | 59 | 16 |
| 93 | jubarte | jubarte-final@b28f7c2cea39 | 78.0647 | 80.5247 | 77.5915 | 80.5077 | — | 1 | 164 | 165 | 31 | 56 | 15 |
| 94 | jubarte | jubarte-final@db8fcec5450c | 77.6222 | 80.0003 | 77.1517 | 79.9831 | — | 1 | 164 | 165 | 29 | 56 | 16 |
| 95 | jubarte | jubarte-final@dd16ad8fbcf3 | 79.4364 | 79.9471 | 79.4364 | 79.9471 | — | 0 | 207 | 207 | 54 | 77 | 13 |
| 96 | jubarte | jubarte-final@037857ee3c92 | 78.078 | 80.2213 | 77.6048 | 79.9349 | — | 1 | 164 | 165 | 32 | 56 | 16 |
| 97 | jubarte | jubarte-final@089b9fd5a592 | 76.7878 | 79.9407 | 76.3225 | 79.8983 | — | 1 | 164 | 165 | 29 | 55 | 21 |
| 98 | jubarte | jubarte-final@1348076d3f43 | 76.4512 | 79.7617 | 75.9879 | 79.6251 | — | 1 | 164 | 165 | 29 | 54 | 22 |
| 99 | jubarte | jubarte-final@9cd65cfcd695 | 76.4087 | 79.7617 | 75.9456 | 79.6251 | — | 1 | 164 | 165 | 29 | 54 | 23 |
| 100 | jubarte | jubarte-final@6481c2fdbfc0 | 79.2475 | 78.8195 | 79.2475 | 78.8195 | — | 0 | 207 | 207 | 45 | 68 | 9 |
| 101 | jubarte | jubarte-final@4f56a39e78ef | 79.2153 | 78.8195 | 79.2153 | 78.8195 | — | 0 | 207 | 207 | 45 | 68 | 10 |
| 102 | jubarte | jubarte-final@755ee30d148c | 79.2153 | 78.8195 | 79.2153 | 78.8195 | — | 0 | 207 | 207 | 45 | 68 | 10 |
| 103 | jubarte | jubarte-final@a764898a424c | 79.1583 | 78.7802 | 79.1583 | 78.7802 | — | 0 | 207 | 207 | 46 | 69 | 9 |
| 104 | jubarte | jubarte-final@a56814ce307c | 79.1225 | 78.7802 | 79.1225 | 78.7802 | — | 0 | 207 | 207 | 46 | 68 | 9 |
| 105 | jubarte | jubarte-final@04dabff1cfaf | 77.824 | 78.6169 | 77.824 | 78.6169 | — | 0 | 207 | 207 | 34 | 54 | 10 |
| 106 | jubarte | jubarte-final@ac1fcea44646 | 77.824 | 78.6169 | 77.824 | 78.6169 | — | 0 | 207 | 207 | 34 | 54 | 10 |
| 107 | jubarte | jubarte-final@55d2ba9dde27 | 75.386 | 78.5677 | 74.9291 | 78.2491 | — | 1 | 164 | 165 | 30 | 54 | 27 |
| 108 | jubarte | jubarte-final@a2f96a5ea5a5 | 75.386 | 78.5677 | 74.9291 | 78.2491 | — | 1 | 164 | 165 | 30 | 54 | 27 |
| 109 | jubarte-ast | jubarte-final@d43557e042c1 | 75.0012 | 77.1365 | 73.4346 | 75.452 | 74.8855 | 9 | 375 | 383 | 40 | 93 | 37 |
| 110 | jubarte | jubarte-final@efe615504e85 | 74.1128 | 74.3749 | 73.6637 | 74.1722 | — | 1 | 164 | 165 | 21 | 42 | 26 |
| 111 | jubarte | jubarte-final@717311c03d4f | 73.4761 | 73.1343 | 73.4761 | 73.1343 | — | 0 | 207 | 207 | 25 | 47 | 26 |
| 112 | sanity-word | — | 68.1679 | 70.4845 | 68.1679 | 70.4845 | — | 0 | 230 | 230 | 0 | 0 | 38 |
| 113 | jubarte-rust | jubarte-rust@6233a48e4ac8 | 66.3055 | 64.1705 | 66.3055 | 64.1705 | — | 0 | 196 | 196 | 0 | 21 | 32 |
| 114 | jubarte | jubarte-final@b4f90acaa85e | 64.6926 | 63.481 | 64.6926 | 63.481 | — | 0 | 196 | 196 | 0 | 5 | 31 |
| 115 | jubarte-rust | jubarte-rust@b834d6e49fdb | 61.7832 | 59.2784 | 51.3368 | 55.9197 | — | 35 | 172 | 207 | 2 | 6 | 39 |
| 116 | ooxmlsdk | — | 55.1866 | 55.2398 | 55.1866 | 55.2398 | — | 0 | 232 | 232 | 0 | 0 | 52 |
| 117 | docxodus | 6.4.0 | 58.7425 | 55.0306 | 58.1749 | 54.9959 | — | 2 | 205 | 207 | 3 | 7 | 66 |
| 118 | folio | 0.3.1 | 55.3092 | 53.7539 | 54.7748 | 53.525 | — | 2 | 205 | 207 | 0 | 1 | 75 |
| 119 | superdoc | 1.19.2 | 57.1871 | 55.5996 | 50.2804 | 53.2474 | — | 25 | 182 | 207 | 2 | 4 | 52 |
| 120 | superdoc-redlines | 0.2.0 | 57.6297 | 55.8997 | 53.4536 | 53.1078 | — | 15 | 192 | 207 | 0 | 1 | 63 |
| 121 | redlines | 0.6.1 | 51.284 | 51.7682 | 49.5498 | 51.3171 | — | 7 | 200 | 207 | 0 | 0 | 84 |
| 122 | docx-redline-js | 0.3.0-ts-migration | 50.5319 | 50.2615 | 48.4264 | 50.09 | — | 7 | 161 | 168 | 0 | 0 | 73 |
| 123 | jubarte | jubarte-final@9991b783a190 | 48.9496 | 49.8858 | 48.9496 | 49.8858 | — | 0 | 164 | 164 | 0 | 0 | 84 |
| 124 | docxodus | 7.0.0 | 50.4935 | 49.6384 | 50.4935 | 49.6384 | — | 0 | 196 | 196 | 0 | 0 | 102 |
| 125 | docx-redline-js | — | 55.1236 | 55.1236 | 12.2497 | 0 | — | 7 | 2 | 9 | 0 | 0 | 1 |

### Common-subset ranking (script_redlines)

Paired comparison on the **139** documents every vendor below completed (best pin per vendor). Unlike the aggregate tables, these medians are computed on the SAME documents for every vendor.

| # | vendor | version | median | mean |
| --- | --- | --- | --- | --- |
| 1 | jubarte-rust | jubarte-rust@01ed1fac181e | 100.00 | 94.12 |
| 2 | jubarte-wasm | 0.1.0 | 100.00 | 94.12 |
| 3 | jubarte | jubarte-final@3995702f73ed | 91.84 | 90.35 |
| 4 | jubarte-ast | jubarte-final@d43557e042c1 | 91.36 | 89.39 |
| 5 | sanity-word | — | 73.95 | 71.90 |
| 6 | docxodus | 6.4.0 | 60.50 | 62.77 |
| 7 | superdoc-redlines | 0.2.0 | 58.50 | 59.70 |
| 8 | ooxmlsdk | — | 57.13 | 58.14 |
| 9 | superdoc | 1.19.2 | 56.92 | 57.99 |
| 10 | folio | 0.3.1 | 56.88 | 58.29 |
| 11 | redlines | 0.6.1 | 53.78 | 52.70 |
| 12 | docx-redline-js | 0.3.0-ts-migration | 50.33 | 51.18 |

### Paired comparisons (script_redlines)

Per-doc paired deltas on shared documents (best pin per vendor); `win/loss/tie` counts docs where the FIRST vendor scores higher/lower/equal. Wilcoxon signed-rank p, zsplit zero method.

| vendor A | vendor B | docs | win/loss/tie | median Δ | p |
| --- | --- | --- | --- | --- | --- |
| docx-redline-js | docxodus | 161 | 33/128/0 | -7.65 | 1.12e-19 |
| docx-redline-js | folio | 161 | 47/113/1 | -5.19 | 7.03e-14 |
| docx-redline-js | jubarte | 161 | 0/161/0 | -42.56 | 3.59e-28 |
| docx-redline-js | jubarte-ast | 152 | 2/150/0 | -41.16 | 1.22e-26 |
| docx-redline-js | jubarte-rust | 161 | 0/161/0 | -46.99 | 3.59e-28 |
| docx-redline-js | jubarte-wasm | 161 | 0/161/0 | -46.99 | 3.59e-28 |
| docx-redline-js | ooxmlsdk | 161 | 36/125/0 | -7.83 | 1.59e-12 |
| docx-redline-js | redlines | 160 | 56/104/0 | -2.45 | 7.25e-05 |
| docx-redline-js | sanity-word | 160 | 15/145/0 | -22.95 | 1.92e-24 |
| docx-redline-js | superdoc | 153 | 34/119/0 | -6.07 | 4.29e-15 |
| docx-redline-js | superdoc-redlines | 152 | 41/110/1 | -6.74 | 6.00e-15 |
| docxodus | folio | 203 | 118/84/1 | +0.77 | 1.13e-04 |
| docxodus | jubarte | 163 | 5/156/2 | -29.62 | 7.14e-28 |
| docxodus | jubarte-ast | 189 | 11/176/2 | -25.78 | 3.23e-31 |
| docxodus | jubarte-rust | 164 | 1/160/3 | -33.02 | 1.31e-28 |
| docxodus | jubarte-wasm | 164 | 1/160/3 | -33.02 | 1.31e-28 |
| docxodus | ooxmlsdk | 164 | 99/65/0 | +2.17 | 9.11e-04 |
| docxodus | redlines | 198 | 143/55/0 | +3.44 | 6.07e-16 |
| docxodus | sanity-word | 163 | 48/115/0 | -11.83 | 4.25e-09 |
| docxodus | superdoc | 182 | 104/73/5 | +0.61 | 2.43e-05 |
| docxodus | superdoc-redlines | 191 | 108/79/4 | +0.97 | 6.05e-03 |
| folio | jubarte | 163 | 1/162/0 | -32.57 | 1.95e-28 |
| folio | jubarte-ast | 190 | 5/184/1 | -29.92 | 2.13e-32 |
| folio | jubarte-rust | 164 | 1/163/0 | -35.63 | 1.36e-28 |
| folio | jubarte-wasm | 164 | 1/163/0 | -35.63 | 1.36e-28 |
| folio | ooxmlsdk | 164 | 86/78/0 | +0.76 | 5.70e-01 |
| folio | redlines | 198 | 131/67/0 | +2.78 | 1.97e-11 |
| folio | sanity-word | 163 | 25/138/0 | -14.34 | 1.40e-19 |
| folio | superdoc | 180 | 100/79/1 | +0.60 | 3.16e-01 |
| folio | superdoc-redlines | 190 | 75/110/5 | -0.56 | 2.26e-03 |
| jubarte | jubarte-ast | 154 | 22/6/126 | +0.00 | 2.47e-02 |
| jubarte | jubarte-rust | 163 | 43/76/44 | +0.00 | 6.90e-04 |
| jubarte | jubarte-wasm | 163 | 43/76/44 | +0.00 | 6.90e-04 |
| jubarte | ooxmlsdk | 163 | 163/0/0 | +33.15 | 1.69e-28 |
| jubarte | redlines | 162 | 162/0/0 | +39.42 | 2.46e-28 |
| jubarte | sanity-word | 162 | 155/7/0 | +18.71 | 3.30e-27 |
| jubarte | superdoc | 155 | 153/1/1 | +33.98 | 5.07e-27 |
| jubarte | superdoc-redlines | 154 | 153/1/0 | +29.84 | 6.16e-27 |
| jubarte-ast | jubarte-rust | 154 | 41/77/36 | -0.00 | 1.87e-04 |
| jubarte-ast | jubarte-wasm | 154 | 41/77/36 | -0.00 | 1.87e-04 |
| jubarte-ast | ooxmlsdk | 154 | 153/1/0 | +32.00 | 5.27e-27 |
| jubarte-ast | redlines | 187 | 184/3/0 | +37.12 | 2.60e-32 |
| jubarte-ast | sanity-word | 153 | 144/9/0 | +18.26 | 2.30e-25 |
| jubarte-ast | superdoc | 171 | 164/6/1 | +33.71 | 3.19e-29 |
| jubarte-ast | superdoc-redlines | 176 | 170/5/1 | +27.61 | 5.05e-30 |
| jubarte-rust | jubarte-wasm | 164 | 2/0/162 | +0.00 | 7.58e-01 |
| jubarte-rust | ooxmlsdk | 164 | 163/1/0 | +36.46 | 1.18e-28 |
| jubarte-rust | redlines | 162 | 162/0/0 | +42.14 | 2.46e-28 |
| jubarte-rust | sanity-word | 163 | 160/3/0 | +20.81 | 3.59e-28 |
| jubarte-rust | superdoc | 155 | 153/0/2 | +37.34 | 3.57e-27 |
| jubarte-rust | superdoc-redlines | 155 | 154/1/0 | +33.52 | 4.05e-27 |
| jubarte-wasm | ooxmlsdk | 164 | 163/1/0 | +36.46 | 1.18e-28 |
| jubarte-wasm | redlines | 162 | 162/0/0 | +42.14 | 2.46e-28 |
| jubarte-wasm | sanity-word | 163 | 160/3/0 | +20.81 | 3.59e-28 |
| jubarte-wasm | superdoc | 155 | 153/0/2 | +37.34 | 3.57e-27 |
| jubarte-wasm | superdoc-redlines | 155 | 154/1/0 | +33.52 | 4.05e-27 |
| ooxmlsdk | redlines | 162 | 112/50/0 | +4.11 | 1.56e-13 |
| ooxmlsdk | sanity-word | 230 | 15/215/0 | -14.02 | 3.48e-35 |
| ooxmlsdk | superdoc | 155 | 83/72/0 | +1.15 | 6.13e-01 |
| ooxmlsdk | superdoc-redlines | 155 | 74/81/0 | -0.50 | 9.07e-02 |
| redlines | sanity-word | 161 | 9/152/0 | -19.31 | 1.99e-27 |
| redlines | superdoc | 181 | 56/125/0 | -2.96 | 1.77e-10 |
| redlines | superdoc-redlines | 185 | 50/135/0 | -3.04 | 2.91e-14 |
| sanity-word | superdoc | 154 | 126/28/0 | +14.26 | 9.05e-18 |
| sanity-word | superdoc-redlines | 154 | 125/29/0 | +12.52 | 3.73e-16 |
| superdoc | superdoc-redlines | 175 | 80/95/0 | -0.89 | 3.34e-02 |

### Lens health (script_redlines)

Docs where the pixel lens and a judging lens (functional accept/reject invariant, WV-1 word-validate) conflict — the bench is measuring the wrong thing on those docs. A bench-health alarm, not a ranking signal.

- **jubarte** jubarte-final@d43557e042c1: 20 doc(s) where the lenses disagree (5.3% of two-lens docs)
- **jubarte-ast** jubarte-final@d43557e042c1: 36 doc(s) where the lenses disagree (9.8% of two-lens docs)
- **jubarte-rust** jubarte-rust@fcea02da49f4: 25 doc(s) where the lenses disagree (6.6% of two-lens docs)

### `accepted_changes`

`accepted_changes`

| # | vendor | version | mean | median | itt_mean | itt_median | skill_median | failures | n_docs | itt_n | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | jubarte-rust | jubarte-rust@653876af82d6 | 89.5841 | 99.8896 | 89.5841 | 99.8896 | — | 0 | 164 | 164 | 78 | 105 | 5 |
| 2 | jubarte-rust | jubarte-rust@e12c880586ec | 89.5838 | 99.8896 | 89.5838 | 99.8896 | — | 0 | 164 | 164 | 78 | 105 | 5 |
| 3 | jubarte-rust | jubarte-rust@07493ca50fd6 | 89.5096 | 99.8896 | 89.5096 | 99.8896 | — | 0 | 164 | 164 | 78 | 105 | 6 |
| 4 | jubarte-rust | jubarte-rust@f6cc3a6a7eb8 | 89.3128 | 99.8896 | 89.3128 | 99.8896 | — | 0 | 164 | 164 | 78 | 103 | 5 |
| 5 | jubarte-rust | jubarte-rust@cbbcefb724a7 | 89.4476 | 99.7477 | 89.4476 | 99.7477 | — | 0 | 164 | 164 | 76 | 103 | 5 |
| 6 | jubarte-rust | jubarte-rust@28c41564723b | 87.1054 | 95.3936 | 87.1054 | 95.3936 | — | 0 | 164 | 164 | 69 | 95 | 8 |
| 7 | jubarte-rust | jubarte-rust@9fcc4289e375 | 87.0018 | 95.3936 | 87.0018 | 95.3936 | — | 0 | 164 | 164 | 69 | 95 | 9 |
| 8 | jubarte | jubarte-final@dd16ad8fbcf3 | 86.534 | 94.4179 | 86.534 | 94.4179 | — | 0 | 164 | 164 | 63 | 87 | 7 |
| 9 | jubarte-rust | jubarte-rust@cdfef70a7156 | 84.2733 | 88.7405 | 84.2733 | 88.7405 | — | 0 | 164 | 164 | 54 | 80 | 7 |
| 10 | jubarte-rust | jubarte-rust@8e77f696f091 | 83.7563 | 87.9669 | 83.7563 | 87.9669 | — | 0 | 164 | 164 | 52 | 77 | 7 |
| 11 | jubarte | jubarte-final@717311c03d4f | 78.1534 | 80.639 | 78.1534 | 80.639 | — | 0 | 166 | 166 | 26 | 43 | 14 |
| 12 | docxodus | 6.4.0 | 68.9994 | 77.1882 | 68.9994 | 77.1882 | — | 0 | 164 | 164 | 14 | 22 | 43 |
| 13 | docxodus | 7.0.0 | 70.1963 | 74.9182 | 70.1963 | 74.9182 | — | 0 | 164 | 164 | 17 | 44 | 49 |
| 14 | superdoc | 1.19.2 | 63.818 | 61.1184 | 57.6669 | 55.8213 | — | 16 | 150 | 166 | 2 | 3 | 33 |
| 15 | folio | 0.3.1 | 57.9094 | 55.608 | 54.5813 | 53.9618 | — | 10 | 164 | 174 | 3 | 4 | 61 |
| 16 | jubarte-rust | jubarte-rust@b834d6e49fdb | 63.499 | 54.4541 | 53.6457 | 49.1664 | — | 27 | 147 | 174 | 13 | 15 | 72 |

### `roundtrip`

roundtrip (self-diff → pdf_source)

| # | vendor | version | mean | median | itt_mean | itt_median | skill_median | failures | n_docs | itt_n | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | jubarte-rust | jubarte-rust@cbbcefb724a7 | 99.1706 | 100 | 99.1706 | 100 | — | 0 | 166 | 166 | 157 | 161 | 1 |
| 2 | jubarte-rust | jubarte-rust@cdfef70a7156 | 99.1699 | 100 | 99.1699 | 100 | — | 0 | 166 | 166 | 157 | 161 | 1 |
| 3 | jubarte-rust | jubarte-rust@fc29f56fd31d | 99.1697 | 100 | 99.1697 | 100 | — | 0 | 166 | 166 | 157 | 161 | 1 |
| 4 | folio | 0.3.1 | 98.0712 | 100 | 98.0712 | 100 | — | 0 | 198 | 198 | 185 | 190 | 4 |
| 5 | jubarte | jubarte-final@dd16ad8fbcf3 | 97.6313 | 100 | 97.6313 | 100 | — | 0 | 166 | 166 | 152 | 156 | 3 |
| 6 | docxodus | 7.0.0 | 97.4281 | 100 | 97.4281 | 100 | — | 0 | 166 | 166 | 148 | 157 | 4 |
| 7 | jubarte | jubarte-final@717311c03d4f | 94.4868 | 100 | 94.4868 | 100 | — | 0 | 199 | 199 | 149 | 165 | 3 |
| 8 | docxodus | 6.4.0 | 92.2445 | 100 | 92.2445 | 100 | — | 0 | 198 | 198 | 144 | 161 | 13 |
| 9 | superdoc | 1.19.2 | 93.0017 | 100 | 91.5854 | 100 | — | 3 | 194 | 197 | 144 | 158 | 8 |
| 10 | jubarte-rust | jubarte-rust@b834d6e49fdb | 93.1152 | 100 | 82.9307 | 100 | — | 23 | 171 | 192 | 120 | 137 | 6 |

### `visual_rendering`

visual_rendering (Playwright viewer)

| # | vendor | version | mean | median | itt_mean | itt_median | skill_median | failures | n_docs | itt_n | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | superdoc | 1.44.1 | 58.7798 | 61.2486 | 58.7798 | 61.2486 | — | 0 | 199 | 199 | 0 | 0 | 38 |
| 2 | folio | 0.5.0 | 59.6494 | 55.0967 | 59.6494 | 55.0967 | — | 0 | 198 | 198 | 0 | 3 | 56 |
| 3 | docxodus | 6.4.0-local.1 | 56.5017 | 49.7216 | 53.9463 | 49.2363 | — | 9 | 190 | 199 | 0 | 0 | 97 |
| 4 | docxodus | 7.0.0 | 56.5017 | 49.7216 | 53.9463 | 49.2363 | — | 9 | 190 | 199 | 0 | 0 | 97 |

### `visual_redlines`

visual_redlines (Playwright)

| # | vendor | version | mean | median | itt_mean | itt_median | skill_median | failures | n_docs | itt_n | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | 6.4.0 | 60.9207 | 61.2232 | 48.5357 | 58.9198 | — | 37 | 145 | 182 | 0 | 0 | 13 |
| 2 | superdoc | 1.44.1 | 55.3334 | 56.4237 | 54.998 | 56.3376 | — | 1 | 164 | 165 | 0 | 0 | 44 |
| 3 | folio | 0.5.0 | 51.5494 | 51.6497 | 50.9283 | 51.4809 | — | 2 | 164 | 166 | 0 | 0 | 68 |
| 4 | docxodus | 7.0.0 | 48.2275 | 48.0758 | 47.6464 | 48.0337 | — | 2 | 164 | 166 | 0 | 0 | 122 |

### `visual_accepted_changes`

visual_accepted_changes (Playwright)

| # | vendor | version | mean | median | itt_mean | itt_median | skill_median | failures | n_docs | itt_n | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | 6.4.0 | 62.3235 | 62.7622 | 62.3235 | 62.7622 | — | 0 | 152 | 152 | 0 | 1 | 21 |
| 2 | superdoc | 1.44.1 | 59.3354 | 60.971 | 59.3354 | 60.971 | — | 0 | 165 | 165 | 0 | 0 | 35 |
| 3 | folio | 0.5.0 | 59.671 | 54.9489 | 59.671 | 54.9489 | — | 0 | 164 | 164 | 0 | 0 | 42 |

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
| docxodus | 7.0.0 | 2026-07-11T02:25:04.610761+00:00 | script_redlines | 50.4935 | 49.6384 | 196 |
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
| jubarte | jubarte-final@8b23cdc7eca8 | 2026-07-13T19:44:34.588429+00:00 | script_redlines | 83.4166 | 88.6547 | 164 |
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
| jubarte | jubarte-final@d43557e042c1 | 2026-08-03T20:00:06.750842+00:00 | script_redlines | 82.2668 | 86.051 | 383 |
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
| jubarte-ast | jubarte-final@d43557e042c1 | 2026-08-03T20:34:46.182209+00:00 | script_redlines | 75.0012 | 77.1365 | 375 |
| jubarte-rust | jubarte-rust@01ed1fac181e | 2026-07-16T23:14:23.444508+00:00 | script_redlines | 92.2148 | 99.9187 | 164 |
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
| jubarte-rust | jubarte-rust@9fcc4289e375 | 2026-07-16T06:01:55.601043+00:00 | script_redlines | 90.0375 | 95.6735 | 164 |
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
| jubarte-rust | jubarte-rust@fcea02da49f4 | 2026-08-03T20:18:45.667340+00:00 | script_redlines | 85.0239 | 93.3681 | 383 |
| jubarte-wasm | 0.1.0 | 2026-07-24T15:13:19.462654+00:00 | script_redlines | 92.2147 | 99.9187 | 164 |
| ooxmlsdk | — | 2026-07-13T17:24:50.712941+00:00 | script_redlines | 55.1866 | 55.2398 | 232 |
| redlines | 0.6.1 | 2026-07-12T07:38:29.295760+00:00 | script_redlines | 51.284 | 51.7682 | 200 |
| sanity-word | — | 2026-07-13T18:06:21.529826+00:00 | script_redlines | 68.1679 | 70.4845 | 230 |
| superdoc | 1.19.2 | 2026-07-09T15:38:31.872437+00:00 | accepted_changes | 63.818 | 61.1184 | 150 |
| superdoc | 1.19.2 | 2026-07-09T18:25:24.395459+00:00 | roundtrip | 93.0017 | 100 | 194 |
| superdoc | 1.19.2 | 2026-07-09T15:34:17.469383+00:00 | script_redlines | 57.1871 | 55.5996 | 182 |
| superdoc | 1.44.1 | 2026-07-09T18:25:37.273372+00:00 | visual_accepted_changes | 59.3354 | 60.971 | 165 |
| superdoc | 1.44.1 | 2026-07-09T18:22:07.033240+00:00 | visual_redlines | 55.3334 | 56.4237 | 164 |
| superdoc | 1.44.1 | 2026-07-09T18:16:46.431642+00:00 | visual_rendering | 58.7798 | 61.2486 | 199 |
| superdoc-redlines | 0.2.0 | 2026-07-12T08:32:43.871610+00:00 | script_redlines | 57.6297 | 55.8997 | 192 |

## Holdout gap

Sealed 20-pair holdout (`corpus/word_based/holdout.txt`) vs the visible corpus, per vendor: the latest holdout-only run (`bench run --holdout`) next to the latest COMPARABLE main run — same tool_version, `holdout_mode=excluded` (disjoint from the sealed set), full corpus (n > 100). `gap = holdout − main`; a strongly negative gap flags overfitting to the visible corpus.

_no holdout runs recorded yet (`bench run --holdout`)_

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

- Deduplication: one line per `(vendor, benchmark, tool_version)`. Re-runs of the **same** triple keep the best by `(render_fit, full_corpus_bucket, timestamp, overall_mean)` — prefer playwright for `visual_*` and soffice for script/accepted/roundtrip, then full-corpus lines (n > 100) over smokes, then the newest line (so a 383-doc post-holdout line supersedes a stale 403-doc one).
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

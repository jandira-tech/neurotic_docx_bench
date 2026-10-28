# Phase 3a — jubarte 0.14.0 DOCX→PDF

1,276 cases replaced; 3,917 cases retained byte-identical. 0 failures (Pixel ITT zero).

| Group | Replaced | Failures | Pixel | J | SSIM | TB |
|---|---:|---:|---:|---:|---:|---:|
| cases | 76 | 0 | 79.6980 (n=76) | 69.3342 (n=76) | 81.2724 (n=76) | 91.0682 (n=66) |
| corpus/clean | 597 | 0 | 81.9070 (n=597) | 70.6266 (n=597) | 85.3280 (n=597) | 88.6849 (n=589) |
| corpus/tracking_without_comments | 101 | 0 | 83.5457 (n=101) | 75.3535 (n=101) | 90.0535 (n=101) | 89.0297 (n=101) |
| corpus/with_comments_clean | 40 | 0 | 78.1169 (n=40) | 66.8025 (n=40) | 84.0850 (n=40) | 91.0450 (n=40) |
| corpus/with_comments_tracking | 62 | 0 | 74.7281 (n=62) | 62.2097 (n=62) | 81.2419 (n=62) | 82.5919 (n=62) |
| wordcraft1014/convert | 400 | 0 | 79.8820 (n=400) | 66.2057 (n=400) | 84.0312 (n=400) | 89.0343 (n=397) |

Assets: 7,885 files, 521,377,668 bytes (497.22 MiB).
Build data excluding report/manifest files: 540,424,791 bytes (515.39 MiB), including checkpoint records and full scorer results.

Bench main `3121c4988d72bf5cd93607c18cb50e3d713ce338`; scorer fingerprint `5e481477e2196f6b`, backend `numpy`, 144 DPI.
Pixel uses `pipeline.overall_from_result` (`overall_score_pagefair` when present), exactly as the bench DOCX→PDF command. Raw `overall_score` is also retained in each row's `pixel_result`.
J/SSIM/TB: upstream page-metrics a72d91bc at 150 DPI over all compatible common pages, multiplied by 100 and rounded to one decimal as site_1028. Upstream nulls remain null; means exclude only nulls, with denominators shown.
Shown pages are the current case's existing selection; cases without shown use first 3. Candidate pages beyond the reference selection are not shown; missing candidate pages retain null gaps.
Encoding: 180-DPI mutool PNG → 2/3 Lanczos resize → 16-colour median-cut → lossless WebP method 4; shown-page PDF via mutool clean -gggz.
Old Wordcraft lanes removed and marked dropped: {'jubarte-0.11.0': 400, 'jubarte-0.12.0': 400}.
All non-jubarte data, Word columns, case order, untouched rows, and all HTML outside DATA validated unchanged. Source index.html and redlines/index.html SHA256 unchanged. No temporary PNGs remain.
No Word invocation, upload, commit, external posting or live viewer write.

Final build directory: 541,578,046 bytes (516.49 MiB), including reports and the asset manifest.

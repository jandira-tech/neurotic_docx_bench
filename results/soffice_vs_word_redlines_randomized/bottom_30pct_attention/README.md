# Bottom 30% — soffice vs Word redline pairs to pay attention to
The **59 lowest-scoring pairs** (of 196) from the LibreOffice-vs-Microsoft-Word redline render comparison — the cases where LibreOffice's rendering of a Word tracked-change `.docx` diverges most from Word's own PDF export.
## Selection
- Ranked by `overall_score` (0.7·avg-page + 0.3·min-page), ascending.
- Bottom 30% = `ceil(0.30 × 196)` = **59 pairs**.
- Score range in this set: **41.09 – 61.55** (cutoff ≤ 61.55).
- Corpus mean is 66.2 / median 67.5, so everything here is below the median.

## What's in each subfolder
Every pair `<base>_<next>` appears as `<base>_<next>_redline.{docx,pdf}` in all three:
| Folder | Contents |
|---|---|
| `docx/` | Source Word redline `.docx` — the single input that generated **both** PDFs. |
| `pdf_word/` | Microsoft Word's PDF export (the **oracle** — ground truth pixels). |
| `pdf_soffice/` | LibreOffice 26.2.4.2 (`soffice --convert-to pdf`) render (the **candidate**). |
| `scores.csv` | These pairs ranked worst-first, with page counts. |

## Why these score low
- **39/59** are multi-page documents. Length is the dominant driver: soffice's line-breaking and pagination diverge from Word, pushing ink onto different pages so the page-aligned pixel comparison collapses.
- **6/59** have an outright page-count mismatch (soffice under-paginating vs Word) — e.g. `file_154_file_155` collapses Word's 4 pages into 1.
- To review a pair, open `pdf_word/<stem>.pdf` and `pdf_soffice/<stem>.pdf` side by side; `docx/<stem>.docx` is the shared source if you need to inspect the underlying markup.

## Ranked list
| # | pair | score | pages W→L | mismatch |
|---:|---|---:|:--:|:--:|
| 1 | `file_154_file_155` | 41.1 | 4→1 | ⚠️ |
| 2 | `file_195_file_196` | 41.6 | 14→13 | ⚠️ |
| 3 | `file_8_file_9` | 41.8 | 12→12 |  |
| 4 | `file_114_file_115` | 42.0 | 14→13 | ⚠️ |
| 5 | `file_99_file_100` | 42.0 | 14→13 | ⚠️ |
| 6 | `file_184_file_185` | 42.0 | 14→13 | ⚠️ |
| 7 | `file_73_file_74` | 42.1 | 11→11 |  |
| 8 | `file_26_file_27` | 42.1 | 11→11 |  |
| 9 | `file_5_file_6` | 42.1 | 11→11 |  |
| 10 | `file_52_file_53` | 42.6 | 11→11 |  |
| 11 | `file_15_file_16` | 44.1 | 11→11 |  |
| 12 | `file_170_file_171` | 44.1 | 4→4 |  |
| 13 | `file_130_file_131` | 44.8 | 9→9 |  |
| 14 | `file_7_file_8` | 44.8 | 9→9 |  |
| 15 | `file_133_file_134` | 46.1 | 2→2 |  |
| 16 | `file_174_file_175` | 46.1 | 5→5 |  |
| 17 | `file_169_file_170` | 46.1 | 4→4 |  |
| 18 | `file_69_file_70` | 46.3 | 3→3 |  |
| 19 | `file_27_file_28` | 46.7 | 13→12 | ⚠️ |
| 20 | `file_176_file_177` | 46.8 | 7→7 |  |
| 21 | `file_175_file_176` | 47.1 | 7→7 |  |
| 22 | `file_77_file_78` | 47.6 | 3→3 |  |
| 23 | `file_82_file_83` | 48.3 | 1→1 |  |
| 24 | `file_53_file_54` | 48.5 | 11→11 |  |
| 25 | `file_74_file_75` | 48.5 | 11→11 |  |
| 26 | `file_143_file_144` | 48.6 | 3→3 |  |
| 27 | `file_78_file_79` | 48.6 | 3→3 |  |
| 28 | `file_6_file_7` | 48.7 | 11→11 |  |
| 29 | `file_188_file_189` | 48.8 | 3→3 |  |
| 30 | `file_9_file_10` | 49.3 | 11→11 |  |
| 31 | `file_146_file_147` | 49.4 | 6→6 |  |
| 32 | `file_16_file_17` | 49.5 | 11→11 |  |
| 33 | `file_197_file_198` | 49.9 | 1→1 |  |
| 34 | `file_14_file_15` | 51.1 | 3→3 |  |
| 35 | `file_83_file_84` | 51.1 | 1→1 |  |
| 36 | `file_131_file_132` | 52.6 | 9→9 |  |
| 37 | `file_58_file_59` | 52.8 | 1→1 |  |
| 38 | `file_198_file_199` | 52.9 | 1→1 |  |
| 39 | `file_46_file_47` | 53.1 | 1→1 |  |
| 40 | `file_19_file_20` | 53.8 | 5→5 |  |
| 41 | `file_28_file_29` | 55.7 | 1→1 |  |
| 42 | `file_164_file_165` | 55.8 | 1→1 |  |
| 43 | `file_141_file_142` | 56.5 | 1→1 |  |
| 44 | `file_163_file_164` | 57.0 | 1→1 |  |
| 45 | `file_139_file_140` | 58.3 | 1→1 |  |
| 46 | `file_140_file_141` | 58.5 | 1→1 |  |
| 47 | `file_94_file_95` | 58.6 | 1→1 |  |
| 48 | `file_100_file_101` | 58.6 | 13→13 |  |
| 49 | `file_3_file_4` | 58.7 | 1→1 |  |
| 50 | `file_112_file_113` | 58.9 | 1→1 |  |
| 51 | `file_59_file_60` | 59.1 | 1→1 |  |
| 52 | `file_196_file_197` | 59.3 | 14→14 |  |
| 53 | `file_95_file_96` | 60.4 | 1→1 |  |
| 54 | `file_18_file_19` | 60.8 | 6→6 |  |
| 55 | `file_55_file_56` | 61.1 | 1→1 |  |
| 56 | `file_30_file_31` | 61.1 | 1→1 |  |
| 57 | `file_120_file_121` | 61.4 | 1→1 |  |
| 58 | `file_115_file_116` | 61.5 | 13→13 |  |
| 59 | `file_41_file_42` | 61.5 | 2→2 |  |

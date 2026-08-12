# Score ladder — jubarte-rust → 90 / 90 / 200+

## Protocol (binding)

1. Full 763-doc ITT every ~2h; record mean / median / exact_100 / ≥90 / <50 / skill_median / page_median.
2. One marginal peel at a time; validate on ~30 fixtures that had the bug.
3. C1 ratchets: R-perfect, R-92, R-fail, R-tail (check noise floor).
4. Delete `runs/` after each official (`--clean-runs`); prune probe/A-B arms regularly.
5. Fidelity before speed; native ≡ wasm before publishing.

## Envelope honesty

Best-of-all-engines envelope on this corpus (2026-08-04): **mean 87.45 / median 97.69 / perfect 309**.
**Mean 90 is above that envelope** — pure sibling transfer cannot reach it; needs new capability or scorer-aware layout fidelity beyond current best-of-all.

## Baseline (restored 2026-08-06)

| pin | mean | median | exact_100 | n | note |
|---|---:|---:|---:|---:|---|
| best known `97da13@ebf1a79` | 79.581 | 84.889 | 182 | 763 | junction+M-CARRIER stack |
| regressed `b9d474` (audit WIP) | 78.074 | 81.133 | 163 | 763 | −19 perfects |
| **restored** `e0fe28e5@2351844` | **79.464** | **84.886** | **178** | 763 | within noise of best |

Audit (`fe39395`) dumped many pure-I/D peels; hard exhibit: `bold_underline_highlight×book_catalog` MIX → pure-I/D (100→47.95). Reverted.

## Arithmetic from best pin

- Median 90 needs **+38** docs crossing 90 (now 344 ≥90; need 382).
- Mean 90 needs **+10.4** pts/doc (~7950 total score-points).
- Perfects: 182 → 200 needs **+18** net (98 near-misses in [95,100)).
- Cluster [40,60): n=149 mean≈51; lift-to-92 would add ~+8 mean and buy the median.

## Next peels (ordered)

1. Confirm restored full-bench scores ≈ 79.6 / 84.9 / 182.
2. Layout-drift in ≈50 cluster (style effective spacing already partially shipped; numbering/list markers next).
3. Near-miss closure for perfects (+18 of 98).
4. Sibling transfer from lossless/docxodus only where mechanism is portable.

## Log

| when (UTC) | pin | mean | median | p100 | ≥90 | <50 | skill_med | page_med | notes |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 2026-08-05T23:21 | 97da13@ebf1a79 | 79.581 | 84.889 | 182 | 344 | 72 | 89.64 | 74.61 | best known |
| 2026-08-06T10:22 | b9d474@ebf1a79-tag | 78.074 | 81.133 | 163 | 329 | 85 | 88.06 | 74.64 | audit regression |
| 2026-08-06T12:27 | e0fe28e5@2351844 (restored ebf1a79) | 79.464 | 84.886 | 178 | 343 | 71 | 89.01 | 74.59 | restored; runs cleaned |

## Peels since restore

| peel | commit | expected | status |
|---|---|---|---|
| Revert audit pure-I/D dump | 2351844 | restore ~79.5/84.9/178 | **landed** full bench |
| numPr ilvl before numId | 236c5ed | validity-only, score-neutral | installed |
| M308 list wholesale pure-I/D fold skip | 059808d | broken_list×multiple_nodes ~52→Word pure-I/D; list family | **REGRESSION** 79.22/84.22/177 |
| M308b restore empty-del M131 + keep LCS list gates | e16ae37 | fix file_197/file_2/bullet; keep broken_list +28 | subset XML; full ITT aborted (failed mid-score; cadence) |
| M308c short-item list pure-I/D only | 262d73b | Word XML: long numbered prose MIX; short lists pure-I/D | XML OK on 6/8 keys; basic_list×sd_1707 still MIX vs Word pure-I/D |


## Focus (2026-08-06)

**For now: jubarte-redlines (rust) + wasm only.** TS family after rust+wasm clear 90/90/200.

## Three-engine gate (binding, later)

Goal incomplete unless **all three** clear mean≥90, median≥90, perfects>200:

| engine | bench run / vendor | source |
|---|---|---|
| jubarte-redlines (rust) | `jubarte-rust` (+ wasm every ~4h must match) | `~/T/jubarte-redlines` |
| jubarte-first-lossless | `jubarte-final-lossless` / vendor `jubarte` | `~/T/jubarte-first` dist |
| jubarte-first-via-ast | `jubarte-final-native` / vendor `jubarte-ast` | `~/T/jubarte-first` dist |

Cadence: rust full ITT ~2h; wasm-only ~4h; lossless+ast deferred until rust+wasm clear.

| when (UTC) | pin | mean | median | p100 | notes |
|---|---|---:|---:|---:|---|
| 2026-08-06T12:57 | 66c3c793@059808d M308 | 79.219 | 84.222 | 177 | **REGRESSION** vs restored −0.24/−0.67/−1 |
| 2026-08-06T14:49 | bea5f183@f6959f8 M309 | 79.540 | 84.886 | 178 | 344 | 71 | 89.01 | 74.61 | M309 short-next pure-I/D; ~restored; gates FAIL mean/med/p100 |
| 2026-08-06T14:19 | e16ae37 M308b subset30 | — | — | — | file_197/2/54/bullet restored; broken_list +27.8 kept; residual list LCS −22/−18; full ITT running |

| 2026-08-06 peel | f85de35 M311 | — | — | — | M311 M85a cap; image×rtl still drops pure-I earlier |
| 2026-08-06 peel | 97b2a6c M310 | subset ooxml sumΔ+15 vs m309 | unit OK |
| 2026-08-06 subset | e3bc6b6 M311 bottom7 | sumΔ +79 vs f6959f8 | image×rtl 15→59; rtl_mixed 29→51; ooxml +6–9 |

| 2026-08-06T16:49 | 9ba60702@e3bc6b6 M311 | 79.642 | 84.886 | 178 | 344 | 70 | 89.01 | 74.61 | speed_med 19.04; image×rtl +28.6; gates FAIL still +10.4 mean to 90 |

| 2026-08-06 peel | HEAD M312 | subset15 sumΔ+39.8 vs e3bc6b6 | two_column×nested 33.8→80.8 (+47); Word XML seq OK; unit green |

| 2026-08-06 peel | e5ed9bd M312/M313 | subset15 sumΔ+50.5 vs e3bc6b6 | two_column 33.8→80.8; broken_list +6.9; hyperlink×rtl +3.6; Word XML seq OK; full after 19:27Z |

| 2026-08-06 peel | 5394f06 M314–M316 | unit+XML | comment×list, hummingbird, support_tickets Word seq OK; staged for 19:27 full |

| 2026-08-06 peel | fe74aa4 M312–M317 | unit+XML | short-base pure-I/D + fold skips; binary ready for 19:27 full |

| 2026-08-06T19:27 | @eb5b8fe M312-318 | 78.871 | 82.303 | 166 | 329 | 69 | 88.94 | 74.61 | full pin peels M312-318 |

| 2026-08-06T19:27 | 38a1d9d3@eb5b8fe M312-318 | 78.871 | 82.303 | 166 | 329 | 69 | 88.94 | 74.61 | **REGRESSION** mean−0.77 med−2.58 p100−12; stamp perfects collapsed from finalize M314/6/7 |
| 2026-08-06 peel | 05f9270 revert finalize | subset stamp restored 100 | kept LCS M312/M315/M318; two_column +47; next full ≥21:45Z |

| 2026-08-06T21:45 | @0ab0e1c | 79.329 | 82.993 | 171 | 334 | 63 | 84.58 | 74.64 | full pin M312/M315/M318 only |
| 2026-08-07T02:05 | jubarte-rust@8dea7e733d6d+git.ec66729 | 79.942 | 84.541 | 178 | 343 | 57 | 88.4951 | 76.047 | full-ec66729 M349-353 |

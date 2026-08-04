# Stage L1 partition — jubarte-final-lossless

Run `019fcc6f-4eb8-72f7-957e-799895a04342` · scorer field `overall_score_pagefair` · band [40, 60) · generated 2026-08-04 20:43 UTC.

## Buckets (raw counts, before interpretation)

| bucket | n | % of judged | meaning |
|---|---:|---:|---|
| `both_hold` | 124 | 76.5% | accept→next and reject→base both hold at text level (functionally valid redline; says nothing about how it renders) |
| `reject_only` | 3 | 1.9% | reject→base holds, accept→next fails |
| `accept_only` | 29 | 17.9% | accept→next holds, reject→base fails |
| `neither` | 6 | 3.7% | neither invariant holds |
| **judged total** | **162** | 100% | |
| *unjudged (excluded, contract C5)* | *4* | — | *error: ValueError: no `tc` element at grid_offset=5: 2, error: ValueError: no `tc` element at grid_offset=0: 1, blind: 1* |
| *cluster size* | *166* | — | *median 51.52* |

The `meaning` column states what the lens **establishes**, not what the plan
infers from it. The lens compares text only; see the L1 review for what that
does and does not license.

## Gate

**STOP_FIX_SCORER** — 124 of 162 judged documents (76.5%) have BOTH invariants holding, above the 15% threshold: the markup is correct and the scorer disagrees. Fix the scorer before lifting the cluster — a mean built on a scorer that under-credits correct markup optimises the engine against our own bug.

## Regeneration control

- engine build: recorded `jubarte-final@d43557e042c1`, now `jubarte-final@d43557e042c1` — **identical**
- candidates regenerated: 166 of 166 cluster documents
- fresh verdicts vs. recorded: 46/46 agree (100.0%); 120 documents had no recorded verdict to compare against

## Cross-tabulation — top fixture tokens per bucket

`n` is documents of that token in the bucket; `conc.` is the share of that token's judged documents landing there. Tokens are not disjoint.

### `both_hold` (n=124)

| token | n | of token's judged docs | conc. |
|---|---:|---:|---:|
| `list` | 26 | 28 | 93% |
| `table` | 22 | 29 | 76% |
| `math` | 19 | 20 | 95% |
| `demo` | 16 | 22 | 73% |
| `ooxml` | 15 | 17 | 88% |
| `diff` | 13 | 15 | 87% |
| `word` | 13 | 17 | 76% |
| `combos` | 12 | 13 | 92% |

### `reject_only` (n=3)

_no token reaches the minimum population._

### `accept_only` (n=29)

| token | n | of token's judged docs | conc. |
|---|---:|---:|---:|
| `styles` | 6 | 8 | 75% |
| `demo` | 6 | 22 | 27% |
| `table` | 6 | 29 | 21% |
| `localized` | 5 | 5 | 100% |
| `heading` | 5 | 8 | 62% |
| `hyperlink` | 4 | 5 | 80% |
| `overflow` | 4 | 15 | 27% |
| `paraid` | 4 | 15 | 27% |

### `neither` (n=6)

_no token reaches the minimum population._

## Generation

`present` counts candidates on disk for the requested pairs; `new` counts the
ones this invocation created. They differ on a re-run, because the generator
skips pairs whose output already exists.

| corpus | requested | present | new | rc |
|---|---:|---:|---:|---:|
| `word_based` | 34 | 34 | 34 | 0 |
| `word_based_randomized` | 12 | 12 | 12 | 0 |
| `word_redlines_superdoc` | 120 | 120 | 120 | 0 |


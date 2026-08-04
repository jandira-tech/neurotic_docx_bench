# Plan 3 — jubarte-first-via-ast → mean > 81, median > 92, perfect > 200

Evidence base: [docxodus-version-diff.md](docxodus-version-diff.md). Numbers from run
`019fcc7c-8d62-76ca-9532-1b2649691eb4` on the 763-document ITT corpus, scorer
`pagefair-v2`.

| | now | target | gap |
|---|---:|---:|---:|
| ITT mean | 69.83 | > 81 | **+11.17** |
| ITT median | 68.30 | > 92 | **+23.70** |
| perfect (score 100) | 84 | > 200 | **+116** |
| failures | **9** | 0 | **−9** |

**Arthur, I think the perfect-fixtures target is wrong for this engine, and you should
hear why before the work starts.**

The other two plans reach 200 perfect by converting near-misses. ast cannot: it has
**94 documents** in [90,100) and needs **+116**. Even converting *every single
near-miss to exact* leaves it at 178, short of the target. Clearing 200 requires
reaching down into the [80,90) band (101 documents) and converting a large fraction of
that too — documents that are not one defect away from exact, they are several.

So ast's perfect-count target is not "the same work, more of it." It is a different and
much larger project than Plans 1 and 2. My recommendation is to set ast's target at
**mean > 81 and median > 90** for this pass, treat 200 perfect as a later milestone,
and spend the freed effort on rust — which needs only a 28% near-miss conversion and is
the engine most likely to clear all three. Your call; if you want 200 on ast, Stage A4
below is what it takes and I will not pretend it is cheap.

Everything below assumes the full target unless you say otherwise.

## Diagnosis — behind on both sub-metrics

| | skill_median | page_median |
|---|---:|---:|
| jubarte-ast | 74.89 | **52.06** |
| jubarte-rust | 86.19 | 65.99 |
| jubarte-lossless | 53.07 | 83.30 |
| docxodus 9.0.0 | 100.00 | 76.38 |

ast is not the mirror of anything — it is mid-table on change-region skill (74.89,
between lossless and rust) and **worst in the benchmark on page geometry** (52.06,
31 points below lossless). Its distribution reflects that: 255 documents in [40,60),
the largest ≈50 cluster of any engine, and only 84 exact matches.

It is also the only jubarte engine with failures: **9 documents** produce nothing.

## Stage A0 — the 9 failures

Do this first, before any scoring work. Nine failures cost 9 × (whatever they would
have scored) in ITT, but more importantly a failure is an unknown: it might be an
engine defect, and it might be ours. This audit has already found five separate
mechanisms by which our own infrastructure recorded a vendor failure that never
happened, and one of them (D4b, an orphaned generator) was found in this very sweep.

Classify each of the 9 as engine-side or harness-side before assuming either.

## Stage A1 — harvest from both siblings

ast is behind rust and lossless on documents where **one of them already scores 100**:

- 40 documents where lossless ≥ 95 and ast ≤ 60.
- 37 where rust ≥ 95 and ast ≤ 60.
- Only 7 and 10 respectively in the reverse direction.

That is 77 documents where a sibling in the same family already has the answer. This is
the single highest-yield stage in any of the three plans, and it is transfer rather than
invention.

Priority within it: **page geometry**, because ast's page_median of 52.06 is the largest
single deficit anywhere in the family and lossless is 31 points better on the same
metric and the same corpus.

## Stage A2 — the ≈50 cluster (mean lever)

- **Target:** 255 documents at ≈50.7 → 90+. The largest cluster of the three engines.
- **Arithmetic:** lever A alone takes ast to **mean 83.00, median 90.00**. Mean target
  cleared with 2.0 points of headroom — the thinnest margin of the three, so ast has
  the least room for lever A to under-deliver.
- Perfect count unmoved (84 → 84).

Run the Plan 1 Stage L1 lens partition on ast's own 255 documents first. Given ast's
page_median of 52.06, expect its ≈50 cluster to be dominated by "rendered wrong" rather
than "not marked" — the opposite of what I expect for lossless.

## Stage A3 — style-chain resolution (shared workstream S)

Shared with Plans 1 and 2; mechanism and docxodus evidence in Plan 1 Stage L3.

ast's weakest token is `styles` at **49.1** — the lowest feature-token mean of any
engine on any token in the benchmark. Also `combos` 54.2, `rstyle` 54.2, `linked` 56.3,
`ooxml` 57.1, plus `page` 53.9 which is ast-specific and points back at Stage A1.

Sized on ast's scores, lever B is worth +2.03 mean and +3.41 median — proportionally the
weakest of the three, because ast's problems are broader than the style family.

## Stage A4 — near-miss closure, and the [80,90) band

Only attempt after A0–A3 have landed and re-run.

- **Pool:** 94 documents in [90,100) — converting all of them reaches 178, still short.
- **Second pool:** 101 documents in [80,90), which must supply the remaining 22+.
- Combined required conversion to clear 200: roughly **60% of everything above 80**.

This is the stage my recommendation above is about. It is a large, open-ended project
with no evidence yet that a 60% conversion rate across two bands is reachable.

## Verification

- Red-first per stage.
- Full 763-document ITT re-run per stage; `corpus_revision` recorded.
- `skill_median` and `page_median` reported per stage — for ast, `page_median` is the
  headline sub-metric and Stage A1 is judged on it.
- Failure count must reach 0 and stay there; a stage that raises the mean while
  reintroducing failures has not worked.
- Sealed 40-pair holdout once, at the end.

## Deferred (noted, not implemented in this pass)

- Per-fixture chasing worth ≈5 points on a single document.
- `issue` (n=10, mean 52.5) and `rtl` (n=10, mean 57.3).
- `math` (n=28, mean 56.5) as dedicated feature work.
- **The 200-perfect target itself**, pending your decision on the recommendation above.

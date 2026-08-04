# Plan 2 — jubarte-rust (and jubarte-wasm) → mean > 81, median > 92, perfect > 200

Evidence base: [docxodus-version-diff.md](docxodus-version-diff.md). Numbers from run
`019fcc5d-34e6-7029-95d9-463d5513fe7c` on the 763-document ITT corpus, scorer
`pagefair-v2`.

**Scope note:** `jubarte-rust` and `jubarte-wasm` score identically (76.21 / 77.95 /
158 on both rows) — same engine, two bindings. This plan covers both; any fix lands
once. If at any point the two rows diverge, that divergence is itself a bug and takes
priority over everything below.

| | now | target | gap |
|---|---:|---:|---:|
| ITT mean | 76.21 | > 81 | **+4.79** |
| ITT median | 77.95 | > 92 | **+14.05** |
| perfect (score 100) | 158 | > 200 | **+42** |
| *(failures)* | *0* | — | *already clean* |

Of the three engines this one is **closest to the perfect-count target** — 42 away
versus lossless's 58 and ast's 116 — and it has the largest near-miss pool to convert
from. It is the most likely of the three to hit all three targets.

## Diagnosis — the inverse of lossless

| | skill_median | page_median |
|---|---:|---:|
| jubarte-rust | **86.19** | **65.99** |
| jubarte-lossless | 53.07 | 83.30 |
| docxodus 9.0.0 | 100.00 | 76.38 |

rust marks the change well — 86.19 skill against lossless's 53.07 — and then loses it
on page geometry, 65.99 against lossless's 83.30. **It is the mirror image of Plan 1.**
Where lossless preserves the document and under-marks the edit, rust marks the edit and
disturbs the document.

That mirror relationship is the most useful fact in this whole exercise, and it is what
Stage R1 is for.

Supporting shape: 197 documents in [40,60) with cluster median 50.6, and 149 in
[90,100) — the largest near-miss pool of the three engines.

## Stage R1 — harvest from lossless before writing anything new

Two engines in the same family, with complementary and *legible* strengths, scored on
the same 763 documents. The transfer opportunity is measurable, not speculative:

- **19 documents** where lossless ≥ 95 and rust ≤ 60.
- **13** the other way.
- The envelope of just these two engines is **mean 82.63, median 90.78, perfect 210** —
  which already clears the mean and perfect targets without a single engine change.

Work:

1. Take the 19 documents where lossless wins outright. Establish what lossless does to
   preserve page geometry that rust does not. Given the +17.3 page_median gap between
   them, expect a small number of shared mechanisms, not 19 separate causes.
2. Port those mechanisms into rust. This is transfer inside one codebase family, which
   is far cheaper than the equivalent capability built from scratch.
3. Re-run and confirm rust's `page_median` moved. **`page_median` is the metric that
   proves this stage worked** — mean can rise for unrelated reasons.

**Guard:** rust's skill_median (86.19) must not fall while page_median rises. Trading
one sub-metric for the other nets nothing, and the two sub-metrics are recorded per run
precisely so this is checkable rather than assumed.

## Stage R2 — the ≈50 cluster (mean lever)

Same lever as Plan 1 Stage L2, and rust's cluster is the middle-sized one.

- **Target:** 197 documents at ≈50.6 → 90+.
- **Arithmetic:** lever A alone takes rust to **mean 86.36, median 90.00**. Mean target
  cleared with 5.4 points of headroom — the largest of the three engines.
- Perfect count unmoved (158 → 158).

Run the same Stage L1 lens partition first, on rust's own 197 documents. Do not assume
the cluster has the same composition as lossless's: rust's skill/page profile is
inverted, so a ≈50 score is more likely to mean "marked correctly, rendered wrong"
here and "rendered correctly, not marked" there. Different cause, different fix, same
number.

## Stage R3 — style-chain resolution (shared workstream S)

Shared with Plans 1 and 3 — implement once, see Plan 1 Stage L3 for the mechanism and
the docxodus evidence.

rust's weakest tokens: `rtl` 50.2, `simple` 51.6, `styles` 55.9, `math` 58.4,
`combos` 60.4, `rstyle` 60.4, `tab` 60.0.

Sized on rust's scores: lever B is worth +1.86 mean and **+5.51 median** — the largest
median contribution of the feature-family fixes on any of the three engines.

## Stage R4 — near-miss closure (median and perfect levers)

- **Pool:** 149 documents in [90,100) — the largest of the three.
- **Required conversion:** 42 of 149 = **28%**, the most achievable rate in the family
  (lossless needs 43%, ast needs more than its entire pool).
- Median > 92 comes from the same population moving up.

Because rust has both the biggest pool and the smallest required rate, **this is the
engine to attempt the perfect-count target on first.** If 28% proves out of reach here,
43% is not going to happen on lossless and the target itself should be re-examined
before more effort goes into it.

Method as Plan 1 Stage L4: classify the largest residual ink region per near-miss,
group by cause, fix by group.

## Verification

- Red-first per stage; failing fixture test must fail for the right reason.
- Full 763-document ITT re-run per stage; `corpus_revision` recorded.
- **Both `jubarte-rust` and `jubarte-wasm` re-run every time.** They score identically
  today; if a change moves one and not the other, the binding is lossy and that is a
  bug the benchmark would otherwise hide.
- `skill_median` and `page_median` reported per stage, not just the headline — R1 is
  meaningless without them.
- Sealed 40-pair holdout once, at the end.

## Deferred (noted, not implemented in this pass)

- Per-fixture chasing worth ≈5 points on a single document.
- `rtl` (n=10, mean 50.2) — rust's single worst token, but ten documents.
- `math` (n=28, mean 58.4) as dedicated feature work.
- Investigating why `simple` (n=10) scores 51.6 when the name suggests it should be
  easy; likely a mislabelled fixture family rather than an engine defect, and worth one
  look before it is used as evidence for anything.

# Plan 1 — jubarte-final-lossless → mean > 81, median > 92, perfect > 200

Evidence base: [docxodus-version-diff.md](docxodus-version-diff.md). Every number
below is from run `019fcc6f-4eb8-72f7-957e-799895a04342` on the 763-document ITT
corpus, scorer `pagefair-v2`.

| | now | target | gap |
|---|---:|---:|---:|
| ITT mean | 77.02 | > 81 | **+3.98** |
| ITT median | 78.53 | > 92 | **+13.47** |
| perfect (score 100) | 142 | > 200 | **+58** |
| *(failures)* | *0* | — | *already clean* |

Of the three engines this is the closest to the mean target and the furthest from the
perfect-count target. That asymmetry drives the whole plan.

## Diagnosis

| | skill_median | page_median |
|---|---:|---:|
| jubarte-lossless | **53.07** | **83.30** |
| docxodus 9.0.0 | 100.00 | 76.38 |

Lossless has **the best page-geometry fidelity of any engine in the benchmark,
docxodus included**, and earns roughly half the available change-region credit on the
median document. It renders the document faithfully and then under-marks the edit.

That is a good position to be in: the hard half (not damaging the document) is done.
The deficit is in the redline itself.

Supporting shape: 166 documents sit in [40,60) with a cluster median of 51.5 — the
signature of "document preserved, change not marked" — and 135 sit in [90,100), i.e.
one visible defect away from exact.

## Stage L1 — characterise the ≈50 cluster before touching the engine

**This stage produces no code change and it is not optional.** Lever A in the sizing
table is worth +8.4 mean on its own; committing to a fix before knowing what the
cluster *is* risks buying none of it.

1. Take the 166 documents in [40,60). Run them through the existing functional lens
   (`functional_lens.py`): `accept(candidate) == next` and `reject(candidate) == base`.
2. Partition into four buckets:
   - **both invariants hold** → the markup is correct and the *scorer* disagrees. This
     would be a benchmark defect, not an engine defect, and it changes what we publish.
   - **reject holds, accept fails** → deletions marked, insertions missing (or inert).
   - **accept holds, reject fails** → insertions marked, deletions dropped rather than
     struck.
   - **neither holds** → no usable redline; the output is paint.
3. Cross-tabulate against the fixture-name token census.

**Gate:** if bucket 1 exceeds ~15% of the cluster, stop and fix the scorer first. A
mean built on a scorer that under-credits correct markup is not worth having, and we
would be optimising the engine against our own bug — the D3 disease this audit exists
to remove.

Expected cost: one lens pass over 166 documents, no engine work.

## Stage L2 — the ≈50 cluster (mean **and median** lever)

Whatever L1 finds, this is the stage that buys **both** the mean and the median target.

- **Target:** 166 documents at ≈51 → **above 92**. The threshold is load-bearing, see below.
- **Arithmetic**, lifting the cluster to each landing point:

  | cluster lifted to | mean | median | perfect |
  |---:|---:|---:|---:|
  | 90 | 85.43 | 90.00 | 142 |
  | **93** | **86.09** | **93.00** | 142 |
  | 95 | 86.52 | 94.69 | 142 |

- **Land the cluster above 92 or the median target is missed.** Lifting to exactly 90
  produces a median of exactly 90.00 — 166 documents piled on one value drag the median
  onto it. Three points higher clears the target. This is a property of where the mass
  lands, not of how hard the fix is.
- **Does not move the perfect count at all** (142 → 142 at every landing point below
  100). That is Stage L4's job, and only Stage L4's.

> **Correction, 2026-08-04.** The first version of this plan assigned the median target
> to Stage L4 (near-miss closure) and described this stage as the "mean lever" only.
> That was wrong — see the box in Stage L4.

Sub-work, ordered by the L1 partition — do only the buckets L1 actually populates.

## Stage L3 — style-chain resolution (shared workstream S)

Lossless's weakest fixture tokens are `rtl` 55.2, `math` 57.6, `combos` 59.4,
`rstyle` 59.4, `styles` 59.5, `ooxml` 60.1, `linked` 61.6 — the
`ooxml_rfonts_rstyle_linked_combos` family, i.e. **style inheritance resolution**.

This is the same area docxodus put 53 new symbols into in 8.0.0, the release that moved
its numbers. Their approach, from the symbol names:

- resolve the effective formatting through the full style chain on **both** sides
  before diffing (`ResolveEffectiveStyleFormatting`, `ResolvesLeftParagraphStyleChain`);
- project docDefaults explicitly rather than leaving them implicit
  (`ApplyDocDefaultsStyleProjection`);
- normalise inserted runs into the target document's style vocabulary
  (`NormalizeInsertedStyleRunProperties`, `NormalizeInsertedParagraphStyle`);
- **drop** style references that cannot be resolved instead of emitting them
  (`DropDanglingParagraphStyleRefs`, `DropUnresolvableStyleRef`).

Sized on our data: lever B is worth +1.88 mean and **+3.47 median** on lossless — the
largest median contribution of any single feature-family fix we can size. Shared with
Plans 2 and 3; implement once, in whatever layer all three engines can consume.

## Stage L4 — near-miss closure (**perfect-count lever only**)

The one stage that reaches the perfect-count target, and the hardest.

- **Pool:** 135 documents in [90,100).
- **Required conversion:** 58 of 135 = **43%** to reach 201 perfect.

> **Correction, 2026-08-04 — this stage does NOT buy the median.**
>
> The first version of this plan claimed "median > 92 falls out of the same work." It
> does not, and the arithmetic is not close. The median of 763 documents is the 382nd
> value, so median > 92 requires **382 documents scoring above 92**. lossless has
> **251** today — a shortfall of **131 documents**.
>
> This stage cannot supply them. Of the 135 documents in [90,100), only **26** sit at
> or below 92; the other 109 already score above 92 and converting them to 100 changes
> the count by zero. So near-miss closure can contribute at most 26 of the 131 needed.
>
> The median target is bought by **Stage L2**, by landing the ≈50 cluster above 92
> rather than at 90. That was verified directly against the recorded per-document
> scores, not inferred.
>
> Credit where it is due: a crush reviewer flagged "the median-target arithmetic looks
> broken" before it was stopped. It was right and I had not checked.

Method: for each near-miss, diff the candidate render against the oracle render and
classify the single largest residual ink region. Group by cause, fix by group. Expect
the groups to be small and numerous — spacing, pilcrow properties, list start values,
underline extents — which is why this is staged last and gets its own iteration budget.

**Honest risk:** 43% is a demanding conversion rate and I will not promise it from the
current evidence. If L4 stalls below it, lossless lands at roughly mean 86 / median 90 /
perfect ~180 — mean cleared, median and perfect missed. Say so in that case rather than
moving the target.

## Verification

- Red-first: every stage lands a failing fixture test that fails for the *right*
  reason before any engine change.
- Full 763-document ITT re-run per stage, `corpus_revision` recorded, no partial-corpus
  comparisons (D1).
- The 40-pair sealed holdout is run **once, at the end**, to check the work generalised
  rather than fitted the visible corpus.
- Lens-disagreement rate reported alongside — a mean that rises while pixel/functional
  disagreement rises is overfitting to the pixel scorer.

## Deferred (per the standing constraint — noted, not implemented in this pass)

- Individual fixture chasing worth ≈5 points on one document.
- `math` (n=28, mean 57.6) and `rtl` (n=10, mean 55.2) as dedicated feature work —
  real gaps, but 38 documents between them; below the bar for this pass.
- Any per-fixture tuning that cannot be stated as a rule applying to unseen documents.

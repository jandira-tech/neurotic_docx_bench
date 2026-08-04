# What the ≈50 cluster actually is — and what the three targets really require

Measured 2026-08-04, directly, without agents. Everything here is reproducible from
`results/detail/*.json.gz` and the probe artefacts in `~/temp/T/r2-probe/`.

Two findings. The first changes the strategy of all three plans. The second explains why
every mechanism-level hypothesis of the last two days has failed, including four of mine
killed in the course of writing this document.

---

## Finding 1 — the targets are reachable, and they are a *transfer* problem

The official metric is **`overall_score_pagefair`** (not `average_score_pagefair`, which
runs ~1.2 points high and would have quietly inflated every table below). It reproduces
the plans' figures exactly.

| engine | mean | median | perfect | >92 |
|---|---:|---:|---:|---:|
| jubarte-rust | 76.21 | 77.95 | 158 | 282 |
| jubarte-lossless | 77.02 | 78.53 | 142 | 251 |
| jubarte-ast | 69.83 | 68.30 | 84 | 158 |
| docxodus 9.0.0 | 80.24 | 91.11 | 186 | 373 |
| **target** | **>81** | **>92** | **>200** | **≥382** |

**No engine in the benchmark hits any of the three targets — including docxodus at its
newest version.** The target is set above the best-known commercial engine on all three
metrics. That is worth saying plainly before anyone reads a plan that promises them.

But they are not out of reach, because the engines fail on *different documents*:

| | mean | median | perfect | >92 |
|---|---:|---:|---:|---:|
| envelope of the 3 jubarte engines | 84.01 | 92.07 | 233 | 384 |
| envelope incl. docxodus | 87.45 | 97.69 | 309 | 467 |

The jubarte-only envelope clears all four thresholds — median by 0.07 and perfect by 33.
**That is an oracle bound (best-of-three per document, chosen with hindsight), never
publishable, and it is the ceiling on every "harvest from your sibling" stage in the
three plans.** Median 92.07 against a target of >92 means the transfer stages have
essentially *zero* margin: they must land almost perfectly to buy the median at all.

### The transfer matrix — where the required documents actually are

Documents where a sibling already clears the bar and this engine does not:

| engine | needs >92 | rust | lossless | ast | docxodus | **union** |
|---|---:|---:|---:|---:|---:|---:|
| rust | +100 | — | 79 | 47 | 134 | **185** |
| lossless | +131 | 110 | — | 54 | 182 | **216** |
| ast | +224 | 171 | 147 | — | 242 | **309** |

| engine | needs perfect | rust | lossless | ast | docxodus | **union** |
|---|---:|---:|---:|---:|---:|---:|
| rust | +42 | — | 52 | 42 | 111 | **151** |
| lossless | +58 | 68 | — | 38 | 118 | **167** |
| ast | +116 | 116 | 96 | — | 125 | **225** |

Every engine has **~1.8× the documents it needs** already solved by something else in
the benchmark. The work is not "invent new capability"; it is "find out why the sibling
wins and port it." This is the single most useful table produced in this programme and it
should replace the cluster-lift arithmetic at the top of all three plans.

**Caveat, stated up front:** a document another engine scores 100 on proves the document
is *winnable*. It does not prove the mechanism is portable, and Finding 2 is a direct
warning about how hard porting will be.

---

## Finding 2 — the ≈50 cluster is not a markup defect. It is accumulated layout drift.

### The decisive observation

Take `evals__document_9bff7e1b_evals__employment_offer_4cf5a872`, score **54.43**, one of
the 46 cluster documents whose **body text is byte-identical to Word's oracle**. Rendered
side by side, candidate and oracle are visually near-identical. The only visible
difference on page 1 is that Word renders a five-item list as `•` bullets and the
candidate renders it as `1.`–`5.` at a wider indent.

That one difference is enough:

| | oracle y | candidate y | drift |
|---|---:|---:|---:|
| "Compensation" | 619 | 619 | 0 |
| "Benefits" | 966 | 957 | −9 px |
| "Confidentiality" | 1206 | 1184 | −22 px |
| "At-Will Employment" | 1321 | 1295 | −26 px |

And the scorer's tolerances are **`max_shift_px = 5.0`** and **`ink_tol_px = 2.0`**.

The consequence, per page:

| page | ssim_full | ink_f1 | edge_iou | color_sim | ΔE |
|---|---:|---:|---:|---:|---:|
| 1 | 0.8086 | 0.5614 | 0.3793 | 0.0000 | 24.7 |
| 2 | 0.9022 | **0.2121** | 0.1281 | 0.0000 | 31.5 |

Page 2 is worse than page 1 because the offset **accumulates**. By page 2 only 21% of ink
lands within 2 px of where the oracle put it. A visually near-perfect document scores 54.

### This explains the whole cluster's term profile

Cluster term means, all three engines, and they are nearly identical to each other:

| term | weight | rust | lossless | ast | points lost (rust) |
|---|---:|---:|---:|---:|---:|
| ssim_full | 0.25 | 0.799 | 0.791 | 0.763 | 5.03 |
| ssim_small | 0.15 | 0.725 | 0.715 | 0.680 | 4.13 |
| ink_f1 | 0.20 | 0.403 | 0.387 | 0.299 | 11.94 |
| edge_iou | 0.15 | 0.292 | 0.284 | 0.198 | 10.62 |
| color_sim | 0.15 | 0.092 | 0.104 | 0.031 | 13.61 |
| blob_sim | 0.10 | 0.913 | 0.921 | 0.917 | 0.87 |
| | | | | | **46.20 → score 53.80** |

`ssim_full` stays high (0.80) — the page is *structurally* right. `ink_f1` and `edge_iou`
collapse — the ink is in the *wrong place*. That is the signature of offset, not of wrong
content.

**The three engines' clusters are term-for-term the same shape.** They are not three
different problems; they are one problem with three implementations.

### Four hypotheses killed while writing this

Each was plausible, each was measured, each is dead. Recording them so nobody spends a
day re-deriving them.

| hypothesis | test | verdict |
|---|---|---|
| **`color_sim ≈ 0` is an independent 13.5-point lever** (author-colour or palette bug) | conditioned colour on alignment | **DEAD.** ssim>0.99 → color_sim 0.9995, ΔE 0.01; ssim<0.90 → color_sim 0.000, ΔE 30.06. Only 6.4% of well-rendered pages lose colour independently. It is a symptom. |
| **Style-resolved paragraph spacing drives the drift** | resolved docDefaults → basedOn chain → style → direct pPr, summed the vertical advance over 46 text-identical docs | **DEAD.** 37/46 differ on ≥1 paragraph, but the cumulative delta is **median 0 twips**. Individual docs reach ±900 px; the median does not move. |
| **Page geometry (`sectPr`) differs** | body-level `sectPr` only | **DEAD, and I first got it wrong.** A buggy "last sectPr in document order" pick counted paragraph-level section breaks and reported 37/46. Corrected: **15/46**, and every difference is default-value serialisation — `orient="portrait"`, `gutter="0"`, `code="0"`, `cols space="720"`. Identical h/w and margins. Zero layout effect. |
| **Dropped headers/footers shift the body origin** | part-manifest diff vs oracle | **DEAD as a cluster explanation.** Real defect — candidate drops ≥1 header/footer in **57.8%** of cluster docs that have them. But the ≥90 reference group drops them at **41.4%** and still scores ≥90. Enriched 1.4×, not causal. |

### Real defects found, correctly sized

These are genuine and worth fixing. None of them explains the cluster.

| defect | cluster rate | reference rate | enrichment |
|---|---:|---:|---:|
| list paragraph resolves to a different **format** than Word | 26/67 (38.8%) | 5/27 (18.5%) | 2.1× |
| list renders **bullet where Word renders number** (or vice versa) | 13/67 (19.4%) | 2/27 (7.4%) | 2.6× |
| drops ≥1 header/footer part | 57.8% | 41.4% | 1.4× |
| `numPr` children emitted `numId,ilvl` — schema sequence is `ilvl,numId` | 15/46 | — | schema-invalid OOXML |
| drops `word/people.xml` (tracked-change author registry) | 20/46 | — | Word-validity risk |
| `pStyle` naming differs (`Normal(Web)` vs `NormalWeb`) | 27/46 | — | both resolve; cosmetic |

Two of these bear on **Word validity** rather than score — the `numPr` child order
violates the CT_NumPr sequence, and `people.xml` is dropped while `w:ins`/`w:del`
author attributes are retained. Neither shows up in a pixel score. Both should be fixed
on correctness grounds regardless of what they do to the benchmark.

Note the honest direction of the list finding: within the cluster, documents with the
*wrong* list kind score **53.43** against **51.59** for those with the right one. The
enrichment against the reference group is real; the within-cluster discrimination is
nil. That is the pattern of a contributing cause among many, not a dominant one.

---

## What this means for the three plans

**The ≈50 cluster has no single cause, and every plan is written as though it does.**
L2, R2 and A2 each assume "identify the mechanism, fix it, the cluster lifts above 92."
The measurement says the cluster is many individually-inert formatting differences
accumulating past a 5 px alignment tolerance. Fixing any one of them moves a document a
few pixels, and a few pixels is not the difference between 50 and 92.

Three consequences:

1. **A cluster document is fixed only when its *total* drift is under ~5 px** — which
   means fixing essentially all of its formatting divergences, not the largest one. The
   C3 floor of "≥75% of the cluster lands above 92" is not reachable by mechanism-fixing
   and should be re-derived or the stage re-scoped.

2. **Re-serialisation is the architectural culprit.** Every difference found is the
   engine re-emitting formatting rather than passing it through: adding `orient`,
   dropping `gutter`, reordering `numPr`, renaming `Normal(Web)`, re-deriving a list
   format. Each is individually harmless and collectively fatal. This is why
   **jubarte-lossless leads the family on `page_median` (83.30 against rust's 65.99)
   while trailing badly on `skill_median` (53.07 against 86.19)** — preserving the
   document is exactly the right instinct for page fidelity. C7 warned that lossless's
   conservatism might be the same property as its page fidelity. It is, and the
   measurement now says so.

3. **The transfer matrix in Finding 1 is the better plan.** Not because transfer is easy,
   but because a sibling scoring 100 on a document is proof that document's entire
   formatting chain can be preserved end-to-end — which is precisely the capability the
   cluster needs and no single mechanism supplies.

---

## Finding 3 — the outcome is **binary**, which makes transfer mechanically tractable

Measured after the two findings above, and it is the most useful of the three.

On the 79 documents where lossless clears 92 and rust does not, lossless is not merely
*better*. It is **essentially exact**:

| page term | rust | lossless |
|---|---:|---:|
| ssim_full | 0.8765 | **0.9993** |
| ink_f1 | 0.7613 | **0.9991** |
| edge_iou | 0.5327 | **0.9989** |
| color_sim | 0.0000 | **0.9833** |
| page_count_mismatch | 6/79 | **0/79** |

And it is perfectly symmetric. On the 110 documents where rust clears 92 and lossless
does not:

| page term | rust | lossless |
|---|---:|---:|
| ssim_full | **0.9999** | 0.9796 |
| ink_f1 | **1.0000** | 0.7743 |
| edge_iou | **0.9986** | 0.5922 |
| color_sim | **1.0000** | 0.0810 |

`null_score` is identical (49.22) on both sides, confirming these are the same documents
scored the same way.

**There is no middle.** On any given document an engine either reproduces Word's layout
essentially exactly, or it drifts and lands at 50–70. This is the same 5 px cliff from
Finding 2, seen from the other side: drift under tolerance scores ~100, drift over
tolerance scores ~50, and almost nothing sits between.

### Why this matters more than either finding above

It changes what a transfer stage actually has to do. The natural reading of "port what
lossless does" is *compare rust's output to Word's oracle and find the difference* — and
Finding 2 shows how badly that goes: the differences are numerous, individually inert,
and mostly irrelevant. I killed four hypotheses that way.

The binary result licenses a far better experiment:

> For each of the 79 documents, diff **lossless's candidate** against **rust's candidate**
> — two outputs from the same source pair, one of which is *verified correct* by its own
> score of ~100.

That diff is small, and every difference in it is by construction score-relevant, because
one side scores 100 and the other 50. Comparing against Word's oracle cannot distinguish
a difference that matters from one that does not; comparing a winner against a loser can.
The same applies in reverse for the 110, and to ast against both.

**This is the concrete Stage R1/L1/A1 method, and it replaces the "harvest from your
sibling" text in all three plans**, which never said how. It is also cheap: both artefacts
already exist in any run directory.

---

## Pre-registered prediction for the run now in flight

`bench run --only jubarte-rust` is executing against `ENGINE_COMMIT.txt = 1be1fcd`
(workstream S, style-chain resolution). Its effect was already A/B-measured on 21 cluster
documents in `~/temp/T/r2-probe/ab_scores.json`, against a base build verified to
reproduce the scored artefact:

- 7 of 21 moved (33%); 14 unchanged to the float.
- mean delta over all 21 sampled: **+3.64**; over movers only: **+10.92**.
- one document crossed 92 (`h_f_normal_odd_even_firstpg…`, **59.65 → 97.36**).

Extrapolated naively to the 197-document cluster:

| | predicted |
|---|---|
| ITT mean | 76.21 → **≈77.15** (+0.94) |
| above-92 | 282 → **≈291** (+9) |
| perfect | ≈158 (unchanged) |

**This is recorded before the result is known.** If the run lands materially above this,
the extrapolation was wrong and the 21-document sample was unrepresentative; if it lands
at or below, workstream S is confirmed as a genuine but small lever — roughly **20% of
rust's mean gap and 9% of its median gap** — and the plans that leaned on it need the
remainder found elsewhere, per contract C4.

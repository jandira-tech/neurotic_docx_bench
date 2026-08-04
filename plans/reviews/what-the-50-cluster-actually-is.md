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

### Executed — and the answer prices the transfer stages honestly

Run on the 78 documents where lossless clears 92 and rust does not, comparing
`runs/jubarte-final-lossless_2026-08-04_17-31/docx` against
`runs/jubarte-rust_2026-08-04_17-47/docx`, same source pair, winner against loser:

| part | differs |
|---|---|
| `word/document.xml` | **78 / 78 (100%)** |
| `word/settings.xml` | **78 / 78 (100%)** |
| `word/styles.xml` | **78 / 78 (100%)** |
| `word/theme/theme1.xml` | **78 / 78 (100%)** |
| `word/numbering.xml` | 37 / 37 (100%) |
| `word/header1.xml`, `word/footer1.xml` | 29 / 29 (100%) |
| `word/fontTable.xml` | 47 / 78 (60%) |

**Every part differs, in every document.** The two engines do not produce similar files
with a localised divergence; they produce entirely different serialisations of the same
logical document. rust additionally drops `word/header1.xml` in **14** of the 78.

> **CORRECTION, and it weakens this table — I did not control for non-determinism.**
> The `stage2-measure` session subsequently established that **the lossless generator is
> not byte-reproducible**: the same build on the same inputs twice changes **206 of 207**
> outputs, because a wall-clock `w:date` is written on every `w:ins`/`w:del`, and after
> normalising dates **27 still differ** through GUID-named media parts. (rust has neither
> problem — 0 changed over 607 regenerated pairs.)
>
> So `word/document.xml` differing on 78/78 was **guaranteed before any engine
> difference is considered**, and the same applies to any part carrying a date or a media
> reference. The 100% figures above are inflated by an unknown amount and **must not be
> quoted as evidence of divergence.** It cost the other session a wrong answer too — its
> first output diff read "800 of 803 changed" before it ran the control.
>
> **What survives the correction:** `word/styles.xml`, `word/settings.xml` and
> `word/theme/theme1.xml` carry no timestamps or GUIDs, and the preserve-vs-regenerate
> table below is computed against the *sources*, not between engines — so the finding
> that **both engines regenerate `styles.xml` and `settings.xml` unconditionally**, and
> that lossless preserves `theme1.xml` where rust never does, is unaffected. The
> architectural reading stands on that evidence; it no longer stands on "100% of parts
> differ."
>
> **Method, now binding for anyone repeating this:** normalise `w:date` and GUID media
> names before diffing lossless output, and run a same-build-twice control first. This is
> C8 applied to the diff itself — a byte difference is not evidence until you have shown
> the generator would not have produced it anyway.

That is a genuinely bad result for the plans, and it must be said plainly: **the
winner-vs-loser diff does not localise the defect, because there is no locality.**
"Port what lossless does" is not a patch — the two engines share no serialisation
surface to port across. Stages R1 / L1 / A1 are therefore **architectural** work
(make one engine emit what the other emits), not the transfer-of-a-mechanism the
plans describe and size.

The preserve-vs-regenerate split confirms the same thing from the other direction:

| part | lossless copies source verbatim | rust copies source verbatim |
|---|---:|---:|
| `theme/theme1.xml` | 94% (on its winning set) | **0%** |
| `fontTable.xml` | 50% | 94% |
| `styles.xml` | 0% | 0% |
| `settings.xml` | 0% | 0% |

Both engines regenerate `styles.xml` and `settings.xml` unconditionally. That is the
re-serialisation habit Finding 2 identifies, present in both, and it is why both engines
have a ≈50 cluster with the same term profile.

### The named attribute set — the direct cause of the vertical advance

Contributed by the `stage2-R2-inplace-rust` session and reproduced here because it is the
answer to the question Finding 2 leaves open. Effective spacing resolved through
docDefaults → `basedOn` chain → direct `pPr`, per attribute, over the 46 text-identical
documents (3714 paragraphs), candidate against Word:

| effective attribute | at the scored baseline | documents |
|---|---:|---:|
| `w:spacing/@line` | 436 paragraphs (11.7%) | 29/46 |
| `w:spacing/@after` | 337 (9.1%) | 31/46 |
| `w:spacing/@before` | 147 (4.0%) | 15/46 |
| `w:spacing/@lineRule` | 130 (3.5%) | 6/46 |

Top transitions (candidate → oracle):

```
130  after     cand=160   oracle=0
123  line      cand=240   oracle=276
104  line      cand=278   oracle=240
102  lineRule  cand=None  oracle=auto
 69  line      cand=None  oracle=240
 56  before    cand=240   oracle=0
```

`after=160 line=278` is Word's modern (Calibri) default block; `after=0 line=240` is the
classic one. **We get it wrong in both directions on different paragraphs of the same
corpus** — 123 paragraphs where we write classic and Word writes modern, 104 the reverse.

That is the diagnostic fact, and it rules out the obvious explanation. A global
stylesheet mis-pick cannot produce both directions at once; **per-paragraph
side-of-origin can** — i.e. whether a paragraph's style formatting is kept from A or
taken from B. `docDefault_spacing` differs on only **1/46**, so the divergence lives in
the paragraph-style layer, not in docDefaults.

Two further results from the same measurement, both worth keeping:

- **The defect substantially survives workstream S.** The style-chain work removes only
  ~15% of the divergence (`line` 444 → 436). That is an independent confirmation of the
  +0.50 headline in [stage1-measured-impact.md](stage1-measured-impact.md): S is real and
  small, and it is not the spacing fix.
- **`finalize.rs::normalize_incomplete_spacing` rule 2 is NOT the driver** — it accounts
  for 21 paragraphs. It was the leading hypothesis (it adds `lineRule="auto" line="240"`
  where Word writes neither, and its own doc comment says Word strips it) and its author
  retracted it on measurement. An eighth dead hypothesis, and the best-named one.

**This is the real Stage R3**: deciding per paragraph which side's paragraph-style
formatting is live. It is the same class of change as workstream S, and it is the first
mechanism identified in this programme that is both precisely specified and plausibly
large enough to matter.

> **Provenance warning attached to this measurement.** It was first reported alongside a
> claim that `1be1fcd` produces output byte-identical to the scored baseline binary, and
> therefore that workstream S was already priced into 76.2072. **That claim is false and
> was retracted.** The dist binary was rebuilt from `1be1fcd` at 17:31, so comparing a
> `1be1fcd` build against it is trivially identical and says nothing about the baseline.
> The decisive counter-argument needs no file forensics: byte-identical binaries cannot
> move 73 documents' scores, and `stage2-measure` independently found 256 of 803 pairs
> producing different `word/styles.xml`. This is the D5 split-brain — provenance read off
> an artifact mutated underneath the reader — and it is the second instance in this
> programme after the docxodus "9.0.0" retraction. **The spacing table above is unaffected
> and stands.**

**Seventh dead hypothesis, recorded:** rust's regenerated `theme1.xml` was the obvious
suspect, since theme fonts resolve every `asciiTheme`/`minorHAnsi` run and a wrong
typeface rewraps every line. It is not the cause — rust preserves the source's major and
minor latin theme fonts in **390 of 390** documents checked. The theme regeneration is
cosmetic.

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

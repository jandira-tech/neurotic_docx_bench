# Stage 1 measured impact — did either engine fix move a score?

Written 2026-08-04. This is the falsifiable test the execution contract
([../jubarte-execution-contract.md](../jubarte-execution-contract.md)) requires before
any stage may be called complete. C1 forbids accepting a stage on the strength of a
plausible mechanism; only a measured before/after counts.

Two fixes were shipped in Stage 1:

| engine | branch | commit | what it does |
|---|---|---|---|
| jubarte-first (TS) | `feat/style-chain-resolution` | `d99ccb5b3` | repoint `numbering.xml` style refs after a styleId rename |
| jubarte-redlines (Rust) | `feat/style-chain-resolution` | `1be1fcd` | resolve the style chain on both sides; Word-style style-level `w:pPrChange`/`w:rPrChange` |

---

## Part 1 — jubarte-lossless (TS). Verdict: **zero measured effect.**

### Provenance — the rebuild demonstrably took

The point of stamping provenance is that "the fix didn't help" and "the fix wasn't in
the binary" are indistinguishable from the score alone. They are distinguishable here:

| | baseline | candidate |
|---|---|---|
| run timestamp | 2026-08-04T11:01:14 | 2026-08-04T21:31:47 |
| `tool_version` | `jubarte-final@d43557e042c1` | `jubarte-final@6db0dcdb2f1a+git.d99ccb5b3adda605e5304200ad88c1aff7fe53c2` |
| `corpus_revision` | `b7f467074a51` | `b7f467074a51` — **same** |
| `scorer` | `pagefair-v2` | `pagefair-v2` — **same** |
| `score_config` | *(6-term pagefair weights)* | **byte-identical** |
| `holdout_mode` | `excluded` | `excluded` — **same** |

The content hash moved `d43557e042c1` → `6db0dcdb2f1a`. **The built artifact is
genuinely different**, and the `+git.d99ccb5b3…` suffix names the commit that made it
different. This is not a stale-binary result.

### Result

| | baseline | candidate | delta |
|---|---:|---:|---:|
| ITT mean | 77.0151 | 77.0151 | **0.0000** |
| ITT median | 78.5311 | 78.5311 | **0.0000** |
| perfect (100) | 142 | 142 | **0** |
| failures | 0 | 0 | 0 |
| `skill_median` | 53.0737 | 53.0737 | **0.0000** |
| `page_median` | 83.2988 | 83.2988 | **0.0000** |

Headline identity is weak evidence — offsetting per-document moves produce it too. So
the test was run per document, not on the summary:

```
base n: 763   new n: 763   union: 763
only in base: 0   only in new: 0
*** documents whose score changed: 0 ***
```

**Zero of 763 documents changed, at a tolerance of 1e-9.** Not "changed a little" —
every one of the 763 floats is bit-identical. The document key sets are also identical,
so this is the same population scored twice, not two different populations that happened
to average the same.

### Ratchets (C1)

| ratchet | outcome |
|---|---|
| R-perfect | **PASS** — 142 → 142, no document left 100 |
| R-92 | **PASS** — unchanged |
| R-fail | **PASS** — 0 → 0 |
| R-tail | **PASS** — max absolute movement is 0.0000 |

All four pass, and they pass **vacuously**. A stage that trips nothing because it did
nothing has not earned a green light; the ratchets are a safety net, not evidence of
value.

### One confound, checked and cleared

`environment_config` differs between the two runs. The baseline chained **three**
`generate-native-redlines.ts` invocations (default corpus, `…_randomized`,
`word_redlines_superdoc`); the candidate ran **one**. That looked at first like a
truncated pipeline that would have starved 400 documents of candidates.

It is not. `bench.yaml` is clean in the working tree and carries the single-pass form;
the generator was refactored to walk the corpora itself. The decisive check is the
population, not the invocation: **the two runs' per-document key sets are equal, with
zero keys on either side alone, at n=763 both.** Same documents, same scores, different
engine. The comparison stands.

`config_hash` also differs (`c7c1789e6edf` → `203541f4c584`), which is the
`environment_config` change hashing through. `score_config` — the part that could move a
number — is byte-identical.

### Verdict — blunt

**The fix is correct and worthless on this corpus, and I do not yet know which.**

Two readings survive the measurement and it does not distinguish them:

1. **Correct but unreachable.** No document in the 763 exercises a styleId rename that
   also carries `numbering.xml` references, so the repaired code path never executes.
   The bug is real (heading styles silently lose outline numbering) and the corpus
   simply does not contain it.
2. **Reachable but inert.** The path executes and the repair makes no rendered
   difference — which would mean the mechanism was mis-diagnosed.

These have opposite consequences. Under (1) the fix is worth keeping and the corpus is
worth extending. Under (2) it should be reverted. **Reachability is being measured
separately; this document will be amended with the answer rather than guessing at it.**

> **ANSWERED in Appendix §A — and the dichotomy above was wrong.** It is **(2), reachable
> and inert**: rebuilding parent `2f4eb955c` shows dangling `Ttulo1..9` references in
> `word/numbering.xml` going **7 → 0**, with `numbering.xml` a changed part on all seven,
> and all seven scoring identically before and after.
>
> **But "revert" does not follow, and that inference was my error.** I conflated *inert in
> the score* with *mechanism mis-diagnosed*. They are different things. The mechanism was
> diagnosed correctly; the repair is invisible because **our oracle renders through
> LibreOffice, and LibreOffice does not read the style→numbering binding**
> (`w:lvl/w:pStyle`, `w:styleLink`, `w:numStyleLink`). In Word — the thing the fix is
> actually for — outline numbering is restored on seven heading-heavy documents.
>
> **Verdict: KEEP.** This is a scorer blind spot, not a failed fix, and it is a
> second instance of the pattern already noted for the `numPr` child-order and
> `people.xml` defects: real Word-validity repairs that no pixel score can see. A
> benchmark whose oracle is LibreOffice cannot price them, and that limitation should be
> stated wherever these numbers are published rather than left for a reader to infer.

What is settled either way: **this fix does not contribute to Plan 1's targets.** Any
arithmetic that counted on Stage L3 / workstream S moving lossless's mean or median is
short by whatever it assumed, and per C4 that shortfall must be found elsewhere or the
target declared missed. It may not be quietly carried.

### What this says about the method, not just the fix

This is the third Stage 1 hypothesis to die on contact with the corpus, and the three
failures rhyme:

| hypothesis | how it died |
|---|---|
| lossless "under-marks the edit" | ins/del volume vs oracle is median **1.000** — volume was never the defect |
| weak `rstyle`/`combos` tokens ⇒ style-inheritance bug | **0 of 25** pairs' `document.xml` changed; the tokens name what a fixture *tests* |
| rust's ≈50 cluster fails like lossless's | rust matches Word on that axis; **46 of 197** are byte-identical to the oracle and still score 52.29 |

Each was diagnosed from score-space — token means, cluster membership, sub-metric
splits — and each was refuted the moment someone read the actual XML. That is contract
C7's blind spot arriving as a measured pattern rather than a caveat, and the honest
reading is that **score-space diagnosis has now failed often enough that it should stop
being the first move.**

---

## Part 2 — jubarte-rust. Verdict: **real, small, and it trips a ratchet.**

### Provenance

| | baseline | candidate |
|---|---|---|
| run | 2026-08-04T10:41:28 | 2026-08-04T21:47:16 |
| `tool_version` | `jubarte-rust@fcea02da49f4` | `jubarte-rust@8a1e896365b3+git.1be1fcd060ce0d8e…` |
| `corpus_revision` | `b7f467074a51` | `b7f467074a51` — same |
| `scorer` / `score_config` | `pagefair-v2` | identical, byte-for-byte |
| `holdout_mode` | `excluded` | `excluded` |
| per-document keys | 763 | 763, **zero unique to either side** |

Content hash moved and the commit is stamped. The rebuild took.

### Result — and the pre-registered prediction was 2× optimistic

| | predicted | **actual** | baseline → new |
|---|---:|---:|---|
| ITT mean | +0.94 | **+0.50** | 76.21 → 76.71 |
| ITT median | — | **+1.02** | 77.95 → 78.97 |
| above 92 | +9 | **+1** | 282 → 283 |
| perfect | 0 | **0** | 158 → 158 |
| cluster [40,60) | — | **−9** | 197 → 188 |

**73 documents changed — 57 up, 16 down.** The direction and the sign were right; the
magnitude was not. The 21-document A/B sample over-estimated the mean effect by ~2× and
the above-92 effect by ~9×, because a hand-picked cluster sample over-represents movers.
That is a calibration lesson worth more than the stage: **sampled A/B deltas extrapolate
badly to a full corpus, and should be treated as an upper bound.**

### Ratchets (C1)

| ratchet | outcome |
|---|---|
| R-perfect | **PASS** — 158 → 158, no document left 100 |
| R-92 | **PASS** — 282 → 283 |
| R-fail | **PASS** — 0 → 0 |
| R-tail | **TRIP** — one document dropped >10 points |

The tripping document, enumerated as C1 requires:

- `super_editor__two_column_two_page_0b8a37c5_behavior__sd_2672_nested_table_…` —
  **80.83 → 33.80 (−47.03)**

**It is not drift. It is a layout blow-up, and the page data names it.** The candidate
emits 21 pages (matching the oracle's 21), but pages **2 through 20 are byte-identical
renders** — `ink_area` 191992 and `ink_f1` **0.010** on every one of them. One page
repeated nineteen times, overlapping the oracle almost nowhere.

The contrast with the sibling pairing is exact. `super_editor__two_column_two_page_0b8a37c5_super_editor__vrect_node_…`
(the +45.64 gainer) emits 21 pages that **alternate** between `ink_area` 90419 and 102468
at `ink_f1` **1.000** — a perfect match to Word. And a third pairing of the same family,
`super_editor__two_column_two_page_arial_…`, scores **99.71**.

So the same two-column base document, paired three ways, produces a perfect score, a
+45.64 gain, and a −47.03 collapse into a repeating page. This is a **section/column
progression defect**, not a tuning imbalance, and it is the sharpest single engine bug
found in this programme.

> **Infrastructure integrity check (D3).** A teammate session reported killing shared
> `soffice` processes with a broad pattern kill and warned this run might be corrupted.
> **It is not.** `runs/jubarte-rust_2026-08-04_17-47` completed at 18:22:54; the kill
> window belongs to `jubarte-wasm_2026-08-04_18-31`, which started afterwards. Verified
> empirically rather than by timestamp: **docx 803 / pdf 803, zero missing, zero
> zero-byte**, `n_failures=0`, `n_oracle_unmatched=0`, and this document's own PDF was
> written at 17:53 with `page_count_candidate == page_count_oracle == 21`. The −47.03 is
> the engine's, not ours.
>
> **`jubarte-wasm` is the run at risk and its result must not be trusted without a
> re-check.** Plan 2 treats rust and wasm as one engine in two bindings that must score
> identically (both 76.2072 / 77.9542 / 158 at baseline). If wasm diverges from rust, the
> first hypothesis is the killed renderer, not a lossy binding.

And the fact that makes it legible: the *same base document* paired the other way,
`super_editor__two_column_two_page_0b8a37c5_super_editor_…`, moved **+45.64 (33.69 →
79.34)**. Same source, two pairings, ±45 points in opposite directions. The style-chain
change flips which side's two-column section setup wins, and it is right in one pairing
and wrong in the other. That is not a tuning problem; it is an unresolved **merge-policy
question about section properties**, and it is the same question Finding 1 of
[what-the-50-cluster-actually-is.md](what-the-50-cluster-actually-is.md) raises.

**C1's deliberate-exception clause covers R-perfect and R-92 only — it does not extend to
R-tail.** Read strictly, this stage is not complete. The net is positive (+0.50 mean, +1
above 92, cluster −9) and the trip is a single document with a now-understood cause, so
my recommendation is **keep the commit and open the two-column pairing as a named
defect** rather than revert — but that is a deviation from the contract as written and
it is recorded as one, not waved through.

Top gainers, for the record: +45.64, +45.56 (`evals__nda…` 45.20 → 90.76), +37.70
(`h_f_normal_odd_even_firstpg…` 59.65 → 97.36), +35.00, +33.70, +27.55.

### Verdict

Workstream S is **real and small**. Against rust's gaps it delivers **10% of the mean
shortfall and 1% of the above-92 shortfall**. Contract C4 declared S "a dependency, not a
bonus" in every plan that cites it; the dependency has now been priced, and every plan
that leaned on it must find the remainder elsewhere or declare the target missed.

---

## Combined verdict on Stage 1

| fix | ITT mean | above 92 | perfect |
|---|---:|---:|---:|
| jubarte-first `d99ccb5b3` (numbering.xml style refs) | **0.00** | 0 | 0 |
| jubarte-redlines `1be1fcd` (style-chain resolution) | **+0.50** | +1 | 0 |

Two engine fixes, both shipped, both correct as code, and together they close **~10% of
one engine's mean gap and ~1% of its median gap.** Nothing in Stage 1 moved `perfect` by
a single document.

This is exactly what the cluster analysis predicts: the ≈50 cluster is accumulated layout
drift past a 5 px tolerance, no single mechanism dominates it, and mechanism-fixing
therefore returns fractions of a point. **Arthur — on this evidence the targets (mean 81
/ median 92 / 200 perfect, on all three engines) are not reachable by the mechanism-fixing
strategy the three plans describe.** The transfer matrix is the only route with enough
headroom, and it is a substantially larger project than the plans currently admit.

---

## Appendix — the reachability measurement, the affected population, and the noise floor

Added 2026-08-04 by the agent that executed the two candidate runs. Everything above
was written from `results/bench.jsonl` alone. This appendix adds what the score log
cannot answer: **which documents each fix actually touched**, established by rebuilding
each engine's parent commit and diffing its output part-by-part against the candidate's.
It resolves the open question in Part 1's verdict and supplies the 136-pair test Part 2
was written to perform.

### A. Part 1's open question, answered: **reachable and inert**

Part 1 leaves two readings alive — "correct but unreachable" (the corpus contains no
document exercising the path) and "reachable but inert" (it runs and changes no pixel) —
and says the answer will be measured rather than guessed. It has been measured. **It is
(2), reachable but inert**, and the mechanism was not mis-diagnosed either.

The parent commit `2f4eb955c` was rebuilt from a scratch clone and run over all 803
pairs. Counting outputs that emit a style reference resolving to no definition:

| | parent build | candidate build |
|---|---:|---:|
| pairs with a dangling style reference | **25** | **18** |
| pairs with dangling `Ttulo1..9` refs in `word/numbering.xml` | **7** (9 refs each) | **0** |

All seven are repaired, and `word/numbering.xml` is a changed part on all seven. The
commit claims five; five is the count inside the 400-pair SuperDoc pool it measured. The
other two live in `word_based`:
`sample_document_word_repair_of_our_output_word_repaired_sd_2517_localized_heading_styles`
and `sd_2517_localized_heading_styles_sectpr_headerref`. The 18 that remain are the
deliberate ones the commit names — `Hyperlink`, `TableGrid`, plus `Heading*` / `Subtitle`
/ `Title` / `style0` cases in the other pools.

All seven repaired pairs are inside the scored 763, and all seven score **exactly the
same before and after**: 55.1852, 44.4307, 43.6138, 44.3895, 44.6158, 43.3929, 82.0248.

So outline numbering was restored on seven heading-heavy documents and the LibreOffice
render did not move by one pixel. The style→numbering binding in `word/numbering.xml`
(`w:lvl/w:pStyle`, `w:styleLink`, `w:numStyleLink`) is not something this rendering path
reads. **Consequence for the verdict above: the fix should be kept, not reverted** — it
repairs a real defect in a Word-validity sense — but Part 1's headline stands unchanged,
and it contributes exactly zero to any lift table.

Two further checks that this is not a stale dist: the new symbol
`RemapStyleReferencesOutsideStylesPart` is present in the vendored
`dist/jubarte-final/lossless.node.cjs` — the exact file the `jubarte-lossless` generator
loads — and absent from the pre-change build.

### B. The rust affected population: 256 pairs, not 136 — and they moved

The Rust generator is **byte-deterministic** (regenerating pool 1 and the SuperDoc pool
with the same binary produced 0 changed outputs of 607). That makes the parent-vs-
candidate output diff an exact statement of the population the change touched, with no
reimplementation of `merge_revised_style_definitions`' gate in the middle.

**256 of 803 pairs changed, and in every one the only changed part is
`word/styles.xml`.** 234 gained style-level change records (median 10 newly marked
styles, max 51); the other 22 changed only through the element-order fixes the commit
also carries. 222 of the 256 are inside the scored 763.

| | n | baseline mean | candidate mean | Δ mean | Δ median | Δ below-50 | docs moved |
|---|---:|---:|---:|---:|---:|---:|---:|
| **touched by the fix** | 222 | 64.0723 | 65.7362 | **+1.6639** | **+1.7291** | **−7** | 64 (52 up, 12 down) |
| untouched | 541 | 81.1868 | 81.2148 | +0.0280 | 0.0000 | 0 | 9 (all noise, §D) |
| all | 763 | 76.2072 | 76.7112 | +0.5040 | +1.0168 | −7 | 73 |

Three readings, all of them load-bearing:

1. **The population thesis is confirmed on this corpus.** Pairs carrying a live style
   collision really are the weak ones — 64.07 against 81.19 for the rest. The claimed
   59.7-vs-79.4 split was measured on 597 pairs with a 537-document scored subset; the
   denominator is different but the shape reproduces.
2. **Those pairs really did move**, and the entire below-50 improvement comes from them.
3. **There is no collateral.** The untouched half moved +0.028, and every one of its nine
   movers is a pipeline-noise document (§D) — no document with an unchanged input moved
   for any other reason.

**The affected population on the 803-pair corpus is 256, not 136.** The 136 figure is not
wrong, it is measured on a different corpus; it should stop being quoted against this one.

### C. C2 census delta, with the cluster membership enumerated

| figure | baseline | candidate | Δ |
|---|---:|---:|---:|
| cluster [40,60) | 197 | 188 | **−9** |
| above 92 | 282 | 283 | +1 |
| near-miss [90,100) | 149 | 151 | +2 |
| near-miss ≤ 92 | 25 | 26 | +1 |
| perfect | 158 | 158 | 0 |
| shortfall to majority (382) | 100 | 99 | −1 |

`pool_shift = −0.0457`, `pool_churn = 0.0660`, **`sizing_void = False`** — the next
stage's sizing table survives, at two-thirds of the 10% churn limit.

Entered the cluster (2): `file_196_file_197`,
`super_editor__sd_2534_collab_export_f3c7fdf7_super_editor__sd_2766_pirates_tracked_changes_3285d875`.

Left the cluster (11): `behavior__sd_2447_toc_tab_alignment_8319c14c_super_editor__broken_complex_list_293fda86`,
`evals__nda_7f304918_super_editor__numwords_393421eb`,
`super_editor__custom_list_numbering1_7eb9fda4_super_editor__diff_before19_97e0f4e6`,
`super_editor__h_f_normal_odd_even_firstpg_9b210d9a_super_editor__basic_footnotes_5be96945`,
`super_editor__invalid_list_def_fallback_d7f55451_super_editor__line_break_627a7159`,
`super_editor__list_with_table_break_ff0c4c1f_behavior__sd_2672_plain_3x3_87943d5d`,
`super_editor__multi_section_doc_080d2655_behavior__pageref_standalone_uppercase_h_7701e07f`,
`super_editor__multi_section_doc_080d2655_super_editor__multiple_nodes_in_list_79d915a2`,
`super_editor__page_numbering_examples_13edaf84_super_editor__pagination_blank_2a98ed7a`,
`super_editor__restart_numbering_sub_list_85ddcb79_super_editor__sd_1919_word_table_74726d6c`,
`super_editor__simple_ordered_list_8288421a_super_editor__line_break_627a7159`.

For the lossless run the C2 census is unchanged in every figure (cluster 166, above-92
251, near-miss 135, perfect 142, shortfall 131; `pool_shift = 0.0`, `pool_churn = 0.0`).

The R-tail offender named in Part 2 is inside the changed population: its
`word/styles.xml` is the only changed part and the pass marked **40** styles on it — the
same 40 as on its sibling pair that gained +45.64. Same stylesheet, same pass, ±45 in
opposite directions.

### D. The measurement noise floor — nine documents move with an unchanged input

Because the Rust generator is byte-deterministic, the documents whose candidate DOCX did
**not** change between the two runs can be isolated and asked whether their score moved.
Nine of them did, with identical `score_config` and an oracle last written at 06:13,
before both runs:

| Δ | document |
|---:|---|
| **+12.7514** | `super_editor__advanced_text_78401c31_super_editor__google_docs_originated_comments___tcs_76ac865d` |
| +4.0347 | `super_editor__table_widths_sd_732_12074135_super_editor__table_c70ca973` |
| −3.8999 | `super_editor__ooxml_rfonts_rstyle_linked_combos_dem_213298de_behavior__sd_2672_rtl_table_63bd9d10` |
| +2.3789 | `super_editor__table_width_issue_20b01504_super_editor__table_widths_sd_732_12074135` |
| −0.9047 | `super_editor__advanced_text_78401c31_super_editor__alternatecontent_valid_de18b376` |
| +0.7728 | `super_editor__alternatecontent_valid_de18b376_super_editor__anchor_images_3327faf8` |
| −0.0021 | `behavior__math_groupchr_tests_4a4970fc_super_editor__diff_before16_f518c031` |
| +0.0016 | `behavior__math_groupchr_tests_4a4970fc_behavior__math_limit_tests_6dc07867` |
| −0.0008 | `behavior__math_groupchr_tests_4a4970fc_behavior__sd_2447_toc_tab_alignment_8319c14c` |

This is render/raster nondeterminism confined to a handful of SuperDoc-pool fixtures
(anchored images, tables, math) — the same fixtures behind the 0.004 disagreements in the
existing native-vs-WASM control. **Its worst excursion, +12.75, exceeds R-tail's own
10-point threshold.** Until that is characterised, a single-document R-tail trip on one of
these fixtures cannot be distinguished from the pipeline. The trip reported in Part 2 is
not one of them — it is four times larger and its input DOCX did change — but the
contract's per-document guarantees are softer than they read.

### E. `jubarte-final-native` / `jubarte-ast` is not affected, and was not re-run

Commit `d99ccb5b3` touches exactly one source file, `src/lossless/WmlComparer.ts`, which
is bundled only into `dist/jubarte-final/lossless.*`. The AST/native generator loads
`dist/jubarte-final/node.cjs`, which contains **zero** occurrences of
`RemapStyleReferencesOutsideStylesPart`, `CopyMissingNumberingFromOneDocToAnother`,
`CanonicalizeNonSemanticStyleIds` or `ProduceDocumentWithTrackedRevisions`. Re-running it
would have measured the render pipeline, not the change. If a run is wanted for the
record, its baseline is `019fcc7c-8d62-76ca-9532-1b2649691eb4` (763 ITT, mean 70.5699).

### F. A side finding: the lossless generator is not byte-reproducible

Generating the same 207 pairs twice with the *same* build produces **206 different
outputs**. The cause is benign — every `w:ins`/`w:del` carries a wall-clock `w:date` —
but after normalising dates, **27 of 207 still differ**, through GUID-named media parts,
`[Content_Types].xml` and `word/_rels/document.xml.rels`. The Rust engine has none of this
(0 of 607 on the same test). It does not affect scores, but any future attempt to
attribute a lossless change by diffing its output must normalise dates and ignore media
naming, or it will report 800 of 803 pairs "changed" — as the first pass of this analysis
did before the control was run.

### G. Provenance, checked as hard as it can be checked

The parent commit `d931a10` of the Rust engine was rebuilt from a scratch clone, and the
resulting binary is **md5-identical** (`32484369cd2d407345283227382129d7`) to the one the
baseline run used. The baseline is therefore exactly "the engine one commit earlier", not
"whatever happened to be vendored" — which is what makes every diff in this appendix
attributable to the single commit under test.

---

## Part 2 (superseded — original entry, kept for the record)

Status at the time of writing: **run in flight.**

`bench run --only jubarte-rust --rerun --no-gate` is executing against
`ENGINE_COMMIT.txt = 1be1fcd060ce0d8e2a1b0f91df618d8ec651e3ba`, the workstream S commit.
The pin is verified against the branch head before the run, so the provenance question
answered above for TS is answered in advance here.

Unlike the TS fix, this one has a **measured target population**: 136 of 597 pairs carry
a live styleId collision, and those 136 score mean **59.7** against **79.4** for the
rest. If the fix works, the movement should be concentrated there — so the test is not
just the headline delta but whether *those specific 136* moved.

> **Superseded by Appendix §B: the population on this corpus is 256, not 136.** The 136
> was measured on a different 597-pair corpus and should stop being quoted against the
> 803-pair one. The subgroup test was performed and it passes cleanly: **touched pairs
> (222 scored) move 64.07 → 65.74 (+1.66) while untouched pairs move +0.028**, and every
> one of the nine movers among the untouched is pipeline noise. The population thesis
> holds — collision-carrying pairs really are the weak ones — and the fix's effect is
> entirely confined to them, with no collateral.

Baseline to compare against (run `019fcc5d`, 2026-08-04T10:41:28,
`jubarte-rust@fcea02da49f4`):

| | baseline |
|---|---:|
| ITT mean | 76.2072 |
| ITT median | 77.9542 |
| perfect | 158 |
| failures | 0 |
| above-92 count | 282 |
| ≈50 cluster [40,60) | 197 |
| near-miss [90,100) | 149 |

To be filled in on completion: the four ratchets, the C2 census delta, the 136-pair
subgroup movement, and a keep-or-revert verdict on the same terms as Part 1.

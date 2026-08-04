# Execution contract — binding on all three jubarte plans

Created 2026-08-04 in response to the adversarial review
([reviews/crush-adversarial-2026-08-04.md](reviews/crush-adversarial-2026-08-04.md)),
which found six gaps present in **all three** plans. Each was a piece of machinery the
plans assumed and never built. This document builds it once and the three plans bind to
it, which also resolves the "referenced by three plans, owned by none" defect.

**Ownership: this contract is owned by Plan 2 (jubarte-rust)** — the engine closest to
all three targets and therefore the one that exercises the machinery first. The other
two consume it. Where a plan needs something this contract does not yet provide, the
plan implements its own copy and says so; it does not wait.

---

## C1 — The regression ratchet (fixes convergent gap 1)

**The defect.** Every lift table in the three plans computes a stage against the frozen
baseline as if all other documents stand still. The perfect-count arithmetic
`158 + 42 = 200` is **gross, not net**: each document an earlier stage knocks from 100
to 99 raises the conversion requirement by one, silently.

**The contract.** Every stage, on every ITT re-run, is gated by:

| ratchet | rule | rationale |
|---|---|---|
| **R-perfect** | no document scoring 100 at the stage's entry baseline may score < 100 at exit | protects the perfect count, which is the target with no slack |
| **R-92** | the count of documents scoring > 92 may not decrease | protects the median, whose shortfall is 100–224 documents |
| **R-fail** | the failure count may not increase | a stage that raises the mean while reintroducing failures has not worked |
| **R-tail** | no document may drop by more than 10 points | catches a stage that trades many small losses for a few large wins |

> **R-tail's threshold is BELOW the measured noise floor and is not currently sound.**
> Found 2026-08-04. Between the two `jubarte-rust` runs, **nine documents moved with
> byte-identical input DOCX**, identical `score_config` and an unchanged oracle — one of
> them by **+12.75**, above R-tail's own 10-point rule. Both runs are outside the
> `soffice`-kill window, so it is not that.
>
> **Consequence: an R-tail trip at 10 points is not by itself evidence of a regression.**
> Until the floor is re-measured and the threshold set above it, every R-tail trip must
> be checked against the noise population before it is treated as real. The trip recorded
> in [reviews/stage1-measured-impact.md](reviews/stage1-measured-impact.md) survives this
> test comfortably — −47.03, nearly 4× the floor, with a diagnosed cause — but it survives
> *on that margin*, not on the rule.
>
> This does not weaken C1; it means C1's numbers were set without measuring the
> instrument. Re-derive R-tail's threshold from `results/noise_floor.json` and state the
> floor alongside it.

A stage that trips any ratchet is **not complete**. It is either fixed or reverted; it
is never accepted with a note. Targets are restated as **net** figures after each stage,
never gross.

**Deliberate exception.** A stage may trip R-perfect or R-92 *if and only if* the
tripping documents are individually enumerated in the stage's report with a stated cause
and the net effect on all three targets is still positive. Silence is not permitted; the
enumeration is the price of the exception.

## C2 — The census checkpoint (fixes convergent gap 2)

**The defect.** Stage arithmetic is computed on a frozen baseline that earlier stages
mutate. ast's A1 pool sits *inside* A2's ≈50 cluster. rust's R1 attacks precisely the
failure mode that dominates R2's cluster, so R2's landing table is stale before R2
starts. No plan re-measures between stages.

**The contract.** After every stage, before the next stage's arithmetic is trusted,
recompute and record:

- the ≈50 cluster: membership and size (documents in [40,60));
- the above-92 count and the shortfall to 382;
- the near-miss pool [90,100) and how many of it sit at or below 92;
- the perfect count;
- the four ratchet outcomes from C1.

**No stage may cite a number from a previous census.** If the census shows a stage's
input pool has changed by more than 10%, that stage's sizing table is void and is
recomputed before work starts. Stage tables in the plans are **entry-condition
estimates, not commitments** — they were all computed against the 2026-08-04 baseline
and every one of them expires at the first census.

## C3 — Failure branches and exit criteria (fixes convergent gap 3)

**The defect.** The near-miss stages (L4/R4/A4) each carry an honest-risk paragraph. The
cluster stages (L2/R2/A2), which carry *more* — both the mean and the median — carry
none. The stages worth the most had no "this didn't work" path.

**The contract.** Every stage declares, before it starts, three numbers:

- **Target:** what it is expected to deliver.
- **Floor:** the minimum below which the stage is declared failed.
- **Timebox:** after which it is declared failed regardless of progress.

Default floors, binding unless a plan overrides them explicitly:

| stage class | floor |
|---|---|
| ≈50-cluster lift | ≥ 75% of the cluster lands **above 92** (not at 90 — see the landing-point tables) |
| sibling transfer | ≥ 1 repair demonstrated end-to-end on a named document |
| style workstream (S) | ≥ 50% of the style-family fixtures above 92 |
| near-miss closure | the stage's stated conversion rate |

**On hitting the floor without hitting the target**: bank the partial gain, run the
census, and re-plan the remaining shortfall against the *new* baseline. Do not continue
the stage on momentum, and do not silently move the target.

**On missing the floor**: stop the stage, report it as failed, and re-examine whether
the target is reachable at all before spending more. A stage that misses its floor is
evidence about the target, not just about the stage.

## C4 — Workstream S has an owner (fixes convergent gap 4)

**The defect.** All three plans say "shared — implement once, see Plan 1". Plan 1 never
claims it. Three plans deferring to a fourth thing that does not exist is how a sized
contribution silently becomes zero.

**The contract.**

- **Owner: Plan 2 (jubarte-rust).** Style-chain resolution is implemented against rust
  first, because rust's lever-B sizing (+5.51 median) is the largest of the three.
- **Engine of record: jubarte-rust.** The implementation lands there and is then ported.
- **Deadline: if S has not landed in rust before Plan 1 or Plan 3 reaches its own style
  stage, that plan implements its own copy and records the divergence.** No plan blocks
  on S.
- S's contribution is a **dependency, not a bonus**, in every plan that cites it. If S
  does not land, the citing plan's median arithmetic is short by the cited amount and
  must find it elsewhere or declare the target missed.

## C5 — Stage 0: build the diagnostics the plans presuppose (fixes convergent gap 5)

**The defect.** Four stages across the three plans depend on two tools that are
presupposed and never built, scheduled, or owned:

- the **lens partition** (Plan 1 Stage L1), cited by R2 and A2;
- the **residual-ink cause classifier** (Plan 1 Stage L4), cited by R4 and A4.

**The contract.** These are Stage 0 of the whole programme. Nothing else starts until
they exist, because every downstream stage is specified in terms of their output.

**S0.1 — cluster lens partition.** For a given run, take every document in [40,60) and
partition by the functional invariants (`accept(candidate) == next`,
`reject(candidate) == base`) into: both hold / reject only / accept only / neither.
Emits a per-document classification plus a summary table.

> **Gate semantics — unjudgeable documents are excluded from the denominator.**
> Surfaced during implementation and adopted, because it decides whether the L1 gate
> can fire falsely.
>
> A **blind** pair (base text == next text) satisfies *both* invariants even for a
> candidate that emits nothing at all. Filing blind pairs under BOTH_HOLD would inflate
> the exact fraction the gate reads and manufacture a **false STOP_FIX_SCORER** —
> halting the programme to fix a scorer that is not broken. Symmetrically, a crashed
> lens run filed under NEITHER would invent an engine defect that does not exist.
>
> So blind, partial and errored documents are carried in a separate `unjudged` set and
> excluded from the gate's denominator, which counts **judged documents only**. This
> matches the existing house rule in `lens_health.py`, where `_functional_ok` already
> returns `None` for blind and partial rather than a verdict.
>
> This is the D3 disease in miniature — our own measurement reporting a defect that is
> ours, not the subject's — and the gate is precisely where it would have done the most
> damage.
>
> **Threshold direction:** the plan says bucket 1 must *exceed* ~15% to stop, so the
> comparison is strict and **exactly 15% proceeds**. The threshold is written
> approximate; treating the boundary itself as a stop would invent precision the
> contract does not claim.
>
> **Known limit of the real-data check:** the 166-document count for
> `019fcc6f` reproduces, but it does **not** pin the half-open convention — that run has
> zero documents scoring exactly 40.0 or 60.0, so the count is identical under
> `[40,60)`, `(40,60)` or `[40,60]`. The boundary is pinned by synthetic tests only. A
> future corpus with a document at exactly 60.0 would be the first real test of it.

**S0.2 — residual-ink cause classifier.** For a given document, diff the candidate
render against the oracle render, isolate the largest residual ink region, and attribute
it to a cause class. Emits a per-document cause label and a frequency table over any
document set.

**S0.3 — ratchet + census runner.** Implements C1 and C2 as a single command that takes
two runs and emits the four ratchet outcomes plus the five census figures.

**S0.4 — holdout gate.** Implements C6.

## C6 — "Done" is decidable (fixes convergent gap 6)

**The defect.** Every plan ends with "sealed 40-pair holdout once, at the end" and never
says who seals it, what score passes, or what happens when the holdout disagrees with
the 763-document ITT result. After four stages there was no criterion for accepting or
rejecting the outcome.

**The contract.**

- **Construction and sealing.** The 40 pairs are the existing sealed holdout; the gate
  records the manifest checksum with the result so a silently-changed holdout is
  detectable. The holdout is run **once per engine per programme**, not per stage —
  running it repeatedly converts it into training data and destroys the only
  overfitting check we have.
- **Pass threshold.** The holdout passes if its mean and median are each within
  **5 points** of the same engine's ITT figures on the 763-document corpus. It is not
  required to *hit* the targets — 40 documents is too small — it is required to be
  *consistent* with the corpus result.
- **Divergence branch.** If the holdout falls more than 5 points below the ITT figures,
  the programme's gains are declared **corpus-specific and not generalised**. The ITT
  numbers may still be published, but only alongside the holdout figures and that
  statement. This is the honesty clause; it is not optional and it is not negotiable
  after seeing the number.

## C8 — An XML diff is not evidence until it survives a render

Added 2026-08-04, after **nine** hypotheses died in a single day across four sessions.
This is the cheapest clause in the contract and it would have saved most of that day.

**The defect.** Every session, mine included, diagnosed a defect by finding a real
difference in the OOXML and reasoning about what it must do to the render. Every one of
those diagnoses was wrong. The benchmark scores a LibreOffice render against a
LibreOffice render, and a correct, schema-relevant, Word-visible XML difference routinely
moves **zero pixels**.

The nine, so nobody re-derives them:

| hypothesis | how it died |
|---|---|
| `color_sim ≈ 0` is an independent 13.5-point lever | collinear with alignment: ssim>0.99 → color_sim 0.9995 |
| style-resolved paragraph spacing drives the drift | cumulative delta **median 0 twips** |
| page geometry (`sectPr`) differs | 15/46, all default-value serialisation, zero layout effect |
| dropped headers/footers shift the body origin | 57.8% of cluster, but ≥90 reference drops them at 41.4% |
| list numbering is *the* cluster cause | 2.6× enriched, but no within-cluster discrimination |
| rust regenerates `theme1.xml` with different fonts | fonts preserved **390/390** |
| section-property merge policy is wrong | Word takes the revised side 88%; so do we |
| `normalize_incomplete_spacing` rule 2 | 7 documents, **0.000 delta**, A/B'd |
| dangling `numbering.xml` style refs | repaired **7 → 0**, **0.0000 delta** on all 763 |

**The contract.**

1. **No mechanism may be proposed as a cause, or sized in a plan, without an A/B
   attached.** Both arms built from **one commit**, so the mechanism is the only variable.
2. **Size against the full 763, never a cluster sample.** A hand-picked cluster sample
   over-represents movers by roughly 2×: a 21-document A/B read **+3.64** mean where the
   corpus read **+0.50**. Sampled deltas are an upper bound, not an estimate.
3. **A flat score is not automatically a failed fix.** It may be a Word-validity repair
   the benchmark cannot see (C9). Decide which before reverting — I nearly reverted a
   correct fix on this confusion.

## C10 — A provenance control is only valid at the moment of use

Added 2026-08-04 after the programme's **third** D5 split-brain in one day.

**The defect.** Checking which build you have, and then using that build, are two events.
Anything can happen between them on a shared machine — and did. A session ran
`resolve_local_version` at some point before 17:31:25 and got `fcea02da49f4`; another
session legitimately rebuilt the shared dist **at 17:31:25**; the first session generated
its probe artefacts **at 17:32:05**. **Forty seconds.** Everything downstream was
attributed to the wrong engine, and the conclusion drawn — "workstream S is already in
the baseline, the plans are double-counting it" — would have stopped work on the only
lever measured to deliver anything.

**The contract.**

1. **Stamp the version at generation time and carry it with the data.** Never check once
   and trust it for a session. A control taken before the work describes the artifact as
   it was, not as it is.
2. **A vendored dist that is a symlink outside the repo is not pinned.**
   `utils/jubarte/jubarte-wasm` points into `~/temp/T/jubarte-redlines`, so a branch
   switch in the engine repo silently changes what the bench runs. Treat any such run as
   unpinned until the artifact itself is hashed.
3. **When a measurement is invalidated, bound the blast radius rather than discarding
   everything.** The retraction above was made useful by establishing that
   `word/document.xml` is byte-identical between the two builds on 197/197 — so
   `document.xml`-derived results stood and only `styles.xml`-derived ones needed
   relabelling. Partition results by which part they read.

The three instances so far: the docxodus "9.0.0" run that executed 7.0.0; the
`jubarte-wasm` pin that recorded four engines as `0.1.0` (fixed, `fafe4aad`); and this
one. **D5 is not an occasional accident in this programme — it is the default failure
mode of a shared checkout with rebuildable vendored artifacts.**

## C9 — The benchmark cannot price Word validity, and must say so

**The defect.** Our oracle renders through LibreOffice. Schema validity and Word-repair
behaviour appear nowhere in a pixel score. Confirmed twice from different engines and
different defect classes, both scoring exactly zero: the TS `numbering.xml` style-ref
repair (7 → 0 dangling, 0.0000 across 763) and the Rust `numPr` child-order plus
`tblGridChange` author/date fixes (invalid 103 → 93, score delta 0.000 on the 29
documents whose bytes changed).

**The contract.**

- **Validity work is judged on the validity census, never on score.** See
  [reviews/validity-census.md](reviews/validity-census.md).
- **The census is published alongside the score table**, not in an appendix. It is the
  only evidence on a dimension the score cannot reach.
- **`55/504` — invalid output from clean input — is the figure that isolates us** and the
  one to drive to zero. Word's own comparison output is invalid on **49/504 (9.7%)**, so
  *match Word* and *be schema-valid* are different targets; where they conflict, the
  governing standard is **Word valid** — opens in Word with no warning, error, or repair
  offer — not the XSD.

Whether the oracle should be Word rather than LibreOffice is the largest open question in
the programme and is **not actionable unilaterally**: switching it invalidates every
recorded score.

## C7 — What none of this fixes

The reviewers converged independently on a blind spot the machinery above does not
address: **the plans are written in score-space, not capability-space.** They describe
clusters to lift and bands to convert without inspecting the engines that produce the
distribution.

The sharpest form of it, from the Plan 1 reviewer: lossless's conservatism may be *the
same property* that produces its best-in-bench page fidelity, so buying the median may
require spending the non-damage invariant the plan treats as banked. The Verification
sections watch for overfitting to the pixel scorer and are blind to that inverse
failure.

**Partial mitigation, and it is only partial.** C1's R-92 and R-tail ratchets will
*detect* a marking-for-fidelity trade after the fact, because degraded documents show up
as ratchet trips. They will not *predict* it, and they cannot tell us whether an engine
is architecturally capable of the repair being asked of it.

Recorded here rather than solved, so that a stage failing its floor is read as possible
evidence of an architectural limit and not merely as a fix not yet found.

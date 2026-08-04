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

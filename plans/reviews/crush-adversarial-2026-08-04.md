# Adversarial review of the three jubarte plans (crush / ZAI GLM)

Dispatched 2026-08-04 against plans at commit `3e7f2de5`. The reviewer prompt
was deliberately one-sided: assume the plan is INCOMPLETE and prove it; a report
that the plan is thorough is a NULL RESULT. Structural scope only — the reviewers
were forbidden from re-deriving numbers, because the arithmetic was verified
separately (and one error was found and fixed: see the correction boxes in each plan).

Raw output, unedited.

---

# Plan: jubarte-lossless

## GAPS

- **TITLE: Stage L2 — the stage that buys both targets — has no body**
  - **WHAT IS MISSING:** Any implementation. L2 is the sole owner of the +3.98 mean and the entire +13.47 median, yet its content is a stub: "Sub-work, ordered by the L1 partition," and the sub-work is never written. There is no mechanism, design, or even hypothesis for how 166 documents move from ≈51 to above 92.
  - **WHY IT BREAKS THE PLAN:** Derails Stage L2, which the plan itself declares load-bearing for two of three targets. A plan whose central stage is a forward reference to an unfinished diagnostic is not a plan; it is a todo list with arithmetic attached.
  - **MINIMUM FIX:** Require L2 to state at least one concrete lift mechanism per L1 bucket (with the code path it touches) before the plan is approved, or mark the plan as two-phase with L2 explicitly unfunded until re-planned.

- **TITLE: No failure branch for L2, whose arithmetic assumes 166/166 conversion**
  - **WHAT IS MISSING:** Any "this didn't work" path for the stage carrying both targets. The median table requires *all* 166 cluster documents to land above 92 — including the bucket L1 itself labels "the output is paint," which may be unlifttable by definition. A partial lift (say 120/166, or everything landing at 90) misses the median, and the plan never says what happens then. L4 gets an "honest risk" paragraph; L2, which is worth more, gets none.
  - **WHY IT BREAKS THE PLAN:** Derails Stage L2 and the Verification stage: a partial success will be indistinguishable from plan completion until the final number, with no pre-agreed re-plan trigger.
  - **MINIMUM FIX:** Add an exit criterion to L2 (e.g., ≥150 of 166 documents above 92, else re-plan the median target) mirroring L4's honest-risk clause.

- **TITLE: The median is accounted twice under two incompatible ledgers**
  - **WHAT IS MISSING:** Any reconciliation between Stage L3's sizing ("lever B … +3.47 median") and Stage L2's lift table, which already credits the cluster lift with moving the median from 78.53 to 93.00. The plan never states whether L3's contribution is *inside* L2's cluster arithmetic or *additional* to it.
  - **WHY IT BREAKS THE PLAN:** Derails Stages L2/L3 sequencing: if additive, L2's table is wrong and the plan over-claims; if inside, L3 alone cannot deliver L2's median and the remainder of the lift is unowned work that appears nowhere.
  - **MINIMUM FIX:** State explicitly that lever-B sizing is a subset of the L2 cluster lift (or show the additive arithmetic), and restage accordingly.

- **TITLE: Shared workstream S is unowned, unbounded, and uncoordinated**
  - **WHAT IS MISSING:** An owner, a target layer, an interface contract, and any sequencing against Plans 2 and 3 for the style-chain work. "Implement once, in whatever layer all three engines can consume" is a coordination requirement with zero mechanism: no decision recorded, no integration point named, no fallback if Plans 2/3 stall or schedule it differently.
  - **WHY IT BREAKS THE PLAN:** Derails Stage L3, the largest *sized* median contribution (+3.47). Cross-plan "implement once" work without an owner is the classic way that contribution silently becomes zero.
  - **MINIMUM FIX:** Name one owner and one engine of record for workstream S, with a deadline after which Plan 1 implements its own copy.

- **TITLE: L1's outcomes route to work that exists nowhere in the plan**
  - **WHAT IS MISSING:** Both branches past the gate. If bucket 1 exceeds ~15%, the plan says "stop and fix the scorer first" — unowned, unbounded, and a scorer change invalidates every baseline number (77.02 / 78.53 / 142) and every target in the document, with no step to re-derive them. If buckets 2/3/4 dominate instead, the plan has no design for missing insertions, dropped deletions, or inert output — L3 covers style inheritance only.
  - **WHY IT BREAKS THE PLAN:** Derails Stage L1's gate: every outcome the gate is designed to detect sends the plan somewhere it does not go.
  - **MINIMUM FIX:** Add one sentence per branch: scorer-fix triggers a re-baseline of all targets before L2; non-style buckets get named follow-on stages or are declared out of scope with the targets re-sized.

- **TITLE: L4 depends on a diagnostic that does not exist, with no budget cap**
  - **WHAT IS MISSING:** Any stage that builds the cause-classifier L4's method assumes: "diff the candidate render against the oracle render and classify the single largest residual ink region … spacing, pilcrow properties, list start values." The bench scores pixels against an oracle; nothing established here attributes residual ink to OOXML causes. The classifier is presupposed, never scheduled, and L4's "own iteration budget" is stated with neither size nor exit condition.
  - **WHY IT BREAKS THE PLAN:** Derails Stage L4 — the *only* stage that reaches the perfect-count target (+58). Its 43% conversion estimate rests entirely on an unbuilt tool plus an unbounded loop.
  - **MINIMUM FIX:** Add a bounded sub-stage to build (or name the existing) residual-region classifier, and cap L4's iteration budget with an explicit stop point feeding the honest-risk outcome.

## BLIND SPOT

The plan's framing — "the hard half (not damaging the document) is done; the deficit is in the redline itself" — treats lossless's conservatism as a banked asset and its under-marking as an independent, additive defect. That framing forecloses the one hypothesis the plan never examines: that the engine's cautious diffing is *the same property* that produces its best-in-bench page fidelity, so that buying +13.47 median may require spending the very non-damage invariant the plan assumes is untouchable. Consequently every stage is expressed in score-space (move 166 documents here, convert 58 there) rather than capability-space: the plan knows where score mass sits but never what the engine mechanically refuses to do, which is precisely why its central stage has no body. No stage measures or gates the marking-vs-fidelity tradeoff, and the Verification section watches for overfitting to the pixel scorer while remaining blind to the opposite failure — an engine change that raises redline credit and quietly degrades the document preservation the whole plan rests on.

---

# Plan: jubarte-rust

## GAPS

- TITLE: All target arithmetic assumes zero regression; nothing protects the 158 existing perfect scores
  - WHAT IS MISSING: Every table in the plan computes each stage against the frozen baseline as if all other documents stand still. There is no invariant anywhere stating that documents currently at 100 must stay at 100, no per-doc delta review, and no regression budget. The perfect-count math (158 + 42 = 200) is gross, not net: every document Stage R1's invasive geometry port knocks from 100 to 99 raises the R4 conversion requirement by one, silently.
  - WHY IT BREAKS THE PLAN: Stage R4 — its 28% conversion rate is only "the most achievable in the family" if the starting 158 is intact; the same applies to the mean/median tables in Stage R2, which assume no currently-high document drops.
  - MINIMUM FIX: Add a per-stage gate that fails the stage if any document scoring 100 at baseline falls below 100, and recompute the +42 requirement as a net figure after each stage.

- TITLE: Stages are computed on a frozen baseline, but Stage R1 rewrites the population Stage R2's arithmetic is built on
  - WHAT IS MISSING: R1 ports page-geometry preservation into rust before R2 runs. Rust's ≈50 cluster is, by the plan's own diagnosis, predominantly "marked correctly, rendered wrong" — exactly the failure mode R1 attacks. So after R1, the 197-document cluster's size, composition, and landing-point table are stale. No step re-measures the cluster between stages, and no statement says whether R2's numbers are pre- or post-R1.
  - WHY IT BREAKS THE PLAN: Stage R2 — its 90/93/95 table and the entire median purchase are asserted for a population that a prior stage has already mutated.
  - MINIMUM FIX: Insert a mandatory census checkpoint after every stage that recomputes cluster counts and the above-92 shortfall before the next stage's arithmetic is trusted.

- TITLE: R2 and R4 borrow diagnostic tooling from Plan 1 that this plan never builds
  - WHAT IS MISSING: R2 opens with "run the same Stage L1 lens partition first" and R4's method is "as Plan 1 Stage L4: classify the largest residual ink region." Neither the lens partition nor the residual-ink classifier is built, scheduled, or even listed as a dependency with an owner in this plan; there is no branch for the case where Plan 1 has not delivered them.
  - WHY IT BREAKS THE PLAN: Stages R2 and R4 — the two levers carrying the median and perfect targets cannot start; the plan has no critical path of its own.
  - MINIMUM FIX: Add an explicit Stage R0 that either builds both diagnostics or records a sequencing contract with Plan 1 naming deliverables and a handoff date.

- TITLE: No failure branch on either lever that carries the median
  - WHAT IS MISSING: The plan names its own cliff — lifting the cluster to 90 yields median exactly 90.00 and misses the target — then provides no contingency for landing at or below 90, no partial-lift model if only part of the cluster responds, and no fallback that tops up the shortfall from R3's +5.51 or R4's 25 convertible documents. Likewise R1 has a guard (skill_median must not fall) but no branch for when the guard trips or the 19 documents yield nothing portable.
  - WHY IT BREAKS THE PLAN: Stages R1 and R2 — the median target (+14.05, the hardest of the three) has no "this didn't work" path at the exact two stages responsible for it.
  - MINIMUM FIX: Define per-stage exit criteria (minimum above-92 conversions for R2, a no-result declaration for R1) and a pre-agreed fallback order for covering a median shortfall.

- TITLE: Shared workstream S is referenced by three plans and owned by none
  - WHAT IS MISSING: R3 says "shared with Plans 1 and 3 — implement once, see Plan 1," but no plan is named as owner, no sequencing exists among the three, and "lever B," which carries R3's entire sizing (+1.86 mean, +5.51 median), is defined only in Plan 1. Three plans each deferring to Plan 1 is the classic unowned-cross-plan-work hole.
  - WHY IT BREAKS THE PLAN: Stage R3 — its contribution is booked as available headroom (and is the only named reserve if R2 under-delivers on the median) yet its delivery is nobody's committed work, with no timebox or exit condition.
  - MINIMUM FIX: Name a single owning plan for workstream S, define lever B inline or by binding reference, and state here whether R3's numbers are a dependency or a bonus.

- TITLE: "Done" is undefined — the holdout gate has no procedure, no threshold, and no disagreement branch
  - WHAT IS MISSING: Verification ends with "sealed 40-pair holdout once, at the end," but never says who constructs or seals the 40 pairs, what score constitutes a pass, or what happens if the holdout contradicts the 763-document ITT result. No stage has a timebox or owner either, so the plan has no exit conditions anywhere except R4's one-sentence "re-examine the target."
  - WHY IT BREAKS THE PLAN: Verification — after four stages of work there is no decidable criterion for accepting or rejecting the outcome, so the plan cannot terminate.
  - MINIMUM FIX: Specify the holdout's construction and sealing step, a numeric pass threshold mirroring the three ITT targets, and an explicit branch for holdout/ITT divergence.

## BLIND SPOT

The plan's organizing metaphor — "rust is the mirror image of lossless" — frames the entire problem as a delta between two sibling engines scored on the same snapshot, and that framing makes three things invisible. First, it treats the four stages as independent levers pulled on a fixed population of documents, so it literally cannot represent interference: a document R1 lifts leaves R2's cluster, R3's style fixes move documents across every threshold in both directions, and each stage's arithmetic is computed as if the previous stage never happened. Second, the envelope statistic (best-of-both-engine per document already clears two targets) is presented as evidence that transfer is feasible, when it is only a ceiling that assumes every one of lossless's wins is individually portable into rust — the lossiest assumption in the plan, and the framing presents it as an encouraging floor. Third, both sub-metrics in the mirror diagnosis — skill and page geometry — are artifacts of one pixel-scoring pipeline against one Word-markup/LibreOffice-render oracle; by taking that decomposition as neutral ground, the plan cannot see that "port what lossless does to preserve page geometry" may mean porting markup that merely renders closer to the oracle rather than markup that is more faithful, so the very metric used to prove R1 worked could reward the wrong fix.

---

# Plan: jubarte-ast

## GAPS

- TITLE: Stage lifts are computed on a fixed baseline and the stages' pools overlap; nothing sums to the target
  - WHAT IS MISSING: Any cumulative accounting. Stage A1's pool is defined as `ast ≤ 60`, which sits inside Stage A2's 255-document ≈50 cluster, yet no overlap analysis exists. Worse, A2's own table (land at 93 → mean 84.01, median 93.00) already clears both retained targets with everything else held constant — so the plan never explains what A0/A1/A3 add, whether stages are additive or alternative, or how A3's "+2.03 mean" sizing survives once A2 moves 255 documents.
  - WHY IT BREAKS THE PLAN: Derails Stage A1 and A2 jointly: if A1 lands first it mutates A2's cluster and voids the table; if A2 alone suffices, the plan's sequencing is unfalsifiable and progress cannot be attributed.
  - MINIMUM FIX: Publish a per-stage lift budget with explicit pool-overlap analysis and a cumulative reconciliation that shows stage sums reaching each target.

- TITLE: Stage A1's "transfer" has no mechanism, and the largest deficit rides entirely on it
  - WHAT IS MISSING: Any explanation of *how* a sibling's working result becomes an ast fix — no root-cause check that ast's 77 documents fail for reasons lossless/rust already solved, no sample audit, no architectural portability argument, and no branch for "not transferable." Page geometry, ast's worst sub-metric (52.06), is routed exclusively through this assumption.
  - WHY IT BREAKS THE PLAN: Derails Stage A1 — the stage the plan calls its single highest-yield — and starves A2, which expects geometry-driven "rendered wrong" repairs to dominate the cluster.
  - MINIMUM FIX: Root-cause a stratified sample of the 77 documents and demonstrate at least one transferred repair end-to-end before committing A1's yield claims.

- TITLE: No no-regression ratchet anywhere in the plan
  - WHAT IS MISSING: Every lift table assumes zero erosion of documents already scoring well; no stage guards the 158 documents above 92 or the 84 perfect ones against regression from A1/A2/A3 engine changes. Verification gates only on failure count ("a stage that raises the mean while reintroducing failures has not worked") — score regressions are unmonitored, and the median margin is thin.
  - WHY IT BREAKS THE PLAN: Derails every stage silently: engine edits that lift the cluster while pushing currently-high documents below 92 defeat the median target with no gate to catch it.
  - MINIMUM FIX: Add a per-stage gate that no document currently above 92 (or at 100) may drop, enforced on every ITT re-run.

- TITLE: Stage A0 stops at classification; repair is unowned and the 9 returning documents are unpriced
  - WHAT IS MISSING: A remediation step — classification into engine-side vs harness-side produces no score change by itself, and neither outcome has a fix branch. Nor does the plan compute what happens when 9 newly scoring documents re-enter the arithmetic: cluster membership, the A2 landing tables, and the median position were all computed with the failures in place.
  - WHY IT BREAKS THE PLAN: Derails Stage A0's handoff into A2: the "do this first" stage can end with a classification report and nothing fixed, and A2's tables may be stale the moment failures reach 0.
  - MINIMUM FIX: Extend A0 with explicit repair sub-steps per classification and recompute A2's tables after the 9 documents score.

- TITLE: No stage has a failure branch; under-delivery is unplanned
  - WHAT IS MISSING: Any "this didn't work" path: A2 lifting the cluster only to 85–90 (median stalls at the landing value), the Plan 1 L1 lens partition contradicting the "rendered wrong" expectation, the final 40-pair holdout missing target, or A4's 60% conversion proving unreachable. Verification defines success criteria but no response to missing them.
  - WHY IT BREAKS THE PLAN: Derails Stage A2 first — the stage with the "thinnest margin of the three" and least room to under-deliver has precisely no fallback defined.
  - MINIMUM FIX: Attach to each stage an explicit abort/fallback condition and the decision it triggers.

- TITLE: Unowned dependencies and unbounded work: Plan 1 coupling, an undated scope decision, and an open-ended Stage A4
  - WHAT IS MISSING: A2 requires Plan 1's Stage L1 lens partition and A3 is Plan 1's workstream S — neither sequenced against Plan 1's schedule, owned here, nor backed by a fallback; A1's sibling pools are pinned to one run while `corpus_revision` may shift them. The perfect>200 target is simultaneously asserted, recommended-against, and "pending your decision" with no owner deadline — and Stage A4, the only stage serving it, is self-described as open-ended with no timebox, exit condition, or evidence of attainability.
  - WHY IT BREAKS THE PLAN: Derails Stage A4 and plan executability: work cannot start until an unowned decision lands, and if kept, A4 is unbounded by construction.
  - MINIMUM FIX: Sequence the Plan 1 dependencies with named owners, force the scope decision to a dated owner, and give A4 a timebox and kill criterion or cut it.

## BLIND SPOT

The plan treats the score distribution itself as the object of work — clusters to lift, bands to convert, pools to harvest — and never once examines the engine that produces the distribution. There is no stage asking how ast actually renders page geometry, why it diverges from its siblings at the code level, or whether its pipeline can even represent the repairs being "transferred" into it. Every stage is specified in terms of score movement rather than engine change, so the plan is structurally unable to see the possibility that its worst deficit is architectural: that sibling fixes may be unportable not because they haven't been found but because ast cannot host them, and that "we haven't located the fix yet" may be indistinguishable from "this engine cannot reach target." Its own arithmetic reinforces the illusion — a single bulk lift clears two targets on paper, making scores look like a dial to turn rather than the emergent outcome of code that has never been inspected.

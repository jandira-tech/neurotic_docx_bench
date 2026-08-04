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

## Part 2 — jubarte-rust. Status: **run in flight.**

`bench run --only jubarte-rust --rerun --no-gate` is executing against
`ENGINE_COMMIT.txt = 1be1fcd060ce0d8e2a1b0f91df618d8ec651e3ba`, the workstream S commit.
The pin is verified against the branch head before the run, so the provenance question
answered above for TS is answered in advance here.

Unlike the TS fix, this one has a **measured target population**: 136 of 597 pairs carry
a live styleId collision, and those 136 score mean **59.7** against **79.4** for the
rest. If the fix works, the movement should be concentrated there — so the test is not
just the headline delta but whether *those specific 136* moved.

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

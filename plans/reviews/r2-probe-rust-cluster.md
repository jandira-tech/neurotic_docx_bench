# Stage R2 probe — jubarte-rust does NOT share lossless's defect

Executed 2026-08-04 against run `019fcc5d-34e6-7029-95d9-463d5513fe7c`. **No engine
code was written.** The stage was specified to measure before implementing, the
measurement disqualified the planned fix, and it stopped there. Probe artefacts under
`~/temp/T/r2-probe/`.

## Fidelity controls

- dist binary hashes to `jubarte-rust@fcea02da49f4` — byte-identical to what run
  `019fcc5d` recorded.
- cluster `[40,60)` = **197** documents, median **50.64** — matches Plan 2 exactly.
- all 197 regenerated plus a 307-document ≥90 control, using the same argv the bench
  generator uses. Oracle coverage 197/197 and 307/307.

## The structural axis L1 used

| | rust cluster | rust ≥90 control | lossless BOTH_HOLD |
|---|---:|---:|---:|
| ins chars cand/oracle, median | 1.000 | 1.000 | 1.000 |
| del chars cand/oracle, median | 1.000 | 1.000 | 1.000 |
| in-place (ins+del) paragraphs, cand vs oracle median | **1 vs 1** | 2 vs 2 | **0 vs 1** |
| cand has NONE where oracle has some | 25/197 (12.7%) | 6/307 (2.0%) | **69/124 (55.6%)** |
| cand has FEWER than oracle | 61/197 (31.0%) | 13/307 (4.2%) | 81/124 (65.3%) |
| cand emits more paragraphs than oracle | 44/197 (22.3%) | 6/307 (2.0%) | 64/124 (51.6%) |

rust's cluster matches the oracle on in-place count at the median. lossless's does not.

## Why the planned fix is disqualified

**The in-place deficit has essentially zero explanatory power inside rust's cluster.**
Score medians by group: NONE 50.23, FEWER 47.94, EQUAL 51.85, MORE 51.04; `ink_f1`
sits at 0.30–0.38 in every group.

- **53 of 197** match Word on in-place count, paragraph count **and** both volumes —
  and still score **52.25**.
- **46 of 197** have body text **byte-identical** to Word's oracle — and still score
  **52.29**, with `ink_f1` 0.398 and `color_sim` 0.000.

A document cannot be fixed by changing markup it already gets right.

## Pipeline control — the loss is ours, not the renderer's

Word's oracle DOCX re-rendered through the same `soffice` path scores **100.00**
(`ink_f1` 1.000) against the stored oracle PDF, on all 8 tested. The renderer is
neutral. This is the D3 check and it clears.

## What rust's cluster actually is: cumulative vertical drift

Identical text, larger inter-paragraph advance, drift accumulating down the page
(0 / +16 / +64 / +96 px on page 1 of the exemplar); a 5-page oracle becomes 6 pages.
The scorer's own drift map: median **117.9 px**, p90 **476.3 px** at 144 dpi.

**Leading cause — style-chain resolution, which is Stage R3 / workstream S, not R2:**

| | cluster | reference |
|---|---:|---:|
| source pair defines a shared styleId differently | 117/194 (60.3%) | 15.7% |
| candidate resolves a shared styleId differently from Word | **148/194 (76.3%)** | 19.3% |

A 4.0× enrichment against the reference group.

## Plan impact — Stage R2 is re-sized and R2/R3 are not additive

R2 as written targets a mechanism present in **61 of 197** documents and worth roughly
**2 points where present** (47.94 → 51.85) — about **+0.16 ITT mean**, against a stage
whose arithmetic assumed lifting 197 documents above 92.

Plan 2's own warning was right and is promoted here to a finding:

> "rust's skill/page profile is inverted, so a ≈50 score is more likely to mean
> 'marked correctly, rendered wrong' here and 'rendered correctly, not marked' there.
> Different cause, different fix, same number."

**R2 and R3 are the same work.** They are not additive, and the median-target
arithmetic that leaned on R2 needs re-deriving once R3's real effect is measured.

# Word's Normal-spacing rewrite rule — derived, verified, shipped

**Date:** 2026-08-04. **Engine commit:** jubarte-redlines `0954519`
(`feat(compare): Word's Normal-spacing delta rule + one-sided-table anchor guard`).
**Method:** truth table over every corpus Word oracle → closed form → engine
reimplementation → full-corpus A/B. This is the C8 discipline end-to-end: no
mechanism was proposed until the render said so, and the rule was validated
against all 760 measurable pairs before one line of Rust changed.

## What was wrong

The scored rust baseline (`1be1fcd`) wrote the LIVE `w:spacing` of the output's
`Normal` style from a hand-fit case cascade (stored/dd/factory arms, constants
`160/278` and `0/240`). Corpus-wide comparison of the candidate's live Normal
spacing against the Word oracle's showed **44 of 760 pairs wrong**, in both
directions:

| candidate live | oracle live | n |
|---|---|---|
| none | after=0 line=240 | 9 |
| after=160 line=278 (factory) | none | 6 |
| none | after=160 line=278 | 5 |
| after=0 line=259 | after=160 line=259 | 5 |
| attribute-presence diffs (0 vs absent) | — | ~10 |

The exhibit that exposed it: `super_editor__basic_table_shading_d3212ffd ×
super_editor__basic_tracked_change_5a9ff724` — A stores Normal `200/276`, B
stores nothing, no docDefaults anywhere. Word's output Normal is **empty** (A's
old value in `pPrChange` only); ours carried a live synthesized `after=160
line=278`. LibreOffice reads the live value → every paragraph and table row
inflates ~1.75× vertically → the exact cluster signature (ssim high, ink_f1
collapsed). This is the mechanism behind the teammate's corpus-wide transition
table (`after cand=160/oracle=0` ×130, `line cand=278/oracle=240` ×104).

## The derivation

Features extracted per pair from the two INPUT stylesheets: A/B Normal stored
spacing, A/B docDefaults spacing, A/B Normal "structured" (any pPr/rPr content
net of change records). Grouping all 752 measurable pairs by those features:
**zero ambiguous groups** — the oracle outcome is a deterministic function of
the inputs. The closed form that emerges:

> Word rewrites Normal so **B's effective spacing survives under the output's
> (A's) docDefaults**:
> - `ctx(attr)` = A.docDefaults spacing attr, else app default
>   (`after=0, line=240, lineRule=auto`)
> - `b_eff(attr)` = B Normal stored attr, else B.docDefaults attr, else app
>   default — the cascade is **per attribute**, not per element
> - target = attributes where `b_eff ≠ ctx` over {after, line}; when `line` is
>   written, `lineRule = b_eff(lineRule)` rides along; an empty target clears
>   A's stored spacing (recording it in `pPrChange`)
> - gate: two completely bare Normals are left untouched even when docDefaults
>   differ (Word does not materialize dd into a style nobody shaped)

Validation of the closed form against the oracles: **751/752**. The per-attribute
cascade is what the old arms could not express — Word mixes sources within one
spacing element (B stored `line=259` + B dd `after=160` → live `after=160
line=259`) and omits attributes A's docDefaults already supply (live `line=276`
with **no** `after`, 12 oracles). The old `FACTORY_NORMAL_SPACING` (160/278) and
`EMPTY_B_SINGLE_LINE_NORMAL` (0/240) constants fall out as special cases: 0/240
is `b_eff = app defaults` under a non-default A dd, and 160/278 was B's own
docDefaults on the pairs that motivated it.

After reimplementation the ENGINE's live Normal spacing matches the oracle on
**758/760** pairs (was 716/760). The two remaining: one pair where neither
input has a Normal style at all (Word synthesizes explicit 0/240) and one
`invalid_list_def_fallback` pair — both logged, neither special-cased.

## The companion fix (block anchors)

`super_editor__sublist_issue × super_basic_table` (rust 54.48, lossless 100.00)
showed rust splicing B's inserted table into the middle of A's deleted
paragraph run by anchoring on EMPTY paragraphs. The engine already refuses
textless anchors when tables are on BOTH sides (M-TBL rule 3); the corpus
oracles show the same physics with one-sided tables (227 contiguous ins-first
replacement runs vs 23 interleaved, Word-wide). The guard now fires when
either side holds a table. Paragraph-merge pivot windows carry no tables and
are untouched (the PR #81 caveat).

## Measured effect (A/B, both arms from one commit each, date-normalized)

- Control: base arm reproduces the scored run's 801 artifacts **801/801**.
- Fix changes **58/801** outputs; 55 scored (3 have no stored oracle PDF).
- **Sum +453.96 → projected full-763 ITT mean +0.60.**
- Gains: +53.84 (43.30→97.14), +49.36 (50.64→**100.00**, new perfect),
  +46.48, +40.67, +32.68, +25.70 … 18 docs improve >1; above-92 4→7 within
  the changed set.
- Regressions: −7.71, −6.55, −4.49 (all M-TBL anchor-refusal cases where the
  fragmented layout accidentally overlapped better), then noise-level.
- Engine test suite: green before and after.

## What this is NOT

- Not corpus-fitting: the rule is a semantic statement about Word Compare
  (preserve B's effective appearance under A's docDefaults) with app-default
  constants from Word's own documentation; the corpus was used to FALSIFY
  candidate rules, and the winning rule has no per-pair branches.
- Not the whole cluster: the multi-page hard core (89 docs) is untouched by
  construction. This lever moves the single-page displacement class.

## Next levers (in order of evidence)

1. **lossless (TS) mixed-paragraph pPr**: on `file_83_file_84` (lossless 50.96,
   rust 100.00) Word keeps A's pPr LIVE with the paragraph mark marked deleted
   (`pPr/rPr/del`, pStyle=Title rendering large); lossless swaps to B's pPr +
   `pPrChange` and renders body-size. Word DOES emit document-level pPrChange
   on 363/828 oracles, so the rule is conditional — needs its own truth table
   (probably: mark deleted when the paragraph CONTENT was replaced, format-
   changed when content survived). This is the "in-place paragraph defect"
   (69/124 lossless cluster docs) from the plans.
2. The 2 unmatched Normal-spacing pairs above.
3. rPr (sz/rFonts) live-value analogue of the same rule — our exhibit's live
   rPr carried `Arial sz24` where the oracle's live rPr is empty; same
   delta-under-context shape, second truth table.

## Addendum — the lossless (TS) truth-table state (2026-08-04 late)

The mixed-paragraph rule for lossless is PARTIALLY derived. On oracle
paragraphs of pure replaced-in-place shape (del-text + ins-text, no equal
runs), aligned back to their input paragraphs by text:

| Word's choice | input pPr same | input pPr differs |
|---|---:|---:|
| paragraph mark deleted (A pPr live) | 86 | 152 |
| pPrChange (B pPr live) | 2 | 52 |

`chg` requires differing pPr (52 vs 2, as expected), but among differing-pPr
paragraphs Word still picks delmark 152:52 — the remaining discriminator is
NOT pPr equality, NOT paraId provenance (Word regenerates paraIds), NOT
adjacency to inserted marks, NOT live pStyle. Leading hypothesis: the
del/ins MARK-COUNT BALANCE of the containing replacement region (1:1 marks →
the mark survives with pPrChange; n:m → surplus A marks die as delmark).
Testing it needs replacement-region extraction around each paragraph — the
next build. Population at stake: lossless has 449 kind-sequence structural
mismatches vs the oracle corpus-wide, 343 of them scoring ≤92
(`/Users/arthrod/temp/T/r3/lossless_struct_mismatch.json`), and 107
single-page lossless failures have a PERFECT sibling. This is the dominant
lossless defect class.

Also measured while waiting: the AST engine's Normal spacing is nearly clean
(1/164) — its 69.83 is NOT the spacing bug; its structural match rate (130/164
kind-seq on the word_based manifest) is close to rust's (133), so its losses
are formatting-level or concentrated in the superdoc manifest. Needs a scored
run with per_doc to target (no ast row in bench.jsonl carries per_doc).

### RESOLVED — the mixed-paragraph discriminator (same evening)

The missing factor is REGION POSITION. Splitting every oracle body into
maximal runs of fully-changed paragraphs (no equal-text runs) and locating
each `pPrChange` paragraph within its region:

> **chg is the LAST A-origin item of its region: 283 of 287.** (4 interior
> exceptions, unexamined.)

So Word's rule for a replaced region of n A-paragraphs and m B-paragraphs:
the FINAL A-paragraph's mark survives, carrying B's final pPr live +
`pPrChange`(A's old pPr); every INTERIOR A mark is deleted (`pPr/rPr/del`)
with A's pPr left live; B's surplus marks are inserted. Lossless instead
pairs marks mid-region wherever its word-level LCS pivot lands
(file_83_file_84: pPrChange on the interior Title paragraph while the region
continues — renders body-size where Word renders the Title formatting, 50.96
vs rust's 100.00). The fix target in the TS engine is the pivot PLACEMENT:
mark survival must migrate to the region's final A-paragraph. Verification
population: the 449 kind-sequence mismatches, then the 107 perfect-sibling
single-page failures.

## SHIPPED — the lossless region-mark relocation (2026-08-05 early)

Implemented as `RelocateRegionMarkSurvival` in jubarte-first's WmlComparer
(engine commit `8f8ea7594`): interior pPrChange paragraphs flip to A's old
pPr live + deleted mark, exactly the 283/287 oracle rule. The first A/B
exposed the exception class — TWO high scorers destroyed (94.69→52.08,
95.09→61.90), both with the same signature: A's old pPr style-less and B's
live pPr carrying a pStyle (Heading1/TOC1). The oracles show Word SPLITS
those paragraphs (B's styled paragraph inserted whole, A's deleted
separately) rather than merging — a shape a mark flip cannot produce, so
the guard skips it. With the guard:

- corpus A/B (262 changed outputs, 154 with stored oracles):
  **net +153.8 → +0.20 corpus mean**, worst regression −3.3,
  +3 docs cross 92, one new exact-100 (63.05 → 100.00).
- lossless suite 752/0; the full-repo suite's 8 failures reproduce
  identically without the change (pre-existing, attributed by stash-rerun).

Official jubarte-final-lossless run in flight at dist
`jubarte-final@041a9bd0cbc3+git.8f8ea7594`.

### v3 spacing-guard — NULL RESULT, reverted (2026-08-05)

Extending the split-class guard to live-spacing-with-empty-old-pPr recovers
all five v2 regressions (+31.1 file_147, +15.9, +4.0, +1.8, +1.8) but breaks
three v2 winners (−27.1 file_116, −21.1 file_60, −8.1 exporttest):
**net −3.44 ≈ zero**. The spacing-flip population is a coin-flip the output
cannot call: token overlap between the flipped paragraph's del/ins text does
NOT separate the classes (0.17/0.0 vs 0.0/0.14). The discriminator lives in
Word's own word-level alignment (which cousins it merges), invisible
post-hoc. v2 ships and stands; the −31 stays as a known bounded residual
until the engine's word-LCS itself is aligned with Word's (the guard-stack
port). The TS working tree is reverted to the committed v2 (8f8ea7594).

## ast at the new dist (2026-08-05 03:00 run)

jubarte-ast (jubarte-final-native) at dist 041a9bd0cbc3: **ITT mean 69.83 →
70.24 (+0.41), median 68.64** — and the vendor's FIRST full row with per_doc
scores, so ast targeting is finally possible. The C1 gate reads FAIL from
its 374-shared-doc ratchet slice (75.04→74.85, −0.19) while the full ITT
moved up — mixed populations, both recorded.

Named residual: **file_8_file_9 renders unloadable** ("source file could not
be loaded", LibreOffice, deterministic) at this dist — a NEW failure (the
other 9 ast failures are unchanged from d99ccb5b3). Valid zip, parseable
XML; the defect is semantic. Not yet attributed (the ast path should not
touch the WmlComparer post-pass); needs an old-dist rebuild for a clean A/B.
Cost while open: one zero-filled doc ≈ 0.09 ast mean.

## The remaining gap, fully named (2026-08-05, end of cycle)

Refreshed perfect-sibling single-page target sets after tonight's ships:
**rust 72** (was 128 — 56 cleared), **lossless 97** (was 107), **ast 163**.
All three engines' residual losses trace to ONE theme — correlation that
diverges from Word's word-level alignment — wearing three faces:

1. **ast (163 targets, biggest win available)**: no cousin zip. On stamped
   cousins (file_101_file_102, 45.6 vs lossless perfect) Word pairs
   paragraphs positionally into mix paragraphs ('file_102101.docx',
   'Underline Text FormattingCalibri Heading 2 R…'); ast emits ins-all →
   del-all. The rust engine solved exactly this with the M126/M205/M75
   diagonal-zip + stamp machinery in lcs.rs. Port target:
   jubarte-first src/compare/correlate.ts. Most of ast's ~60 file_N targets
   and its 7.5-point gap to lossless (same bundle!) sit here.
2. **lossless (97)**: mid-region word-LCS pivots (partially fixed by the
   post-pass; the spacing coin-flip class needs the LCS itself to align —
   v3 null result proves post-hoc is exhausted).
3. **rust (72)**: the multipara-cell mis-pair (identical-heading pairing,
   H1 row flush) and the remaining docxodus-only wins.

Priority for the next cycle, by measured value: (1) ast cousin-zip port,
(2) lossless guard-stack port, (3) rust identical-heading pairing. The
truth-table method (derive from all oracles → validate → A/B → official)
is proven at 4-for-4 tonight and is the required workflow for each.

### ast port spec, exact (closing addendum)

file_101_file_102's oracle is NOT a blind diagonal zip: Word confettis the
stamped demos and then pairs SPECIFIC residuals — stamp line ↔ stamp line
(mix 'file_102101.docx'), title ↔ title on shared last-significant token
('…Demo': mix 'Underline Text FormattingCalibri Heading 2 R…'), body ↔ body
— leaving the rest pure ins/del. That is EXACTLY jubarte-redlines'
`stamp_residual_pairs` + `is_related_stamped_variant` machinery
(src/comparer/lcs.rs: RELATED_STAMP_MIN_BODY_TOKENS=40,
STAMP_CONFETTI_MAX_BODY_OVERLAP=0.55, tiers M75/M95/M96/M107/M114/M133/
M135), already corpus-validated on the rust side. Port target:
jubarte-first src/compare/correlate.ts `doLcsNoMatch` (the wholesale
revised-first branch at ~line 1560) — replace the fixed
ins-all/unk(A0,Blast)/del-all shape with confetti + residual pairing.
Population: most of ast's 163 perfect-sibling targets (~60 file_N + the
super_editor cousins). This is a faithful-port task of ~a day with the
truth-table method as the acceptance gate; it was NOT attempted in this
cycle to avoid shipping an untuned zip (rust's own history shows blind zip
regresses weak cousins — M126).

## SHIPPED — the ast stamped-cousin pairing (2026-08-05, second wind)

Ported rust's `stamp_confetti_then_replace` core into the ast engine's
`wholesaleUnrelatedWordShape` (jubarte-first `f9c71f0c`): stamp-line digit
confetti + residual pairing at rust's exact tier thresholds (M75/M95/M96 +
end-zip) + unconditional boundary fold. Corpus A/B against the official
jubarte-ast row: **174 outputs changed, net +1735 → +2.27 ITT corpus
mean**, 119 up / 12 down, above-92 in the changed set 1 → 39, gains to
+50.7 (48.97 → 99.66).

Second null result of the night, recorded: gating the boundary fold on
shared vocabulary (to rescue file_170_171's −40) is **net −899** — the
zero-overlap folds carry the biggest wins; Word folds the boundary pair
even with no common words. The unconditional fold ships; file_170_171
(−40) and file_59_60 (−29) stay as named residuals.

Official jubarte-final-native run in flight at dist
`jubarte-final@5bf73ce40d09+git.f9c71f0c`.

### Next ast exhibit, precisely cut (post-ship)

`super_editor__diff_after11 × diff_after16` (ast 44.4, rust perfect):
oracle = ins B-heading, ins B-TABLE, then del A's paragraphs — pure split,
ins-first. ast = MIX(A-para1 × B-heading) then dels then the table LAST.
Two known rules violated in one window: (a) Word splits rather than merges
at a styled (Heading1) boundary — the same split-class derived during the
lossless work; (b) inserted tables precede deleted paragraph runs (oracle
corpus 227 ins-first vs 23). Fix seam: ast correlate.ts doLcsNoMatch's
words+rows interleave — trace which branch fires, then apply ins-first +
styled-boundary no-merge. This is the first move of the next cycle.

### Styled-boundary discriminator — measured, single-feature INSUFFICIENT

Oracle-wide over all replacement regions containing both ins and del
paragraphs: P(split | first B-para styled) = 0.69 (84:37) vs
P(split | unstyled) = 0.44 (162:207). Real signal, not a rule — unlike the
Normal-spacing table (100%) and the region-end rule (283/287), split-vs-merge
needs multi-feature alignment modeling (boundary content overlap, run
lengths, Word's own word-anchors). That modeling pass — inputs aligned to
oracle regions with per-boundary features — is the specified centerpiece of
the next cycle. Do NOT ship a pStyle-only guard on this number.

### Next rust exhibit, precisely cut

`super_editor__anchor_images × annot2` (rust 44.1, lossless 100.00): rust
DROPS B's two leading inserted empty paragraphs before the inserted table —
oracle opens [p ins '', p ins '', tbl ins, del-run…], rust opens [tbl ins,
del-run…] with two fewer blocks. Two-line displacement of the whole page.
Same empty-paragraph-adjacent-to-table family as the ex1 between-tables
drop that the Row-aware guard fixed — this one at region START, so the
pMark-consumption happens in a different step_h/H1 walk. Method: re-add the
env-gated LCS trace, find the consuming branch, fix, A/B. rust has 72
remaining perfect-sibling targets; several in this family.

Trace analysis for the anchor_images exhibit (saves the next hour): the top
window is A=5 paras × B=[P,P,Table]. H4 flattens; the Row-aware guard
correctly voids the anchor in the [w×485 × wwR] window, but H1's zip then
pairs A's 485 CONTENT words against B's two EMPTY pMark words
(Words↔Words positional pairing), and the lone-pMark pivot inside those
table-free sub-windows merges B's empties into A paragraphs at positions 1
and 221 — they vanish as separate paragraphs. Two rules needed in
step_h/H1 (lcs.rs):
1. Never pair a pure-textless Words-group against a contentful one — the
   textless side is pure ins/del (safe for the PR #81 pivot windows, whose
   short side always has content).
2. Emission order: Word's oracle is [ins empties, ins Table, del A-run] —
   contiguous B-first. H1's branch 4 (lg Word && rg != Word → delete lg
   first) parks the table after the del-run; the fix must confine ins-first
   ordering to windows whose pairing was voided by rule 1, NOT change
   branch 4 globally (it is Word-verified on fixture f-4).
Both are A/B-able on the 72-target rust set in one cycle.

CORRECTION to the trace analysis: a textless-vs-contentful pairing rule
added to H1's zip does NOT change the exhibit's output — the empties are
consumed on a different path (H1's Words↔Words slot was not the consumer;
candidate suspects: H2's Para/Table walk, the defensive flush, or an
earlier produce-level merge). The edit was reverted unshipped (C8: an edit
that does not move its motivating exhibit does not ship). Next context:
re-instrument with a branch-labelled trace in step_h before re-attempting.

SECOND CORRECTION, decisive: with a fire-probe, the H1 textless rule DOES
fire (trace: `H1 iter lg[0]=Word rg[0]=Word lgTL=false rgTL=true` →
inserted(B-empties) pushed) — and the final document STILL lacks the two
inserted empty paragraphs. **The consumer is DOWNSTREAM of correlation**:
the produce/coalesce/finalize layer drops inserted bare-paragraph-mark
sequences (suspects: produce.rs coalesce_recurse or a finalize fixup that
strips empty inserted paragraphs adjacent to tables). The earlier
"H1 wasn't the path" reading was wrong in the opposite direction: H1 IS
reachable and fixable, but fixing emission is NECESSARY-NOT-SUFFICIENT
until the produce-layer drop is found. Hunt order for the next cycle:
grep produce.rs/finalize.rs for empty-inserted-paragraph elision, fix, THEN
re-apply the H1 rule, then A/B both together on the 72-target set.

DROP SITE LOCATED (produce.rs, CoalesceRecurse Step 1): atoms are grouped
by `(ancestor Unid, element type)` and the code **silently filters
empty-key groups** (`grouped.filter(|(k,_)| !k.is_empty())`; key built from
`ancestor_unids.get(level)` with `if u.is_empty() { return String::new() }`).
Inserted bare-paragraph-mark atoms from B whose ancestor unids were never
minted fall into the empty key and are DROPPED — B's two leading empty
paragraphs in anchor_images×annot2 die here even after H1 emits them as
Inserted. Fix path: `assemble_ancestor_unids` Phase B ("reverse walk,
minting missing") must cover inserted bare pMarks in flattened windows —
verify their ancestor_unids at produce time, mint when absent, THEN
re-apply the H1 textless-pairing rule, then A/B both on the 72-target set.
This chain (H1 emission + produce minting) is one shippable unit.

Phase B review: `assemble_ancestor_unids` DOES mint unids for every atom
(pPr atoms via `unid_or_mint` per ancestor; others borrow the following
paragraph's prefix with name-based share). So the empty grouping key is NOT
missing unids — it is a LEVEL mismatch: the Step-1 key reads
`ancestor_unids.get(level)` and the inserted pMark atoms in the flattened
window likely carry SHORTER unid chains than the grouping level being
coalesced (their `.get(level)` is None → empty key → filtered). Next probe
(first action of the resumed cycle): print `ancestor_unids` and the
grouping `level` for the two inserted pMark atoms at Step-1 time in
anchor_images×annot2, then decide mint-at-level vs group-at-parent.

Probe results, narrowing complete for tonight: with the H1 textless rule
LIVE and a Step-1 drop probe LIVE, the exhibit shows **zero Step-1 drops
and still no inserted empties in the output** — Step 1 is exonerated; the
empties vanish between the correlation worklist and coalesce grouping.
`build_paragraph`'s `if text.is_empty() { continue }` is the LEGACY
atom-shortcut assembler, not the CoalesceRecurse path. Remaining suspects,
in order: (a) the worklist resolution of the Inserted pMark-only
CorrelatedSequence (atoms may never be tagged), (b) finalize's handling of
inserted bare paragraph marks with no run content. Next probe: count
Inserted-status pPr atoms entering CoalesceRecurse for the exhibit. All
probes reverted; engine tree clean at 24b182f.

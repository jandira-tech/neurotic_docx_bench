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

## SHIPPED — the empty-paragraph chain closed (engine 6817a28)

The five-probe hunt ended in a two-line-of-logic fix, decomposed per
regression: (1) H1 must not positionally pair a LEADING ≤3-run of bare
paragraph marks on the revised side against contentful words
(insert-direction only — the delete variant broke meeting_agenda's 100;
leading-only after the first draft broke it anyway); (2) M86's run-less
whitespace fold only applies when NO inserted block content follows the
del run (file_173's 100 depends on the fold; anchor_images' 44 was caused
by it). Final blast radius: **5 docs, all scored changes positive (+45.9,
+10.3, +7.7), zero regressions, exact-100 docs byte-identical.** Suite
green. Official run in flight at jubarte-rust@74bbefc415c4+git.6817a28;
wasm rebuilding from the same source.

Method note for the record: the naive versions of BOTH rules each destroyed
a different 100-scoring document, found only because the A/B scores every
changed document against the officially recorded per-doc baseline. Blanket
rules lose; scoped rules discovered by per-document decomposition win.

### Next rust class: URL-interior anchoring (hyperlink pairs)

`hyperlink_node × hyperlink_node_internal` (rust 52.6, lossless AND
docxodus perfect): the two docs contain DIFFERENT URLs sharing long
substrings ('https', 'stackoverflow.com/questions/…'); rust's word-LCS
anchors inside the URLs and stitches the wrong paragraphs into mixes.
Word treats the hyperlink runs as atomic-ish and pairs at region end
([ins, ins, mix(last A×last B), del URL]). Study needed: how Word
tokenizes/anchors URL text in compare — likely a word-separator or
anchor-quality rule for runs inside w:hyperlink. Several hyperlink-named
targets in the rust-72 set share this class.

URL-anchoring class, sized and probed (7 rust targets, 52.6–90.9, ≈+0.18
mean potential): deeper than tokenization. In hyperlink_node×internal the
oracle redline contains ZERO w:hyperlink elements (Word unwrapped/dropped
them; the deleted URL is plain runs), lossless keeps 1 (fully inserted),
rust keeps 2. And Word DECLINES an exact-text paragraph anchor ('Some text
bookmark' is verbatim in both inputs yet the oracle pure-inserts B's copy)
— something invisible distinguishes the copies (bookmarkStart ids, rStyle,
or hyperlink wrapping) and drives Word to region-end pairing. Next cycle:
dump both inputs' 'Some text bookmark' paragraphs fully, find the
distinguishing attribute, and derive the anchor-refusal rule from all 7
pairs plus their perfect siblings' outputs.

RE-DIAGNOSED — the "URL class" is the UNRELATED-THRESHOLD divergence.
Inputs decoded: A=[title, URL-hyperlink-para], B=[title+bookmarks,
'Some text bookmark', link-para] — 'Some text bookmark' exists ONLY in B
(the earlier exact-text-anchor reading was wrong). Word's oracle shape is
the revised-first wholesale with ONE boundary mix ([ins B0, ins B1,
mix(A0×B_last), del A1]) — Word classified the pair UNRELATED. The TS ast
engine already implements exactly this rule (correlate.ts
DetectUnrelatedSources: unique-lexical overlap < UNRELATED_LEXICAL_FRACTION
= 0.08 AND no top-level group key matches ⇒ wholesaleUnrelatedWordShape).
rust's equivalent gate (`windows_related`, ≥20% of the smaller side's units
sha1-matching) measures a different thing and does not fire on this pair.
Port target: add the unique-lexical-fraction unrelatedness test to rust's
M-ANCHOR/confetti gating with the TS constant, emitting the boundary-mix
wholesale. Covers most of the 7 hyperlink-named targets and likely other
low-overlap cousins in the rust-72. One cycle, reference implementation
in-tree.

UNREL-LEX attempt 1 — inert, reverted (C8). The lexical gate was added to
`detect_unrelated_sources_word_mode` (after `disjoint`, small-window
2–3×≤6, <0.08 overlap, boundary-mix emission) and compiles clean, but the
exhibit output is unchanged: rust consults the unrelated shortcut only
AFTER the LCS finds no run, and on this pair the word-LCS accepts an
anchor first ('link'-family tokens), so the check never runs. The TS
engine runs DetectUnrelatedSources BEFORE correlation. The correct port is
therefore an anchor-VOID: in do_lcs_algorithm's guard chain (next to
M-ANCHOR, which requires min side >32 and thus skips small windows), void
len>0 when the small-window lexical-unrelatedness test passes, letting the
window fall through to the unrelated wholesale. One more cycle with the
window trace to confirm the flow before re-implementing.

## SHIPPED — UNREL-GLUE (engine 8cd638d)

The hyperlink class closed in three iterations, each killed by evidence:
detect_unrelated gate (inert — rust checks unrelatedness after LCS),
token-level stamp exclusion (tokenizer splits 'file_151'), raw-text stamp
check (stamp consumed upstream of residual windows). The shipped form:
extend the existing glue-word anchor gate to multi-para windows whose
sides share <0.08 significant tokens, with an `in_stamp_residual` settings
flag protecting the confetti machinery's own windows. Exhibit
52.58 → 99.66; blast radius 3 docs, net +43.9; file_151/127 byte-identical
via the flag. Suite green; official run in flight at 8cd638d.

### New class: in-block image loss (diff_before16×diff_before19, 53.9)

Block structure IDENTICAL to the oracle ([ins, mix, tbl del, same]) yet
53.9 — the loss is INSIDE the blocks, and the fixture is image-bearing
('An image will be added below:'). Likely the drawing is dropped or
misplaced within the mix/deleted table. Needs pixel-level comparison, not
alignment work. Several image-named targets in the remaining 70 may share
it (anchor_images at 89.99 post-fix, image_inline_and_block…).

### The dominant remaining rust class: one-sided table flattening (H2b)

`diff_after16×diff_after19` (rust 41.6, docxodus 100, worst remaining
target): rust's output contains NO tbl element — A's deleted table was
H4-flattened into words and reconstructed as a mix PARAGRAPH. Word and
docxodus keep the whole-table deletion: [ins B-paras (ins-first), mix at
the para boundary, tbl del, same]. Same family as multipara_cell (70.3
after the v6 partial fix) and likely several table-named targets in the
remaining 70. Spec for the next cycle — a new step_h H2b for ONE-SIDED
tables (left_tables>0 XOR right_tables>0): group-adjacent [Para-run,
Table, Para-run]; pair para-runs as Unknown (para-level LCS supplies the
boundary mix), emit tables whole as del/ins in ins-first order; never
fall through to the H4 word-flatten for these windows. Reference outputs:
docxodus at 100 on the exhibit, generated at
/Users/arthrod/temp/T/r3/dox_top/docx for the top-8 targets.

H2b — byte-neutral, reverted (C8). A correct one-sided-table walk in step_h
produces BYTE-IDENTICAL output to the current path: correlation already
emits the deleted table whole; the flattening happens DOWNSTREAM. The 'p
mix cell-00…' paragraphs mean the table's atoms are reconstructed as
paragraph children — the produce/assemble layer (Phase B's "borrow the
following paragraph's Unid prefix" with name-based share) mis-attributes
deleted-table atoms in mixed windows. This is the same machinery family as
the empty-paragraph drop (which was finalize's whitespace fold, found by
build-bracketing). Next cycle: bracket-dump the assembled body for
multipara_cell BEFORE finalize (the AFTER-MARK dump showed [p×7,tbl,p] for
anchor_images — run the same dump here to see whether the tbl exists at
assembly and dies in finalize, or never assembles). The class is worth
~two of the worst remaining targets (41.6, 45.8) plus the table-named tail.

## SHIPPED — the table-eating fold (engine pending-official)

The one-sided-table flattening was NOT correlation and NOT assembly — the
finalize bracket-dump pinned it to the SAME M86 whitespace fold (third
defect from one function tonight): para_is_pure_deleted accepts an
all-deleted TABLE, so the fold merged cell runs into a paragraph and
deleted the tbl. One-line guard (fold target must be w:p). A/B: 7 changed,
net +90.3, wins to +34.0; diff_after16 (the worst remaining target) now
matches the oracle exactly and scores 65.99 — its residual is the in-block
image class, not alignment.

UNREL-PRE attempt — reverted (C8, third inert variant on this class). The
pre-LCS wholesale at do_lcs_algorithm entry passes all canaries but misses
diff_after6×7: the window carries B's TABLE groups, failing the all-Word
gate; the actual shredding happens in an H1-created Words×Words sub-window
that also did not re-enter the gate as expected. The class needs the
window trace on diff_after6 specifically (which recursion entry resolves
the A-para × B-first-words pairing) before the next variant. Score at
stake: ~48.1 → ~90 on this exhibit plus the diff_after fixture family.

## SHIPPED — empty-alpha anchor void (v12, pending official)

diff_after6's surviving anchor decoded by trace as ['.', pMark] — Step F
keeps it because pPr atoms are not w:t. Voided in the UNREL-GLUE gate
(same unrelatedness + stamp-residual guards): A/B 8 changed, net +31.4,
one new exact-100 (increase_indent×insert_link 86.24→100.00), residual
−9.7 on product_roadmap (unrelated pair where the '.¶' anchor happened to
align — same coin-flip family as the lossless spacing folds). The
remaining diff_after6 delta is the fold POSITION rule: Word folds A0 into
B's LAST paragraph (or defers the del entirely when B ends with a table);
our H1 pairs A with B's FIRST words-group. That positional rule is the
next increment on this class.

UNREL-H1 attempt — no-op, reverted (C8). The H1-walk ins-all/del-last rule
passes every canary byte-identically but never fires on diff_after6; the
suspected cause is para_text_tokens_from_units semantics over flattened
WORD-unit windows at that seam (worked at the glue gate, inert here —
unverified). The fold-position class stays open with one precise question
for the instrumented cycle: print t1/t2 at the H1 seam on diff_after6.
Session tally on this class: v12's empty-alpha void banked (+31.4 A/B,
official 77.97/81.83/163/292); the remaining delta is fold position only.

## SHIPPED — rows-aware gate (v13): TWO new perfects, zero regressions

The fold-position class resolved without a fold-position rule at all: the
H1-seam probe showed H1 was never reached — the ['.', pMark] anchor
survived because the glue/empty-alpha gate required BOTH sides pure Words
and the flattened window carries table ROWS. Letting sides carry Rows
(run still pure-Words; single-para GLUE arm keeps the strict sides)
voids the anchor and the wholesale emerges downstream on its own:
diff_after6 48.10 → 100.00 EXACT, diff_before6 94.68 → 100.00, zero
regressions, every canary byte-identical. Official run in flight.

TS punctuation-void transfer — inert on diff_after11, reverted (C8). The
ast exhibit's anchor is real shared text ('text'/'this' between cousin
paragraphs), not punctuation: it is the styled-boundary merge class as
originally diagnosed, NOT the v13 visibility class. The v13 transfer may
still pay on ast pairs whose anchors are separator-only, but with no
moving exhibit in hand it does not ship. ast's cycle keeps its original
spec: trace the interleave branch on diff_after11 (which TS seam pairs
A-para1 with B-heading) and derive the split-vs-merge condition there.

ast interleave — second inert patch, reverted. The unrelated-para-run
branch landed in the words+rows interleave walk (keys 'word'/'row' from
interleaveKindOf — the 'para' condition was dead), which is also not the
seam: the top [ppp]×[ptp] window resolves to a 1×1 para pairing through a
path that is neither the pure-word zip nor the words+rows walk (leftWords=
rightWords=0 there). Corrected probe for the ast cycle: label EVERY return
site in the TS doLcsAlgorithm/doLcsNoMatch with env-gated prints (as done
for rust step_h) and run diff_after11 — find which branch creates the 1×1
A-para×B-heading unknown, then apply the <0.08 unrelatedness split THERE.

### ast one-sided-table seam — LOCATED and characterized; threshold underived

The seam is found and proven: doLcsNoMatch's one-sided-tables walk pairs
FIRST paras unconditionally (site: `lg.key === "para" && items>1 …
unk([lg.items[0]],[rg.items[0]])`). Splitting on FIRST-PARA unrelatedness
(<0.08 sig tokens) + ins-first wholesale takes diff_after11 44.35→97.89
and diff_after16 +18.2 (net +35.2 on the 22-doc blast radius) BUT destroys
sd_2672_nested_table×plain_3x3 (100→67) — related-table cousins whose
first paras share nothing. WINDOW-level relatedness (culA/culB incl.
tables) INVERTS: excludes the exhibit (one incidental shared ≥4-token)
while still firing on the cousins. The separating feature is between those
two scopes and needs DATA: log (t1, t2, inter, ratio) at the seam for all
22 changed pairs + their outcomes, then derive the threshold/feature
offline like the Normal-spacing table. Candidate features: table-text-only
overlap (cousins share cell text, diff_after doesn't), or ratio with
stopword-extended sig. Both variants reverted; TS tree clean at f9c71f0c.

## SHIPPED — ast styled-boundary split (engine 1cfd5d08)

The seam's rule turned out to be exactly what the corpus-wide 69/44 signal
hinted but could not prove: at the one-sided-table para pairing, split iff
the REVISED first paragraph is pStyle'd and the original's is not. The
derivation that made it shippable: feature-logging six A/B'd pairs at the
seam showed token overlap is NON-separating (correct merges share 0.0,
correct splits up to 0.57) while the style feature separates 6/6.
Exhibit diff_after11×16 44.35 → 97.89; corpus A/B: 15 byte-changed, the
only scored mover is the exhibit (+53.54), the token-split's three victims
(one exact-100) byte-identical. Suite: only the two documented
pre-existing failures. Official ast run in flight at 1cfd5d08.

## Text-equality amendment — committed (jubarte-first HEAD), official DEFERRED

Net +11.3 A/B'd (18 changed; +18.2 diff_after16; −3.7/−2.6 sd_2672×
hyperlink residuals). Deferred from its own official run under the
bench.jsonl budget (~4 slots left); the dist stays at the 1cfd5d08
official state. Next ast increment rebuilds from HEAD and batches both
into one run. Residual question for that cycle: why the text-split arm
lands multipara×hyperlink at 76.15 while the token arm hit 87.46 —
diff those two arms' outputs on that doc.

HARNESS BUG FOUND AND CHARACTERIZED (affects several ad-hoc A/Bs, NOT the
officials): the scoring harness cached rasters under truncated keys
(`k[:36]`/`k[:40]`), which COLLIDE across the multipara_cell×… pairs — the
token-arm/text-arm "difference" on multipara×hyperlink (87.46 vs 76.15)
was measured on BYTE-IDENTICAL outputs; one number scored the wrong
cached render. Corrected conclusions: (1) the text-equality amendment's
−2.6 "regression" was fake — its true A/B net was ≥ +13.9, and its
official row (72.59/73.71) stands as the ground truth; (2) any future
ad-hoc A/B must key raster caches by the FULL pair stem or a hash of it.
The officials all used the bench's own pipeline and are unaffected.

## CORPUS-INTEGRITY FINDING — 31 zero-revision oracles over differing inputs

Of the 92 measurable lossless perfect-sibling targets, **31 pairs' stored
oracle redlines contain ZERO w:ins and ZERO w:del while their two input
documents' texts DIFFER** — a Word compare of differing texts cannot
produce a revision-free redline, so these stored oracles are NOT the
compare of their mapped inputs (all are in the doctored word_based
`id_paraid_overflow` / `style_default_missing` family; e.g.
heading_4_style_demo×helvetica_font_demo, oracle = B's text with only 2
rPrChange/2 pPrChange). Consequences:

1. These 31 are NOT engine defects. Engines "win" them by accident (the
   rust output there carries mark-only dels that render invisibly) and
   "lose" them by doing a REAL compare (lossless's visible strikethrough
   is CORRECT behavior scored as wrong). They must be quarantined or
   their oracles regenerated — Arthur's call (bench-design, like C9).
2. The real lossless perfect-sibling target list is ~60, not 97; every
   engine's word_based-family scores carry some accidental credit.
3. Truth tables derived from oracle CONTENT on these pairs (the
   Normal-spacing table included them) should be spot-rechecked once the
   oracles are regenerated, though styles.xml-level rules may be
   unaffected.

Full list of the 31 pairs printed in the session log; reproducible via:
oracle has no ins/del AND doc_text(A) != doc_text(B).

### Next lossless class, sized: dropped empty DELETED paragraphs (11 targets)

Word's oracle keeps every empty/break-only paragraph of a deleted run as
its own deleted paragraph; lossless collapses them — exhibit
list_with_break_from_word×instrtext (57.8, rust perfect): oracle 8
del-paras ('Item 1','','Break test','','Item 2','','New list…','Num 2'),
lossless 5. Eleven real targets (57.8–90.7), two dropping 10 paragraphs
each (diff_before×before10 81.5, diff_after×after10 83.6). Instrument for
the next cycle: TS-side bracket dump of body child counts through
WmlComparer's internal produce/conjoin passes on the exhibit — the rust
twin of this class died in a finalize fold (M86); the TS drop site is
likely its conjoin/coalesce analog. Population value: roughly +2–4 points
across the 11 if the exhibit's +40-class recovery generalizes.

Lossless empty-del-para class — drop site BRACKETED to one function:
SRC1-RAW = 8 paragraphs [p,p0,p,p0,p,p0,p,p] (three empties), unchanged
through PreProcessMarkup; POST-PRODUCE = 5 — the empties die INSIDE
`ProduceDocumentWithTrackedRevisions` (TS WmlComparer). Same family as the
rust producer's historical empty-para bugs. Next cycle: sub-bracket inside
ProduceDocumentWithTrackedRevisions (its CoalesceRecurse / paragraph-mark
conjoin analogs) on this exhibit, find the collapse, guard it for DELETED
bare pMarks, A/B on the 11-target class (worth ≈+2–4 lossless points).
Traces reverted; TS tree clean at 6f9f76fc.

## SHIPPED — the empty-deleted-paragraph keep (jubarte-first HEAD, official in flight)

The five-layer TS bracket hunt ended at a documented blanket rule:
`RemoveEmptyDeletedParagraphMarks` stripped every empty deleted pilcrow
(file_8×9 GT) while `EnsureEmptyDeletedBetweenShortPureDeleted` re-invented
them for one-token shapes. The 22-line fix keeps an empty when BOTH
adjacent paragraphs are text-bearing pure-deleted (a real source spacer in
a continuing deleted run). Exhibit 8/8 oracle blocks (was 5/8, 57.8 vs
rust 100). Slice A/B with a same-build CONTROL isolating the rule from
54 docs of ambient drift: 73 attributable, 61 scored, net +87.9, two new
exact-100s, worst −0.64. This also includes the note that the deferred
amendments (f9c71f0c..6f9f76fc) drift 54/400 lossless outputs — needs its
own explanation next cycle. Trace scaffolding fully stripped before the
amended 22-insertion commit.

Drift question CLOSED with a same-build-twice control: lossless
document.xml is nondeterministic on 11/60 docs (18%) — GUID media names
leak into document.xml via rIds on image-bearing pairs. The 54-doc
"amendment drift" was this, not the amendments. All score-based verdicts
stand; byte-diff attribution on lossless requires rId/media normalization.

### Queue-top for the next cycle: lossless table-sink class

`diff_before3×sd_1494_table_left_indent` (60.0; rust AND docxodus perfect):
lossless emits […, ins '', ins '', del 'Here's some text.', tbl ins, ins '']
where the oracle is […, tbl ins, del] — the SECOND inserted table lands
AFTER the deleted paragraph, plus two phantom inserted empties. The TS
producer has `SinkDeletedBlocksBelowInsertions` (the rust twin's
reorder_replaced_blocks physics) — its conditions miss this two-table
shape. Instrument: bracket that pass on this exhibit (the Z-dump pattern),
inspect its gate, extend. 58 real lossless targets remain (artifact-31
quarantined); several table-bearing ones likely share this class.

**RESOLVED (2026-08-05): run-less inserted tables.** The sink's
`isInsertedBlock` table arm required `runs.length > 0` — the exhibit's
inserted tables have empty cells (zero `w:r`), so the pass never fired.
Fix: run-less table arm = `Descendants(w:ins) > 0 && Descendants(w:del)
== 0` (ins marks live on cell pilcrows/row marks). Exhibit 60.0 → 93.67,
block order matches oracle except one trailing inserted blank after the
table (Word drops it; the TS side lacks the rust trailing-empty strip —
smaller follow-on class). Full-corpus A/B: 81 byte-changed docs, 68 of
which are pure media-rId GUID nondeterminism (the r:embed="R<hex>" form —
NOT the "rId" prefix; normalization must strip `r:(embed|id|link)="[^"]*"`),
13 real: the exhibit + 6 word_based pairs ×2 corpora (OLE/sdt/strict docs
with run-less inserted tables). Suite: 494 pass, only the two pre-existing
failures (bookmarks self-compare, browser smoke). Second normalization
pass: the "13 real" shrank to 1 — SmartArt relIds (r:dm/r:lo/r:qs/r:cs)
are GUID-nondeterministic too; the definitive normalization is
`r:[a-zA-Z]+="[^"]*"`. THE EXHIBIT IS THE ONLY REAL CHANGE in 814 docs.

**Follow-on shipped same cycle: strip blank after inserted table.** With
the sink fixed, the exhibit read [tbl ins, eI, del] vs oracle [tbl ins,
del]. `StripMidstreamEmptyInsertedBeforePureDeleted` already handles
[content-para, eI, pure-del] — its `prevIsContent` refused tables. Added
`prev is wholesale-inserted tbl (hasIns && !hasDel)` arm. Exhibit 93.67 →
**100.00, exact oracle block match** (rust and docxodus parity). Suite
clean (same 2 pre-existing). A/B arm loss_stripfull vs loss_sinkfull.

**Drop-vs-relocate: B's blank count decides (8/8 truth table).** The
plain drop regressed word_based table pairs (book_catalog −10.22,
project_tasks −8.07, support_tickets −7.72): their oracles show
[eI, eI, tbl, del] — Word RELOCATES the misplaced blank back before the
table. A content-based gate (relocate iff table has text) fixed those
but broke the superdoc winners (annot2 100→49.95). The real feature is
**B's source blank count immediately before that table vs ours**:
relocate iff ours < B's (the producer split B's blank run around the
table); equal counts mean separator surplus → drop. Validated 8/8:
book_catalog/support_tickets/project_tasks B=2 ours=1 → relocate;
annot2 B=2 ours=2, diff_before7/pirates/sd_1494 B=0, diff_after7 B=1
ours=1 → drop. Implementation keys B's tables by concatenated live text
(first 64 chars), max blank count on collision; wDoc2 threaded into the
pass. Result vs sink baseline on the 13 affected rows: **+82.30, 10
improved > 0.5, zero regressed, 4 new perfects** (annot2, diff_after6×7,
the exhibit, diff_before6×7 all 100.00). With the sink's +33.65 the
cycle is +115.95 raw, no regressions.

### Lossless carrier-merge (I+D→M) — IMPLEMENTED, A/B pending

`sd_1919_word_simple×diff_after5` (52.7): we emit [ins 'Here's some
text.', del 'Chapter One', del..., same ''] where the oracle MERGES the
leading inserted para into the first deleted para: [mix 'Here's some
text.Chapter One', del..., same '']. Scan: **99/400 superdoc pairs
diverge first at exactly this seam, 93 exact-concat** — the largest
remaining lossless class. 52/400 oracles keep adjacent [I,D] unmerged
(separate correlation groups; coincidental adjacency), so a blind
post-pass merge is wrong — the fix belongs where the group is known.

Oracle carrier anatomy (sd_1919): ONE paragraph, A's pPr (Heading1) with
rPr/del pilcrow mark, B's ins runs first, A's del runs after.

Mechanism found in the lossless engine: DoLcsAlgorithm already has a
validated 1×1 low-overlap rewrite emitting [ins(B words), del(A words),
Equal(pilcrowA, pilcrowB)] — the Equal pilcrow pair is what fuses the
mix paragraph. Dead ends on the way: (1) instrumented
src/compare/correlate.ts first — that is the NATIVE engine, never loaded
by the lossless adapter (lossless.node.cjs ← src/lossless only);
reverted. (2) the new arm placed inside `if (s_docsShareContentWords)`
never fired — sd_1919's docs share ZERO content words so that whole
rewrite family is skipped; the arm must live OUTSIDE that gate.

Shipped shape — M×1/1×N wholesale replacement arm (exactly one side is
a single paragraph; all-words both sides; both streams end at a pilcrow;
jaccard < 0.2 with the same strong-share rescue as 1×1): emit
ins(B leading whole paras) + ins(B carrier words) + del(A carrier words)
+ Equal(carrier pilcrows) + del(A tail whole paras).
sd_1919: exact oracle block MATCH, **52.7 → 100.00** (LO does NOT tank
on the mix shape — the file_187 fear does not generalize here). Suite
494 pass / same 2 pre-existing fails. ≥2×≥2 merge population left for a
separate cycle (interacts with the early multi-para zip).

Full A/B (jfcF vs installed): **n=117, +894.63 → +1.17 projected mean,
perfects 5→20, above-92 11→37**, 51 improved vs 20 regressed. Shipped as
ff4d09d67.

**Regression class resolved: deleted table must extend the region in
RelocateRegionMarkSurvival.** Top regression diff_before16×diff_before19
(−46.16): the carrier para sits right before a wholesale-DELETED table;
tables were transparent to the pass, so the carrier was the region's
last A-origin paragraph and kept its live pPrChange (B pPr live, style
lost, no del mark) where the oracle flips it (A's Heading1 live + del
pilcrow). sd_1919 only worked because five deleted paras followed its
carrier. Fix: a pure-deleted table joins the region as an A-origin
member (never mutated itself — no pPrChange); a wholesale-inserted
table joins as B-origin; other tables flush the region. Result:
db16 → **100.00**, sd_1919 stays **100.00**. Suite green.

Full region-fix A/B (jfcH vs jfcF): **n=10, +69.29, two more 100.00s**
(diff_before16×19 +46.16, diff_after16×19 +30.81), word_based neutral.
Shipped as 07bd8ba21 (carrier merge = ff4d09d67).

**Open class from the region fix: sd_2672_sdt_table×sd_2750_borderbox
−13.82** (89.36→75.54). The flipped member is an interior pPrChange
para (live style-less, old Heading1) in a 73-member region of inserted
paras ending [pA, TA-deleted-table]; it carries REAL deleted text, so
del-content gates can't separate it, and the oracle still keeps it live
with pPrChange. Three gate refinements (pure-ins skip; table-anchored
del-content requirement; delText-only content test) were all
behavior-neutral on the corpus and were reverted per C8. Needs its own
truth table over pPrChange-para-before-deleted-table sites. Two smaller
same-family residuals: multipara_cell×hyperlink_node −3.96,
plain_3x3×hyperlink_node −2.41.

**Remaining regression classes from the carrier merge** (accepted, net
+894.63): math_groupchr×diff_before16 −24.7, table_merged_cells×
table_width −16.2, missing_sectpr×missing_separator −9.5 (block shapes
IDENTICAL base vs idm at top level — the delta is run/pilcrow-level,
uninvestigated), line_break×line_space −8.4, rtl_page_numpages×sd_1960
−9.3. Next major population: the ≥2×≥2 wholesale merge (the rest of the
99-seam class; interacts with the EARLY multi-para zip at
WmlComparer.ts ~17454).

### Native (ast) heading-carrier rule — sd_1919 51.55 → 100.00

Cross-engine follow-through: ast trails the new lossless by ~990 points
across 58 carrier-merge docs. Investigation surprises: (1) the native
doLcsNoMatch zip-gate loosening (parasB ≥ 1) was a NO-OP for sd_1919 —
baseline native ALREADY produces the mix block structure via another
path (13 byte-changed docs, all ≈ ±0; reverted per C8; the earlier
"MATCH" exhibit test was against stale official per_doc, not a fresh
baseline arm — always regenerate the baseline before exhibiting). (2)
The real native deficit is the HOST pPr: the mix carrier keeps B's
style-less live pPr + pPrChange, where the oracle hosts A's Heading1
live with the pilcrow marked deleted. `wordParityMixedBoundaryHostPpr`
already does exactly this promotion but excludes HeadingN (document_100
Tip: Word keeps bare B when the region does NOT continue deleted). The
region signal separates them: sd_1919's carrier is FOLLOWED by
pure-deleted paragraphs. New list-level pass
`wordParityHeadingCarrierBeforeDeletedRegion` (after regroup in
coalesce.ts, where sibling context exists): mix para + old pStyle
Heading[1-9] + bare live style + next block pure-deleted → promote old
pPr live, pilcrow del. Suite 661 pass. Full A/B pending.

Heading-carrier full A/B (jfcN2 vs fresh 07bd8ba2 baseline arm): 31
byte-changed docs, 25 scored (3 base-arm soffice failures in the
rId-noise ole_object/strict01 family, twins all +0.00): **+288.12 →
+0.38 mean projection, 17 improved vs 1 (−4.10
invalid_list_def_fallback), five new 100.00s** (sd_1919_word_simple,
sd_1919_word_mixed, diff_before16×19, multipara_cell×missing_separator,
hyperlink_node_internal×?). Shipped as 19b5f14c6; native official
running.

### QUEUE-TOP: rust carrier-merge port (~875-point gap, +1.15 mean)

Rust trails the new lossless on **54 carrier-merge docs, 875.4 points**
(multiple_nodes_in_list gap 51.7, doc_with_graphs 51.1, sd_1919 47.3,
missing_sectpr×fields 46.2 …). rust sd_1919 emits [I 'Here's some
text.', D 'Chapter One', D×5, D ''] vs oracle [mix, D×5, same ''] — the
same class, plus rust dels B's trailing empty where Word keeps it Equal.

The Word rule (validated across three engines): in a wholesale
replacement, B's LAST paragraph's words ride into A's FIRST deleted
paragraph — ONE carrier para: ins B-words then del A-words, A's pPr
LIVE (Heading survives), pilcrow marked deleted (pPr/rPr/del). Leading
B paras stay pure-ins, remaining A paras pure-del.

Rust entry points located: `stamp_confetti_then_replace` (lcs.rs:789,
wholesale-disjoint docs; residual pairing via `stamp_residual_pairs`
jaccard ≥0.25 tiers — sd_1919 shares ZERO tokens → no pairs → insert-all
+ delete-all thrash), `detect_unrelated_sources_word_mode` (lcs.rs:4179)
and the M104/M123/M133/M134 residual arms. Port shape: when residual
pairing yields NO pair for (A first-contentful residual, B last
residual), force-pair them so word-level LCS runs inside (the pair
machinery already produces the mix para; verify the pMark comes out
A-live + del — rust's finalize may need the same region rule as
RelocateRegionMarkSurvival got). Then A/B per the standard discipline.
The TS lossless implementation to mirror: the M×1 arm added OUTSIDE
s_docsShareContentWords in DoLcsAlgorithm (WmlComparer.ts, commit
ff4d09d67): ins(B lead) + ins(B carrier words) + del(A carrier words)
+ Equal(carrier pilcrows) + del(A tail).

Rust port increment (2026-08-05): `detect_unrelated_sources_word_mode`
(lcs.rs:4179) is the whole-doc ins-all/del-all gate but its count gates
need min side ≥2 contentful groups — sd_1919's B has ONE contentful
group, so the pair BYPASSES this gate and full LCS produces the [I, D]
shape elsewhere (trace needed: instrument lcs() entry for this pair
next). Mechanism confirmed available: nesting a 1×1 para pair through
`lcs(dom, vec![a], vec![b], settings)` produces the MIX paragraph
(M125's comment documents exactly that — it gates AGAINST nesting for
unrelated titles where Word pure-I's; our M×1 truth table is the
counter-population where Word DOES mix). Port shape stays as recorded:
fire only when exactly one side is a single contentful paragraph group
(mirroring the shipped lossless M×1 gate), emit ins(B-lead groups) +
nested-lcs(A-first-para, B-last-para) + del(A-rest). Trace first with
eprintln at the emission candidates; cargo build --release; exhibit
m_1919 via --method=jubarte-rust; keep wasm at parity (rebuild wasm
dist from the same commit).

Rust port FINAL SPEC: `resolve_correlated_sequences` (lcs.rs ~5000)
mirrors the C# pipeline exactly — `do_lcs_algorithm(dom, unknown,
settings)` is rust's DoLcsAlgorithm. Add the M×1 arm there, same
placement as lossless (after the zero-length-side early branches,
outside any share-words gating): all-Words both sides; pilcrow = Word
unit whose single atom's content element is pPr; exactly one side has
pilcrows==1 (other ≥2); both streams end at a pilcrow; content-word
jaccard < 0.2 with the strong-share rescue (shared token ≥5 letters AND
both sides ≤16 content words → skip). Emit: Inserted(B lead paras) +
Inserted(B carrier words) + Deleted(A carrier words) + Equal([A
pilcrow], [B pilcrow]) + Deleted(A tail paras). Then verify on m_1919
that rust's finalize (region-end mark survival) yields A-pPr-live +
del-pilcrow on the carrier; if not, rust needs the same region rule
RelocateRegionMarkSurvival got. Build: (cd ~/T/jubarte-redlines &&
cargo build --release), install target/release/jubarte as
src/neurotic_docx_bench/utils/jubarte/jubarte-rust/redline, exhibit,
full A/B (2×814), suite (cargo test), commit, officials for BOTH
jubarte-rust AND jubarte-wasm (rebuild wasm from same commit,
wasm-pack build in a subshell, never cd the main shell out of the
bench repo for uv run bench).

Rust M-CARRIER first attempt (2026-08-05, NOT shipped): the arm is
implemented in do_lcs_algorithm exactly per spec (working tree of
~/T/jubarte-redlines, uncommitted). Exhibit result: block structure
MATCH TRUE including the trailing same-empty (the old del-empty tail
fixed), carrier keeps Heading1 LIVE — but score moved 52.73 → 51.55
(−1.18) and C8 blocks shipping. Two visible defects in the carrier
pPr: (1) NO rPr/del pilcrow mark (rust's finalize did not flip it —
needs the region rule / or emit the pMark pair differently), (2) a
leaked `xmlns:ns0="http://powertools.codeplex.com/2011"` declaration
on the cloned w:pStyle. Debug next: why the −1.18 (compare renders —
possibly the missing del mark changes LO paragraph spacing, or the
xmlns leak, or the Equal pMark pair chose the wrong side's atoms);
then the del-pilcrow emission. The rust baseline binary was RESTORED
at src/neurotic_docx_bench/utils/jubarte/jubarte-rust/redline — the
new binary is parked at /Users/arthrod/temp/T/r3/jubarte-rust-carrier.

**Rust M-CARRIER attempt 2: sd_1919 52.73 → 100.00.** The fix: emit the
carrier pMark as Deleted([A pilcrow]) and absorb B's pilcrow entirely
(do not emit it) — the oracle carrier has exactly ONE paragraph mark,
A's, deleted, with A's pPr live. The Equal pair from attempt 1 left the
pilcrow unmarked (−1.18); the Deleted emission also serializes clean
(the xmlns:ns0 powertools leak from attempt 1 is gone). Carrier now:
pStyle Heading1 + rPr/del — exact oracle shape in all three engines.
State: edit UNCOMMITTED in ~/T/jubarte-redlines working tree
(lcs.rs do_lcs_algorithm M-CARRIER arm); new binary at
/Users/arthrod/temp/T/r3/rustdist/redline; bench baseline binary still
the OLD one (restored — do not run rust officials until the A/B
verdict). In flight: full A/B arms (rust_carfull vs rust_basefull,
2×814) and cargo test --release. Next: diff arms (r:-normalization),
score changed docs, if net-positive → commit engine, install binary,
rebuild wasm from same commit, officials for jubarte-rust AND
jubarte-wasm, commit rows, push.

Rust suite gate (attempt 2): cargo test fails ONE test —
m148_tolerated_inputs::canonicalizes_numeric_style_ids_to_word_names.
Its synthetic 1×2 pair now routes through the M-CARRIER arm and the
carrier mix para carries pPrChange{PreformattedText} with NO live
pStyle — the test asserts B's numeric list style must remap to
ListParagraph and survive live. Open question for the truth table: when
B's carrier para is STYLE-BEARING (list), does Word keep B's style live
in the replacement carrier (test's claim) or A's pPr live + del pilcrow
(sd_1919's oracle, where B was style-less)? Either add a B-styled
guard to the arm (skip when B carrier has pStyle/numPr) or update the
test per oracle evidence. Both full A/B arms are GENERATED
(rust_carfull vs rust_basefull, 814 docs each) — continuation: diff
with r:-normalization, score changed, resolve the style question, then
ship per the recorded pipeline.

Rust M-CARRIER full A/B (attempt 2 binary): **n=177, +695.43 → +0.91
mean, 60 improved vs 36 regressed, perfects 24 → 35**. NOT shipped yet:
three former-100.00 docs broke — diff_after6×diff_after7 −48.50,
diff_after11×? −47.81, msword_tracked_changes −15.79 (plus sdpr×sdt
−28.6, math_groupchr −27.6, font_size×green_bold −19.96/−6.39 both
corpora). Pattern: these are RELATED pairs whose interior unknown
regions have 1×N pilcrow shape — rust's arm fires there while the
lossless arm did NOT fire on the same pairs (they were absent from
lossless's 117-doc changed set at 99.98/100 baselines). Gate refinement
needed before ship; candidates: (a) fire only when the unknown region
is the document-leading region or spans the whole body (wholesale
replacement, not interior residual), (b) compare against what upstream
already resolved — if the region is small relative to the resolved
Equal mass, skip, (c) trace WHY lossless's identical gate doesn't see
these regions (different unknown splitting upstream) and mirror that
condition. The +0.91 net says the class is worth landing once the
over-fire is gated. Scores: r3/rustcar_ab_scores.json; arms kept
(rust_carfull / rust_basefull); binary parked at r3/rustdist/redline;
bench baseline binary UNCHANGED (safe).

Rust gate KEY FINDING (diff_after6×7 probe): the arm merged NON-ADJACENT
paragraphs — base output had I@block2 ('This will be del…') and
D@block6 ('Here's some tex…') with inserted TABLES between them; the
car arm fused them into M@2 and deleted block 6. The unknown region
that reached do_lcs_algorithm paired B-lead words with A-tail words
from opposite sides of Equal-matched middles — NOT a physically
contiguous replacement. The lossless engine's identical arm never sees
such regions (its unknowns preserve adjacency). Gate: require the
carrier pair to be layout-adjacent — e.g. fire only when the WHOLE
unknown maps to one contiguous body neighborhood (no Equal/table
content between the A-side and B-side atoms; check ancestor/document
order of A-first-para atoms vs B-last-para atoms), or restrict to
unknowns whose atoms' document positions interleave rather than span
disjoint neighborhoods. This single gate should rescue the three
former-100s (−48.5/−47.8/−15.8) while keeping the +695 class.

---

## Cycle 2026-08-05 (post-compaction): lossless 79.19 → 80.36 official

Goal moved to mean 90 / median 90 / 200 perfect (start lossless).

**Shipped (engine a7ee150e3 + a9e4a33ac, official row pushed 464f4738):**
1. `DropDanglingStyleReferences` final pass — Word drops style refs its
   output styles part doesn't define (truth table 39/40 drops; the 1 kept
   ref is defined in output). A/B: 16 changed, +38.7, 0 regressions.
2. Junction carrier seam — group-level 1×N/M×1 arm (XOR-single, DIRECT
   carrier emission; Unknown re-entry let recursion re-pair arbitrarily)
   + unrelated-docs M×N fast-path seam (text-bearing junction gate:
   38/52 junction-M, zero false positives). A/B: 61 changed, +831.5,
   42↑/3↓, perfects +17.

**Official: mean 80.36 / median 86.42 / perfect 188 / above92 319.**
Projection 80.33 vs actual 80.36 — method holds.

**Catastrophe averted + memory written** (truth-table-coverage-must-match-
blast-radius): extending the group arm to M×N (`either side >1`) hijacked
related-doc recursions (word-hash jaccard ≈ 0 when formatting differs) —
−1801 pts, 59 perfects lost in A/B. Diff-first, then table the CHANGED set.

**In flight: rule 4a** — interior junction-mix pilcrow deletion without
pPrChange (RelocateRegionMarkSurvival). Truth table: 35/49 seam junctions
pilDel in oracle; blast-radius check on the 76 out-of-evidence docs came
back 55:1 goodflip:badflip (rule generalizes to related-doc regions).
A/B scoring 93 docs now (arm_cand4 → arm_cand5, dist jfcW).

**Open classes (recorded, unshipped):**
- Guard scoping (rule 4b): `liveHasStyle && !oldHasStyle` skip should not
  apply to unrelated-seam regions (two_column residual −0.44; oracle flips
  styled junction, pPrChange rides last A para @151). Needs isolated A/B —
  first attempt rode with the bad M×N gate and could not be attributed.
- ooxml_bold_vals×diff_before8 −10.2: oracle = MMM positional correlation
  of first min(nA,nB) paras between unrelated docs — different shape from
  the junction seam; 'other-shape' bucket (11 pairs) likely same class.
- title_style p2: Word emits wholesale ins-before-del inside a matched
  paragraph even with a shared ≥5-letter token (strong-share rescue
  over-correlates there); title pair residual 78.00 vs docxodus 100.
- image_inline_and_block at 91.05 (was 30.46): remaining 9pts unknown.

## 2026-08-05 afternoon: lossless 80.60 official; AST buffer-pooling bug found

**Lossless OFFICIAL #2 (engine d44dc0749, row 5c64f427): mean 80.60 /
median 86.60 / perfect 201 / above92 326.** The 200-perfect goal is met for
lossless; mean and perfects now lead docxodus (80.55 / 187). Median 86.60
vs docxodus 91.19 is the remaining axis.

**AST root-cause discovery (jubarte-first b9f77679b):** mammoth's openZip
accepted a bare Buffer through its `options.buffer` branch via the
Buffer's own `.buffer` property — the WHOLE Node allocation pool. Node
pools small readFileSync results into one shared ArrayBuffer; zip readers
scan backward for the EOCD, so every pooled document parsed as whichever
file sat LAST in the pool → compare saw identical sides → identity
redline, zero revisions on differing documents (title_style pair reported
0 revisions; with unpooled copies: 4). Every same-tick read pair was
exposed — the bench generator reads exactly that way. Fix: openZip routes
bare typed-array inputs as the exact view (JSZip is offset-correct).
Follow-ups shipped: sequential side reads (ae810fd0f), dangling-style-ref
strip in the style post-pass (50155bfba). AST official in flight.

**Median-90 campaign notes (2026-08-05):** gap is 35 docs ≥90 out of a
105-doc 78-90 band; 42 band docs have docxodus ≥90. The top two exhibits
(annot2×annotations_import 78.43, increase_indent×insert_link 78.59) both
show the JUNCTION shape on RELATED-doc paths: oracle keeps B's middle
paragraphs pure-I and rides B's LAST paragraph into A's FIRST deleted one
(annot2: even when A-first is EMPTY — the fast-path text gate should be
B-last-only when this ships). Two speculative DoLcs gates (fast-path
afirst relax; low-jaccard residual junction before TryMultiParaPositional
Zip) did NOT move either exhibit — the pairing happens elsewhere: the
FindCommonAtBeginningAndEnd residual split (WmlComparer.ts ~13262) pairs
≤2 leftover paragraph chunks POSITIONALLY first-to-first. Next cycle:
trace which branch pairs those residuals and apply the junction emission
there (reverted both gates per C8; tree back at 50155bfba).

## 2026-08-05 rust M-CARRIER shipped (engine 0f39b64e)

The QUEUE-TOP adjacency gate resolved as a WHOLESALE gate: both sides of
the unknown must start at their body's first content block AND end at its
last (trailing empty paragraphs tolerated). diff_after6×7's fusion turned
out to be a 1×N whose B side continued with content tables — Word keeps
A's deleted paragraph whole after them (junction-pure, the same empty/
continuation discriminator as the lossless truth table). All three former-
100 sentinels verified back at baseline structure; sd_1919 keeps the
carrier. The m148 suite question resolved WITH evidence: document-final
carriers keep a LIVE mark with B pPr + pPrChange (Equal pilcrow pair),
interior carriers keep A props + deleted mark — the lossless rule-4b
split, ported. Full cargo suite green.

A/B: 70 changed, +636.2, 28↑/5↓ (worst −10.3), perfects +11. Projection
+0.83 mean → expect ~78.9 rust official. Binary installed; wasm rebuilt
from the same commit; officials for jubarte-rust AND jubarte-wasm in
flight.

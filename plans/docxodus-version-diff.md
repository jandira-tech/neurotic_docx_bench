# What docxodus does differently — 7.0.0 → 9.0.0, and why it wins

Evidence base for the three jubarte plans. Everything here is measured, not
inferred from release notes (docxodus publishes none for these majors).

Method: `npm pack` of 7.0.0 / 7.1.0 / 8.0.0 / 9.0.0, extracted side by side under
`~/temp/T/docxodus-diff/`, then (a) file-set and byte diffs of `dist/`, (b) symbol
diffs of the .NET payload `dist/wasm/_framework/Docxodus.wasm` via `strings -n 6`,
(c) per-document score joins on `results/bench.jsonl`.

---

## 1. It is not a rewrite. It is an accretion.

| step | identifiers added | removed |
|---|---:|---:|
| 7.0.0 → 7.1.0 | 31 | 1 |
| 7.1.0 → **8.0.0** | **846** | 28 |
| 8.0.0 → **9.0.0** | **331** | 9 |
| 7.0.0 → 9.0.0 (net) | 1208 | 38 |

1208 added against 38 removed makes 9.0.0 very nearly a superset of 7.0.0.
`Docxodus.wasm` grew 2.54 MB → 2.99 MB (+17.6%); `index.js`, the JS surface, moved
by −194 bytes.

This closes out a claim I published and retracted earlier in this audit ("9.0.0 is a
rewritten IR engine"). It is not. `IrReader` is one of the 38 removed symbols and the
`IrMarkup*` family is still present in both — the engine was extended, not replaced.

## 2. The default comparison engine flipped between the majors

```
7.0.0  index.js:  options?.engine ?? ComparisonEngine.WmlComparer
9.0.0  index.js:  options?.engine ?? ComparisonEngine.DocxDiff
```

Same call, different engine, no error and no warning. Our generator pins
`ComparisonEngine.DocxDiff` explicitly (`scripts/generate-native-redlines.ts:288`), so
the published A/B held the engine constant and the 38→3 failure drop is attributable
to the version, not to this flip. Anyone benchmarking docxodus **without** pinning
`engine` has silently compared two different algorithms across the upgrade.

## 3. Where the 846 symbols of 8.0.0 went

| theme | new symbols |
|---|---:|
| **Style** | **53** |
| Table | 26 |
| Field | 22 |
| Anchor | 18 |
| Revision | 15 |
| Textbox | 13 |
| Drawing | 13 |
| Sdt (content controls) | 11 |
| HeaderFooter | 10 |
| Backfill | 6 |

The Style family is the story. The names are explicit about what it does:

```
ResolveEffectiveStyleFormatting      ResolvesLeftParagraphStyleChain
ApplyDocDefaultsStyleProjection      AllLeftStoryParagraphStylesResolveWithinLeftStyles
CollectUsedStyleIdentities           CollectInlineCharacterStyles
NormalizeInsertedParagraphStyle      NormalizeInsertedStyleRunProperties
DropDanglingParagraphStyleRefs       DropUnresolvableStyleRef
EnsureStylesPart                     RebindRightImportedStyleNumberingReferences
```

`left`/`right` is comparison vocabulary. This is a comparer that **resolves the full
style inheritance chain on both sides before diffing**, normalises what it inserts
into the target document's style vocabulary, and drops references it cannot resolve
rather than emitting them.

A second family repairs the *output document* rather than the diff:

```
BackfillDefaultTheme   BackfillFontTable   BackfillStockDocDefaults   BackfillWebSettings
```

That is Word-validity insurance: if the comparison result lacks a theme, font table,
docDefaults or webSettings part, docxodus synthesises a stock one instead of shipping
a document Word will offer to repair.

## 4. Where the 331 symbols of 9.0.0 went

| theme | new symbols |
|---|---:|
| Comment | 30 |
| Note (foot/end) | 24 |
| List / numbering | 23 |
| Revision | 21 |
| Anchor | 16 |

Be careful attributing these. A large share are the **editor** API, not the comparer —
`AddComment`, `AddCommentReply`, `InsertFootnote`, `InsertEndnote`, `ListComments`,
`SerializeCommentList` — and 9.0.0 also ships new `editor-reconcile.js` and
`page-number-format.js` entry points. `editor.js` grew +40 KB in the same step.

The comparer-side additions in 9.0.0 are the numbering ones — `EffectiveNumberingOf`,
`RepointListInstance`, `StampOriginalNumberingMarker`, `ApplyListStartOverride`,
`ClearListNumberingAnnotations` — which matter because list renumbering is a classic
source of whole-document visual drift in a redline.

**Unmeasured, and the cheapest next experiment:** we have 7.0.0 and 9.0.0 on the bench
but never ran **8.0.0**. The symbol census says 8.0.0 carries the comparer work and
9.0.0 carries mostly editor work. One 8.0.0 run settles it and costs a single sweep.

## 5. What the scores actually say — the advantage is *not* typical

Joining per-document scores on the 760 documents both engines scored:

| | docxodus 9.0.0 | jubarte-lossless |
|---|---:|---:|
| ITT mean | 80.24 | 77.02 |
| ITT median | 91.11 | 78.53 |
| **median of the *paired* difference** | \+0.06 | |

On the median document the two are within **six hundredths of a point**. docxodus wins
354 documents, jubarte wins 273. The headline median gap of +12.6 is a difference in
distribution *shape*, not a uniform superiority — and the documents each engine wins
are different documents.

Where the gap does live:

- docxodus's 354 wins average **+18.6** and total **6581** points.
- jubarte's 273 wins average +14.4 and total 3939.
- Net **+2641** over 760 docs = **+3.46** mean.
- **86 documents carry half** of docxodus's entire winning margin.

The gap is concentrated in ~11% of the corpus. That is what makes it addressable.

## 6. The mechanism, from the two sub-metrics we already record

| | skill_median | page_median |
|---|---:|---:|
| docxodus 9.0.0 | **100.00** | 76.38 |
| jubarte-lossless | 53.07 | **83.30** |
| jubarte-rust | 86.19 | 65.99 |
| jubarte-ast | 74.89 | 52.06 |

`skill` is the change-region score net of the null baseline — how much of the available
credit the engine earns *for the redline itself*. `page` is page-geometry fidelity.

This is the whole diagnosis in four rows:

- **docxodus nails the change region** (skill_median 100 — on the median document it
  extracts *all* available skill) and is mediocre on page geometry.
- **jubarte-lossless is the opposite**: the best page fidelity in the table, and it
  earns only half the available change-region credit on the median document.
- **jubarte-rust** sits in between, good skill and the worst-but-one page fidelity.
- **jubarte-ast** is behind on both.

jubarte is not losing because it renders documents badly. It is losing because its
*markup of the change* is less complete, on a subset of documents, while it renders
better than the winner.

## 7. Independent corroboration: our weak fixtures are docxodus's 8.0.0 investment

Lowest-scoring fixture-name tokens, per engine (n ≥ 10):

| jubarte-rust | jubarte-lossless | jubarte-ast |
|---|---|---|
| rtl 50.2 | rtl 55.2 | styles 49.1 |
| styles 55.9 | math 57.6 | page 53.9 |
| math 58.4 | combos 59.4 | combos 54.2 |
| combos 60.4 | rstyle 59.4 | rstyle 54.2 |
| rstyle 60.4 | styles 59.5 | linked 56.3 |
| tab 60.0 | ooxml 60.1 | math 56.5 |
|  | linked 61.6 | ooxml 57.1 |

`rstyle` / `combos` / `linked` / `styles` / `ooxml` are the
`ooxml_rfonts_rstyle_linked_combos` fixture family — **style inheritance resolution**.
All three of our engines are weakest there, and it is exactly the area docxodus put 53
new symbols into in the release that moved its numbers. Two independent lines of
evidence pointing at the same defect is as good a signal as this data can give.

## 8. The finding that dominates all of it: the family already clears the targets

Per-document upper envelope of the three jubarte engines — for each document, the best
score any one of them achieved:

| | ITT mean | ITT median | perfect |
|---|---:|---:|---:|
| target | > 81 | > 92 | > 200 |
| docxodus 9.0.0 | 80.24 | 91.11 | 187 |
| jubarte-lossless | 77.02 | 78.53 | 142 |
| jubarte-rust | 76.21 | 77.95 | 158 |
| jubarte-ast | 69.83 | 68.30 | 84 |
| **envelope of lossless + rust** | **82.63** | 90.78 | **210** |
| **envelope of all three** | **84.01** | **92.07** | **233** |

The capability to clear every target already exists inside the jubarte family. It is
distributed across three engines that fail on **different documents**. There are 123
documents where some jubarte engine scores 100 and docxodus does not, against 77 the
other way.

**Blunt caveat, and it is the important sentence in this document:** the envelope is an
*oracle* bound. It is computed by looking at the scores — i.e. by using the answer to
choose the engine. It is a ceiling, not a result, and it must never be published as a
score. A shippable router has to choose from the input pair alone. The envelope's value
is that it proves the ceiling is above the target, so the remaining question is
selection and transfer, not capability.

## 9. Lever sizing (arithmetic on the recorded scores)

Every engine has a dense cluster of documents scoring ≈50 — the single largest mass in
each distribution:

| engine | docs in [40,60) | median of that cluster |
|---|---:|---:|
| jubarte-lossless | 166 | 51.5 |
| jubarte-rust | 197 | 50.6 |
| jubarte-ast | 255 | 50.7 |
| *docxodus 9.0.0* | *167* | — |

Counterfactuals, applied to the recorded per-document scores:

| lever | lossless | rust | ast |
|---|---|---|---|
| A — lift every [40,60) doc to 90 | 85.43 / 90.00 / 142 | 86.36 / 90.00 / 158 | 83.00 / 90.00 / 84 |
| B — lift the 40 style-family fixtures to 95 | 78.90 / 82.00 / 142 | 78.07 / 83.46 / 158 | 71.86 / 71.71 / 84 |
| A + B | 86.04 / 90.00 / 142 | 87.08 / 90.00 / 158 | 83.70 / 90.00 / 84 |

*(mean / median / perfect)*

> **Correction, 2026-08-04.** The lever-A rows above lift the cluster to exactly 90,
> which is why every median in that column reads 90.00 — that is an artifact of the
> landing point I chose, not a ceiling. Lifting the same cluster to 93 instead gives
> median **93.00 / 93.00 / 93.00** for lossless / rust / ast, clearing the target.
> Where the mass lands matters as much as that it moves.

Read that table carefully, because it splits the goal in two:

- **Mean > 81 and median > 92 are both bought by lever A** — the ≈50 cluster, provided
  those documents land *above 92* rather than at 90.
- **Perfect > 200 is not.** Lifting documents anywhere below 100 moves the perfect count
  by exactly zero. That target alone requires converting *near-misses into exact
  matches* — precision work, not coverage work.

**Why near-miss closure cannot buy the median.** The median of 763 documents is the
382nd value, so median > 92 requires 382 documents scoring above 92:

| engine | scoring > 92 today | shortfall to 382 | of the [90,100) pool, how many sit ≤ 92 |
|---|---:|---:|---:|
| jubarte-lossless | 251 | 131 | 26 |
| jubarte-rust | 282 | 100 | 25 |
| jubarte-ast | 158 | 224 | 20 |

Near-miss closure can contribute at most 26 / 25 / 20 documents to shortfalls of
131 / 100 / 224. The rest must come from the ≈50 cluster. The first version of the three
plans assigned the median target to near-miss closure; that was wrong and is corrected
in each of them.

Near-miss inventory (documents in [90,100), the pool that must convert):

| engine | in [90,100) | perfect now | needed for 200 | conversion rate required |
|---|---:|---:|---:|---:|
| jubarte-lossless | 135 | 142 | +58 | 43% |
| jubarte-rust | 149 | 158 | +42 | 28% |
| jubarte-ast | 94 | 84 | +116 | > 100% — must also reach into [80,90) (101 docs) |

---

*Corpus: 763 ITT documents (803 pairs less the 40-pair sealed holdout), scorer
`pagefair-v2`, oracle LibreOffice 26.2.4.2. Runs `019fcd2f` (docxodus 9.0.0),
`019fcc6f` (lossless), `019fcc5d` (rust), `019fcc7c` (ast).*

---

# Correction, 2026-08-04 (evening) — §7's token analysis does not survive Stage 1

§7 argued that our weakest fixture-name tokens (`rstyle`, `combos`, `linked`,
`styles`, `ooxml`) coincide with docxodus 8.0.0's 53 new Style symbols, and called
that "two independent lines of evidence pointing at the same defect". **Stage 1
measured it and the coincidence does not hold.** Recorded here because that argument
is what targeted workstream S, and it targeted it at the wrong population.

**Fixture-name tokens name what a fixture TESTS, not why we lose on it.**
`ooxml_rfonts_rstyle_linked_combos_*` is a *combinatorial* family — its members pair
formatting attributes two at a time — so the token marks correlation granularity, not
a shared cause. Measured on the 25 `rstyle`/`combos` pairs after the Rust engine's
style-chain work landed:

| | count |
|---|---:|
| pairs whose output `document.xml` changed | **0 / 25** |
| pairs with a *live* colliding style (the population S addresses) | 6 / 25 |

The family's lowest scorers — `highlight × bold` 41.05, `highlight × italic` 41.18,
`italic × rFonts` 43.59, `size × strike` 44.15 — have **zero** live collisions and
**zero** body-markup change. Style-chain resolution cannot move them because their
defect is not style inheritance.

**What the symbol-name inference got wrong.** Reading a competitor's exported symbol
names tells you what they *built*, not what *we* lack. Three of the four repairs the
names suggested were already present in our engines under different names, worthless
on this corpus, or actively harmful:

- `ResolveEffectiveStyleFormatting` (walk `w:basedOn` before comparing) — 238 merge
  verdicts flip in the TS engine, and in **0** of them do the two sides name a
  different parent. Every flip is a no-op with ratchet risk.
- `DropUnresolvableStyleRef` — **the wrong repair.** Word's own redline emits the
  identical dangling `rStyle w:val="Hyperlink"`; dropping it moves us *away* from the
  oracle. The remaining dangling-ref pairs already score 97.6 and 100.0.
- `NormalizeInsertedParagraphStyle` / `CollectUsedStyleIdentities` / `EnsureStylesPart`
  — already implemented in the TS engine as `CopyMissingStylesFromOneDocToAnother`,
  `BuildMergedStyleLikeWord`, `EnrichDocDefaultsLikeWord`.

**What the corpus said instead**, found by measuring the oracles rather than reading
docxodus's exports: Word's Compare stylesheet takes the **revised** document's
definition of every style both documents define and records the **original** inside a
`w:pPrChange` / `w:rPrChange` **on the `w:style` element itself**. 52.5% of 564 corpus
oracles carry style-level change markup. Our `copy_missing_styles` was keyed on
`(type, styleId)` and skipped any id already present whatever its body, so the output
kept the original's definition and recorded nothing — content on both sides rendered
with the original's fonts, sizes and borders and the change was invisible.

**136 of 597 corpus pairs carry at least one live collision. They score mean 59.7 /
median 55.9, against 79.4 / 86.2 for pairs without one.**

That is a real, sized, measured population — and it is not the one the token table
pointed at. Use token tables to locate fixtures, never to attribute cause.

# GLM fixture report — 2026-10-11

Per-fixture diagnosis of jubarte DOCX→PDF rendering vs the Microsoft Word oracle.
Converter under test: jubarte 0.12.0 RC (`jubarte-loop/release_0.12/rc/jubarte-9263d377`,
invoked as `convert <docx> -o <pdf> --force --revisions word --compress`).
Method: diagnose from the rendered PDFs first; unpack the DOCX only to confirm.

---

## Fixture `4351ae2564` — clean__4351ae2564_000e1b3323b64d5ef8787d98095593fcfb7a1332c3a3c4f5

Traditional-Chinese internal-control form (佛光大學, 標楷體 body font, A4,
`docGrid type="lines" linePitch="360"`). Contains one full-page embedded Visio
flowchart displayed via EMF. Sources_500 set.

**Scores** (bench visual scorer, vs Word oracle PDF):

| run | overall | pages |
|---|---|---|
| jubarte 0.12.0-rc 9263d377 (this diagnosis) | **43.35** | 6 vs Word's 5 (mismatch) |
| jubarte 0.10.1 (corpus-all run 2026-10-01) | 59.97 | — |
| soffice 26.8 / docxide-pdf 0.17.1 (reference) | 42.78 / 44.67 | — |

Per-page (0.12.0): 52.1 / 46.9 / 43.9 / **39.8 (blanked flowchart page: ink_f1 0.0, edge_iou 0.0)** / 40.2.
This fixture regressed 59.97 → 43.35 from 0.10.1 to 0.12.0.

### Issue 1 (primary): EMF image rasterized to a blank white bitmap — flowchart lost

- **Word**: renders `word/media/image1.emf` (37,768 B, valid EMF, frame 656×863) as
  vector — 129 drawing ops on page 3, with selectable text
  (開始 / 詢問姊妹校名額及公告接受教師申請 / 繳交申請資料 / …). The swim-lane
  flowchart is the document's central content.
- **jubarte**: reserves the correct placement (56.7,56.7 → 538.0,630.2 pt ≈ the
  requested 481.2×573.6 pt) but embeds a 291×384 DeviceRGB PNG that is **pure white**:
  numpy over every pixel → min=max=255, 0 non-white pixels of 111,744. Jubarte page 4
  is therefore visually blank; page score 39.76 with ink_f1 = 0.0.
- **DOCX evidence (confirmed after PDF diagnosis)**: single `<w:object w:dxaOrig="9855"
  w:dyaOrig="12963">` with `<v:shape style="width:481.2pt;height:573.6pt" o:ole="">`
  + `<v:imagedata r:id="rId7"/>` (rels → `media/image1.emf`) and
  `<o:OLEObject Type="Embed" ProgID="Visio.Drawing.11" … r:id="rId8"/>`
  (rels → `embeddings/oleObject1.bin`). The flowchart is an OLE/Visio object whose
  display face is the EMF; Word plays the metafile, jubarte's rasterization of it
  produces an empty bitmap.

### Issue 2: CJK line box ~14.5 % too tall inside table cells → row growth, page overflow

- Same span, same font, same size in both PDFs — 「佛光大學內部控制文件制訂/修訂說明表」
  18 pt MicrosoftYaHei: **Word line box 23.8 pt (1.32 em ≈ YaHei winAscent+winDescent
  2166+536 / 2048); jubarte 27.2 pt (1.51 em)**. 14 pt bold spans: 18.4 vs 21.1 pt.
- Measured page-1 revision-table row borders (horizontal rules >100 pt wide):
  Word gaps 50.0 / 49.2 / 62.6 / 83.0 / 165.4 / 62.4 / 62.6 / 62.7 pt;
  jubarte gaps 73.5 / 72.8 / 108.7 / 144.7 / 288.8 pt — rows ~1.4–1.5× taller, only
  ~5 rows fit where Word fits 8+, and the table spills onto a second page.
- Body paragraphs **outside** tables are grid-snapped identically by both renderers
  (baseline gaps all 36.0 pt = 2 × linePitch 360 twips), so this is specifically the
  in-cell line-box metric (Word does not apply docGrid inside table cells; jubarte's
  cell line height ≈ 1.51 em does not match Word's ≈ 1.32 em for the same font).
- Net effect: 6 pages vs Word's 5, all downstream content shifted (drift up to
  ~498 px/page in the scorer).

### Issue 3 (consequence): anchored objects land on different pages

The floating text box 文字方塊 8 (「表單修訂日期：105.09.14 / 保存期限：…」; stored as
`mc:AlternateContent` — `wp:anchor` + `wps:wsp` DrawingML with a VML `w:pict`
fallback) is rendered by both, but on **Word page 1** vs **jubarte page 2** — it
follows its anchor paragraph, which jubarte pushed to the next page by Issue 2.
The second form page (第2頁/共2頁) starts on Word p4 vs jubarte p5; the tail
(3.控制重點 … 5.依據) on Word p5 vs jubarte p6.

### Checked and NOT issues

- `w:tblHeader` repeated header rows: count 0 in this DOCX — the document-control
  header table is physically repeated in the body, not a repeat-header effect.
- The "footer notes" are not story footers (no footer*.xml parts); they are the
  anchored text box above, and jubarte does render them.
- Page geometry identical (A4 595×842 pt both).
- Font substitution itself: both renderers substitute the missing 標楷體 with
  MicrosoftYaHei for the measured spans (Word additionally uses MS-Gothic/YuGothic
  for some runs), so Issue 2 is a metric/formula difference, not font choice.

### Conclusions

1. **EMF (OLE/Visio display face) rasterization is broken/blank** — the whole
   flowchart is lost; worst single-page penalty on this fixture (ink_f1 0.0).
2. **In-table CJK line box should be ≈ winAscent+winDescent (~1.32 em for YaHei)**,
   not ~1.51 em; fixes the row-height inflation and the 5→6 page drift and lets the
   anchored text box land on page 1 like Word.
3. Score regression 59.97 (0.10.1) → 43.35 (0.12.0-rc) on this fixture; the blanking
   of the EMF plus the taller rows account for it.

*Evidence artifacts (scratch, rasters deleted after scoring): jubarte.pdf + word.pdf
side-by-side page pairs; pixel stats of the extracted page-4 PNG; span/line/ruler
measurements via PyMuPDF; document.xml fragments quoted above. Re-scored with the
bench's own `pipeline.score_folders_plain` (dpi 144, default config).*

---

## Fixture `9abf4fa5b5` — `rejected/tracking_without_comments/9abf4fa5b5`

The id resolves to the word_based_0926 comparison **6e08e456f6_roboto_underline_demo
__vs__36fbd8c734_sales_report_january_2026_suggesting_insertions_redline_9abf4fa5b5**
(state `tracking_without_comments`; Word-Compare redline: 13 `w:ins` + 5 `w:del`).
Its reject-all derivative `clean__6eaf636739_9abf4fa5b5_rejected_tracking` (pool
`rejected_tracking_0928`, named `9abf4fa5b5_rejected_tracking`) was checked as well —
same root cause. One page each (Letter), "Roboto Underline Demo" vs "Sales Report"
docs merged by Word's Compare.

**Scores** (bench visual scorer, vs Word oracle PDF):

| doc | 0.9.3 | 0.10.1 | 0.12.0-rc 9263d377 (this diagnosis) | docxide metrics 0.10.1 |
|---|---|---|---|---|
| A: tracking redline | 83.13 | 83.13 | **83.15** (ink_f1 0.987, edge_iou 0.865) | 64.75 |
| B: rejected_tracking | — | 78.11 | **79.43** (ink_f1 0.963, edge_iou 0.773, color_sim 0.0) | 40.81 |

### Issue: font substitution — `Roboto` rendered as Arial (jubarte) vs real Roboto (Word)

- **Word**: embeds and uses **Roboto-Regular** for the three lines that request it
  (heading + two body lines of the Roboto demo half of the comparison); everything
  else Calibri. Insertions painted `#d13438` + underline; deletions kept as
  strikethrough text.
- **jubarte**: identical in every measured structural respect — same text layer
  (only trailing-space spans differ), same line y-positions (72.0 / 97.5 / 122.9 /
  148.4 / 173.8 / 199.2 / 224.7 / 250.0 / 274.6), same revision color `#d13438`,
  same underline geometry within ±3 pt (e.g. 296.9 pt vs 292.3 pt wide; Arial's
  advances differ) — **except** the Roboto lines come out in **ArialMT**.
- The whole ~17–20-point loss on these one-page documents is letterform/advance
  difference from that substitution: edge_iou 0.865/0.773, color_sim 0.0 (both pages
  are pure grayscale — verified pixel scan; the color metric reacts to the shifted
  anti-aliasing tone histogram of different glyph shapes), slight underline width
  drift. No layout, pagination, or revision-painting bug.

### DOCX + source evidence (confirmed after PDF diagnosis)

- Runs declare a **compound, CSS-style family name**: `<w:rPr><w:rFonts w:ascii="Roboto,
  sans-serif" w:hAnsi="Roboto, sans-serif" w:cs="Roboto, sans-serif"/><w:u w:val="single"/></w:rPr>`
  (the fixture generator wrote HTML-ish font lists into OOXML; fontTable carries
  `w:font w:name="Roboto, sans-serif"`).
- Roboto is **not installed** on this machine (only RobotoCondensed ships inside some
  jubarte distributions); neither DOCX embeds fonts. The Word oracle was produced on a
  machine where Roboto resolved to the real face (PDF embeds a Roboto-Regular subset).
- Jubarte's choice is deliberate catalogue policy, not a lookup miss:
  `jubarte src/convert/font.rs` `mapped_face()` classifies `key.contains("roboto")`
  into the generic **Sans slot = Arial** (47-face in-memory catalogue; Carlito=Calibri,
  Serif=Times New Roman, …; several other families got fixture-tuned mappings — e.g.
  `cambria`, `bookantiqua` — but Roboto folds to generic sans).

### Conclusions

1. Revision rendering (`--revisions word`) is **correct** on this fixture: insertion
   color/underline, deletion strikethrough, positions, and underline rules all match
   the Word oracle.
2. The fidelity gap is **Roboto → Arial substitution**. Matching the oracle requires
   actual Roboto glyphs: add a Roboto (or RobotoCondensed) face to the converter
   catalogue, or bundle it — the `contains("roboto")` → generic-sans mapping cannot
   reproduce Word's output on machines where Word has Roboto.
3. For the record: the oracle itself is environment-dependent (Word used a locally
   available Roboto); on a Roboto-less machine Word would also substitute — this
   fixture class measures whether the renderer ships/covers common web fonts.

*Evidence (scratch, rasters deleted after scoring): span tables (font/color/flags/y)
for both PDFs, underline drawing dumps, grayscale pixel scans of both pages, run
rPr XML quoted above; re-scored with `pipeline.score_folders_plain` (dpi 144).*

---

# Batch 2 — 2026-10-11 (user-passed list, priority first)

Same method: PDF-first diagnosis, DOCX unpacked only to confirm. Converter:
jubarte 0.12.0-rc `jubarte-9263d377 convert --revisions word --compress` unless
noted. Scratch under `tmp/glm_batch/<id>/` (rasters deleted after analysis).

## PRIORITY `corpus/clean/0b1d0278ce` — math radicals disappear (score 65.83)

`0b1d0278ce_behavior__math_radical_tests_4c1ce187`, one Letter page, three
`m:oMath` runs (`sqrt_degHide`, `cube_root`, `empty_deg_no_degHide`).

- **Word**: each `m:rad` renders as radical glyph `√` + operand `𝑥` in CambriaMath
  12 pt **plus a drawn vinculum** (3 thin rects over each operand: y≈74.6/101.0/128.2,
  ≈6.7 pt wide); the cube root's degree shows as a small CambriaMath 7 pt mark before
  the radical.
- **jubarte**: **the `√` glyph and the vinculum are gone entirely** — text layer is
  just `𝑥`, and the page has **0 vector drawings** (Word has 3). The cube root comes
  out linear: `3𝑥` — the `m:deg` content leaks as a plain 12 pt digit in front of the
  operand with no radical structure at all.
- **DOCX confirmation**: `<m:oMath><m:rad><m:radPr><m:degHide m:val="1"/>…</m:radPr>
  <m:deg/><m:e><m:r>…<m:t>x</m:t></m:r></m:e></m:rad></m:oMath>` ×3; #1 has
  `m:deg` = `3`, others empty `m:deg` (one with, one without `m:degHide`).
- **Conclusion**: jubarte's OMML handling linearizes `m:rad` to the operand text
  (and degree digits) and drops the radical glyph + overbar. Fix: render `m:rad`
  as U+221A (radical, Cambria Math) with a drawn vinculum over the `m:e` operand,
  degree set small and superscript-left of the radical when `m:degHide` is absent.
  This is a hard fidelity defect for any math-bearing document (score 65.83 driven
  entirely by it; ink_jaccard 0.19).

## `cases/case70` — margin line numbering: jubarte is CORRECT, reference is off by one (score 81.08)

docxide-pdf test case (`w:lnNumType`, OOXML 17.6.8): 12 single-line paragraphs,
sectPr carries `<w:lnNumType w:countBy="1" w:start="1" w:restart="continuous"/>`.

- **Reference** (`docxide-pdf/tests/fixtures/cases/case70/reference.pdf`): margin
  numbers read **2,3,4,…,13** — every line off by one (12 lines must end at 12).
- **jubarte**: margin numbers read **1,2,3,…,12**, one per line at x≈66.4 (reference
  x=66.0), matching `start=1 countBy=1 restart=continuous` and Word's documented
  line-numbering behavior (first body line numbered 1).
- **Conclusion**: "didn't obey original" is inverted here — the original
  (reference.pdf) is the deviant. Recommendation: **keep jubarte's behavior**;
  file the off-by-one against the docxide-pdf reference. Residual 19-point gap on
  this page is typography (font/metrics), not the numbering semantics.

## The four `redlines/tracking_without_comments/*` fixtures — one shared root cause: revision paint color is author-keyed in Word, fixed in jubarte

Cross-fixture evidence (all PDF-diagnosed first, then confirmed by `w:author`
in the unpacked DOCX):

| fixture | revision author(s) (w:ins/w:del) | Word paint | jubarte `--revisions word` paint | score (word mode) |
|---|---|---|---|---|
| 9abf4fa5b5 (batch 1) | Comparison | `#d13438` red | `#d13438` red — **match** | 83.15 |
| `3f74e8a0d4` | MacLachlan, Jamison B (EHS) | `#4e6aed` blue | `#d13438` red | 76.90 |
| `15a27d9c50` | Arun Kamble (651 ins / 244 del) | `#4e6aed` blue | `#d13438` red | 43.19 |
| `42878027b0` | Martinez, Evelyn (64 ins / 87 del) | `#005b70` teal | `#d13438` red | 72.03 |
| `c9b73cc74a` | Author + Online User | `#5c2e91` / `#881798` purple | `#d13438` / `#0078d4` | 82.85 |

In every other respect the tracked-change rendering matches: same tracked spans,
same fonts, same y-positions, same underline rule under the same span (verified
rect 114.0→181.0 @ y≈754.3 in 3f74e8a0d4 on both sides), insertions underlined,
deletions struck. Word's markup color is **keyed by author** (same palette slot
for MacLachlan and Kamble, different slots for Martinez / Author / Comparison) —
it is not "first author = red". Jubarte's `word` mode has a two-color palette
(red, then #0078d4) that only matches Word when the author happens to land on
Word's red slot (as "Comparison" did).

### `3f74e8a0d4` (MassHealth redetermination, 4 pp, "check pdf conversion")

Word 4 pages = jubarte 4 pages; text layers near-identical; the visible delta is
the markup color above plus minor rule-count differences (Word 40 thin rules on
p1 vs jubarte 129 thinH + 72 small rects — extra rules sit under multi-run
inserted words). Verdict: **conversion is faithful except the author-color**.

### `15a27d9c50` (HLL Lifecare Hindi/English tender, 15 pp → jubarte 14 pp)

- The tracked changes are **genuine, on purpose** — author "Arun Kamble",
  651 insertions / 244 deletions (a real edit session, not a compare artifact).
- Word: 15 pages, all changes blue `#4e6aed`. jubarte word mode: 14 pages
  (**pagination drift −1 page**), all changes red `#d13438`.
- Devanagari text (Mangal font) is shaped correctly in both — the doubled
  consonants in jubarte's extracted text layer (`लललमटेड`) are a text-stream
  ordering artifact, the glyphs on the page are right.
- **User directive to record**: the changes in this document are intentional;
  move this fixture **out of `--revisions word` into jubarte's other revisions
  behavior (`conventional`)** for the bench rendering. (Conventional-mode score
  42.89 vs word-mode 43.19 — mode choice is not what the pixel score measures
  here; the directive is about semantic intent, and the −1 page drift + red/blue
  mismatch remain the visual deltas to fix.)
- **42878027b0** (Student Union agenda, 4 pp = 4 pp): author "Martinez, Evelyn",
  Word paints teal `#005b70`. **User directive**: docxodus output is the source
  of truth for this pair; jubarte should use its **other (conventional)
  behavior — "our optimal"** — for this fixture.
- **c9b73cc74a** (IT Security Policy v2, 1 p): authors "Author" + "Online User",
  Word paints two purples (`#5c2e91`, `#881798`); jubarte red/`#0078d4`.
  **User directive**: **follow Word behavior** — i.e. `--revisions word` stays,
  and jubarte's author palette must reproduce Word's by-author assignment.

**Recommendation (all four)**: implement Word's author-keyed markup palette in
`word` revisions mode (derive the slot from the author name as Word does —
evidence above shows name→slot is stable across documents), and keep
`conventional` mode for fixtures whose changes are authored content rather than
compare output (15a27d9c50, 42878027b0 per user).

## `corpus/clean/73aceaa568` — VML image size in `px` ignored → 72×72pt default (score 51.38)

Spanish travel brochure, Word 4 pages → jubarte 3. The hero photo (native
1024×575) is a **VML inline picture**: `<w:pict><v:shape type="#_x0000_t75"
style="width:600px; height:336.9140625px; …"><v:imagedata r:id="rId8"/>` — size
in CSS px, no `wp:extent`.

- **Word**: px at 96 dpi → 600px = 449.6 pt, 336.9px = 252.2 pt; placed at
  (72.0, 236.2) — measured exactly 449.6×252.2.
- **jubarte**: same position but **72.0×72.0 pt** — the px width/height in the
  VML style is not parsed; a 1-inch default box is used. Shrunken image → row
  of brochure content reflows → 4 pages become 3. Header/footer PNGs (with
  proper `wp:extent`-style handling) place correctly on both sides.
- **Fix**: parse `width:`/`height:` in `v:shape/@style` including `px` units
  (96 dpi → pt) when no extent is available.

## `corpus/clean/a206273d01` — justified-RTL left measure wrong (score 59.32)

Persian thesis-defense notice, 2 = 2 pages, page border frames equivalent
(Word 36 small rects vs jubarte 8 — same double-rule geometry).

- **Word**: the justified RTL abstract lines span **64.1 → 523.2 pt** — the
  line box extends ~8 pt past the 72pt left margin (margins are uniform 1440
  twips, no indents; Word's Arabic-justification measure).
- **jubarte**: the same lines span **72.0 → 523.2** — clamped at the margin,
  so every line wraps earlier and the abstract reflows (p1 spans 150 → 132;
  committee info shifts; p2 grows 30 → 104 spans). Mixed RTL/LTR wrapping also
  differs (title 'آنالیز سیگنال EEG … (PTSD' stays one line in Word, splits in
  jubarte).
- Docx facts: 13 `jc=center`, 1 `jc=both`, only ONE explicit `w:bidi`
  paragraph; space-run padding does the "column" layout (17 single spaces at
  7.2pt each in Word = natural width; jubarte's runs stretch wider).
- **Fix**: reproduce Word's RTL justification measure (line may start left of
  the margin) and Word's space-run advance for Arabic script.

## `corpus/clean/9666fa13fb` — WMF rasterized blank: coat of arms invisible (343 → 342 pp)

Telecommunications Act 1997 compilation. **The cover image is
`word/media/image1.wmf`** (Windows metafile).

- **Word**: renders it as a 226×165 raster with real ink (25% non-white) at
  (120.5, 70.9), size 111.7×81.1 pt.
- **jubarte**: embeds a **384×279 PNG that is 100% white** (0 of 107k pixels
  non-white) at the same position/size — the Commonwealth Coat of Arms is
  invisible. Same defect class as batch-1 fixture 4351ae2564 (EMF → blank).
- All 83 Part/Division headings ARE present in both (an earlier regex
  mismatch suggested otherwise — extraction-order artifact). Page delta −1 is
  pagination drift, secondary.
- **Fix**: the WMF/EMF rasterization path produces empty bitmaps (see also
  84fa0f7a28 below) — three independent fixtures now confirm it.

## `corpus/clean/ad43500302` — numbered list rendered as bullets (score 77.92)

`super_editor__list_numbering_reimport` demo, 1 page, four 'test' items.

- **Word**: `1. test / 2. test / a. test / 3. test` (decimal ilvl0,
  lower-letter ilvl1).
- **jubarte**: `• test / • test / o test / • test` — bullets.
- **DOCX confirmation**: paragraphs carry `<w:numPr><w:ilvl …/><w:numId
  w:val="1"/></w:numPr>`; numId 1 → abstractNum 0, whose levels are
  `numFmt="bullet"` with `lvlText` U+F0B7 / `o` / U+F0A7 (Symbol/Courier/
  Wingdings). The decimal definitions (`%1.`, `%2.` = decimal/lowerLetter)
  live in abstractNum 1/2 behind numId 2 — **unreferenced by the paragraphs**.
- Word's oracle nevertheless paints the decimal list: on this re-imported
  file Word reconciles the numbering (nsid/tmpl/durableId heuristic) to the
  decimal definition instead of the literal numId chain.
- **Fix (user directive: numbers, not bullets)**: replicate Word's numbering
  reconciliation for this re-import pattern (match by `w:nsid`/`w:tmpl`/list
  identity rather than the bare numId→abstractNum pointer when the referenced
  abstract is a stock bullet set and a sibling abstract shares the list nsid).

## `corpus/clean/d18a18cfba` — floating image transposed + misplaced on landscape page (score 44.46)

Japanese garden document, landscape (842×595), Word 19 pp → jubarte 21.

- The single raster image (651×657 PNG) declares `wp:extent cx="2343807"
  cy="1922780"` = **184.6 × 151.4 pt**, anchored bottom-right.
- **Word**: placed exactly **184.5 × 151.4 at (540.4, 361.7)**.
- **jubarte**: placed **151.4 × 184.6 at (104.2, 98.6)** — width/height
  **transposed** and anchored top-left. With the image occupying the wrong
  region, the many anchored text boxes (211×425 pt class) reflow and the
  document grows by 2 pages (21 vs 19); graphic pages (≈500 vector ops each in
  both) survive.
- **Fix**: honor `wp:extent` cx/cy without swapping on landscape sections, and
  resolve the anchor (column/margin-relative offsets) against the rotated page
  box. Everything else on this doc is close ("almost perfect" per user).

## `corpus/clean/e5d81e791e` — block spacing too tight; rules at wrong spots (score 44.65)

Seychelles Supreme Court judgment, 7 = 7 pages. ("needs to follow word strictly")

- Word p1 draws 2 real horizontal rules (471pt wide at y=246/410, from the
  `w:pBdr` bottom borders — 5 in the doc) plus 1,964 **degenerate 0×0 rects**
  (invisible; no crest exists — no image parts in the package).
- jubarte p1 draws **4 full-width rules** (y=232.3/382.1/473.8/517.7) — two
  extra rules surface where Word has none — and compresses the page: by
  mid-page text sits 28–56 pt higher than Word ('21 September, 2017' y=422.7
  vs 394.6; '19 October 2017' y=503.9 vs 448.0). Line spacing is
  `w:line="360" lineRule="auto"` (1.5) with `w:after` 120–240 — jubarte's
  paragraph spacing doesn't reproduce Word's metrics on this pleading, which
  also relocates every pBdr rule.
- **Fix**: match Word's paragraph-spacing arithmetic (1.5-line + contextual
  after-spacing) and pBdr placement; drop the two spurious rules.

## `corpus/clean/84fa0f7a28` — chart metafiles rasterized near-blank (score 52.55)

Friction-stir-welding paper with MATLAB/Origin-class charts, 6 = 6 pages.
Media: `image6.emf`, `image7.wmf`, `image8.wmf`, `image9.emf` (+5 PNGs).

- **Word** p2–p5: 674/514/257/574 vector drawing ops (live charts).
- **jubarte**: p2–p3 comparable (720/536), but **p5's two charts rasterize to
  384×296 images with 0.2% ink — effectively blank** — replacing 574 vector
  ops; p4's is 11.1% ink; p6's 67.4%. Chart axes/curves are lost where the
  raster fails. p6 also drops most text (36 → 2 spans) and the
  'List of figures' block.
- Third independent confirmation of the broken WMF/EMF rasterization path
  (with 9666fa13fb and batch-1 4351ae2564). **This is the user's "graphic
  really terrible" and the highest-value convert fix after math.**

## `corpus/clean/b8eddffd09` — Arabic lines overflow the page edge (score 51.12)

Morocco HCP consumer-price memo (Arabic), 3 = 3 pages. Same defect family as
a206273d01 but catastrophic:

- **Word**: RTL lines stay inside the text area — right edges ≤ 524.4 pt on a
  595-wide page (ragged start per RTL).
- **jubarte**: title/heading lines reach **x1 = 599.2 pt — 4 pt past the
  physical page edge** (595) and far past the 523.2 margin; body lines run to
  547.5. Justified lines are stretched with huge space runs (extraction shows
  10–15 trailing spaces per line), and p1 loses ~2/3 of its line count
  (94 → 26 spans) as content merges.
- **Fix**: RTL line measure must wrap at the right margin; do not stretch
  space runs beyond the column width. (User: "RTL text doesn't align left
  correctly" — confirmed: measure + alignment both wrong.)

## `corpus/clean/2e41610325` — inline mid-sentence image dropped out of the line (score 47.40)

`super_editor__diff_after6` demo: 'Here's some [image] text.', 1 = 1 page,
ink_jaccard 0.0 — **zero overlap** between renders.

- **Word**: 200×200 image **inline in the sentence**: 'Here's some ' ends at
  x=138.9, image occupies (138.9, 72.0)–(238.9, 172.0) between the words,
  ' text.' continues at x=238.8 on the same baseline area (y=160.8).
- **jubarte**: the image is evicted from the line — placed on its own at
  (72.0, 97.0), and the sentence closes up as one span 'Here's some  text.'
  at y=72.0.
- **Fix**: keep inline drawings (run-level `w:drawing`) in the line box;
  evicting them to a block changes every subsequent line ("ours is horrible"
  = the whole page shifts).

## `corpus/clean/dff49e67e2` — table vertical borders missing (score 64.51)

Hungarian competency-change table, 1 = 1 page. All text present in both;
purely a border defect ("our table doesn't have vertical lines").

- **Word**: **624 vertical** + 460 horizontal rules.
- **jubarte**: **276 vertical** + 506 horizontal — fewer than half the
  vertical lines.
- **DOCX confirmation**: 6 tables, 138 grid columns; `tblPr/tblBorders`
  declares `insideV`/`insideH` single sz=4, while **414 cells carry
  `<w:tcBorders>` overrides, 230 of them `<w:bottom w:val="nil"/>`** (classic
  collapsed-border suppression pattern).
- **Fix**: implement OOXML border resolution order — tblBorders insideV/H are
  the defaults; per-edge tcBorders override; `nil` suppresses. Jubarte is
  dropping insideV edges in the presence of tcBorders overrides instead of
  merging them.

---

### Batch-2 cross-cutting summary (priority order)

1. **WMF/EMF rasterization produces blank/lossy bitmaps** — 4351ae2564 (EMF,
   blank), 9666fa13fb (WMF, blank), 84fa0f7a28 (EMF/WMF charts, blank/partial).
   One fix covers three fixtures.
2. **OMML math: radicals dropped** — 0b1d0278ce (user-flagged priority).
3. **RTL line measure/alignment** — b8eddffd09 (overflows page edge),
   a206273d01 (left measure 8pt short, reflow).
4. **Floating/inline picture geometry** — 73aceaa568 (VML px size ignored),
   d18a18cfba (extent transposed + misanchored on landscape),
   2e41610325 (inline image evicted from its line).
5. **Numbering** — ad43500302 (bullets instead of numbers; Word's
   reconciliation of re-imported lists must be replicated).
6. **Table borders** — dff49e67e2 (insideV lost under tcBorders overrides).
7. **Revision paint palette** — author-keyed colors in `--revisions word`
   (batch table above).
8. **Paragraph spacing/pBdr** — e5d81e791e.
9. case70 — no jubarte defect (reference is off by one; keep jubarte).

---

# Batch 3 — 2026-10-11 (priority cases + 4 corpus docs)

Cases are docxide-pdf fixtures (`docxide-pdf/tests/fixtures/cases/<id>/input.docx`
vs `reference.pdf`). Same method: PDF first, XML last. Scores are vs the
docxide reference (not a Word oracle) — several references are themselves
broken; noted per case.

## The chart cases: `case29` (53.40), `case52` (50.25), `case53` (51.51), `case31` (51.10)

DOCX carries real chart parts (`word/charts/chartN.xml`). All four renderers
use the Office theme palette (#4472C4 / #ED7D31 / #A6A6A6 / #C0504D…).

- **`case29`/`case52` (bar charts) — the REFERENCE is the broken side.**
  Reference draws each series as **one giant overlapping slab** (211–220 pt
  wide, e.g. blue 211×159.4 + orange 211×119.2 + gray 211×40.4 stacked with
  staggered offsets) — not a clustered chart. **jubarte draws a textbook
  correct vertical clustered chart**: 4 clusters × 3 bars, 22.4 pt wide,
  heights 83/68/15, 122/98/23, 104/87/17, 147/110/37 at x≈98/180/262/344, plus
  legend swatches. The ~50 score measures distance from a broken reference.
  Real jubarte deltas: axis/legend text is gray `#595959` (reference: black).
- **`case53` (extreme data)** — genuine jubarte defect: bar VALUES are right
  (e.g. 30.1/149.3/60.8/141.5/89.5 vs jub 30.3/150.4/61.2/142.6/90.1 — within
  0.5pt) but jubarte draws **50 bars where the reference draws 76** —
  categories/series are dropped on dense charts.
- **`case31` (scatter/doughnut/radar/bubble)** — jubarte draws 18 markers at
  6.0pt vs reference 24 at 4.7pt: fewer, larger points; doughnut/radar series
  incomplete ("rly rly bad" per user).
- **Recommendation**: keep jubarte's clustered-bar geometry (it is right;
  file the slab rendering against the docxide reference); fix (a) dropped
  categories on dense charts (case53), (b) marker count/size for
  scatter-family charts (case31), (c) use black for chart text if matching
  the reference matters.

## `case37` — SmartArt: INVERTED, jubarte is right ("blacked out?" — yes, by the reference)

User suspicion confirmed in the unexpected direction: the **reference blacks
the SmartArt out** — 5 solid black rects (75→221, 235→382, 396→543 × 77.7→165.5
and two more) — its fallback for unsupported diagrams. **jubarte renders the
real diagram from the OOXML cache**: exactly **13 shapes matching
`word/diagrams/drawing1.xml`'s 13 `dsp:sp`** with the same fills
(#70AD47 green, #BFBFBF, #4472C4 blue, #404040) and texts
(Start/Research/Review/Approve/Complete/Planning/Execute/Report).
**Recommendation**: keep jubarte's behavior (Word renders from the same
cache); score 48.07 measures distance from a black-box fallback.

## `case43` (59.24) / `case44` (59.23) — WordArt: text renders flat, no warp/effects ("needs word arth fix")

Modern DrawingML WordArt (`wps` text body + `a:lstStyle` effects).

- **Reference**: draws the warped/shadowed WordArt as **vector outlines** —
  12/20 drawing ops, no text spans for the WordArt words.
- **jubarte**: emits the words as **real 36pt text in the correct theme
  colors** ('FLAT OUTLINE' #2e75b6, 'SHADOW TEXT' #c00000, 'WAVE EFFECT'
  #ed7d31, 'DEFLATE', 'CHEVRON', 'CASCADE', 'DOUBLE WAVE', 'FADE RIGHT'…)
  but **completely flat — 0 vector ops**: no warp presets, no shadows, glow,
  outlines or fills.
- **Fix**: implement the warp `prstGeom` transforms (wave/chevron/inflate/
  deflate/cascade/fade) and the effect list on text runs. Base text, fonts
  and colors are already right.

## `case51` — nested tables collapse ("very important")

Nested-table test (2×2 outer with 2×2 inner per scenario). **Reference 2
pages → jubarte 1**; drawings 232 → 143; text survives (1312 vs 1264 chars)
but re-flowed. Inner-table row heights are not computed — the nested content
stacks tight, every scenario compresses onto one page. **Fix**: recursive
table layout (measure inner tables into their cell's height, honor
`w:trHeight` and cell margins at both levels).

## `case55` — conditional table formatting: close, header text color wrong (60.13)

`tblLook` + `tblStylePr` test. Fill counts nearly match (black 76→64, green
66→60, blue 18→16) — some border fills dropped. The visible defect: **5
header-row spans that the reference renders white (#ffffff on colored
shading) come out black in jubarte** (white spans 9 → 4). **Fix**: honor
`tblStylePr`/`firstRow` run formatting (font color from the table style) and
the remaining border fills.

## `corpus/clean/844ea6febc` — EMF financial tables lose content ("very very bad", 53.36)

Indonesian proceedings paper, 11 → 12 pages. The financial tables are **EMF
images** (`image6.emf`, `image2.emf` — pasted Excel ranges), not `w:tbl`.

- **Word**: plays the EMFs as **vector + real text** — 87/213 grid-line
  drawings, extractable values ('Investasi awal', 'Rp 60,000,000,000',
  '7.00%', '9.83%', '15.973%', '116,081.23', '2.392', 'HARGA', 'KONSUMSI'…).
- **jubarte**: rasterizes them at **~65 dpi equivalent** (e.g. 384×230 px
  for a 425×256 pt area) with only 6–27% ink — values are blurry pixel mush
  or missing; 182 of 458 text lines exist only in Word's output.
  Embedded fonts (`word/fonts/*.odttf`) are also present in this package.
- **Fix**: this is the metafile path again (5th instance with 4351ae2564,
  9666fa13fb, 84fa0f7a28, and case-partials) — EMF/WMF need vector playback
  (or ≥300dpi raster) with text extraction, not 65dpi bitmaps.

## `corpus/clean/9d3fa84f9f` — numbering part missing: numbers vanish (62.09)

The package has **no `numbering.xml` at all** (word/ = document.xml +
styles.xml only); paragraphs reference `numId 1` nevertheless.

- **Word**: self-heals — renders `1. 2. 3. 4.` before Apples/Bananas/
  Oranges/Grapes.
- **jubarte**: renders no markers whatsoever ('Bullet List Demo / Apples /
  Bananas / Oranges / Grapes').
- **Fix**: when the numbering part is absent but `w:numPr` references exist,
  synthesize Word's default list definition (decimal, '%1.'). Related to
  ad43500302 (bullets-vs-numbers) — both are numbering-resolution repairs
  Word performs and jubarte must mirror.

## `corpus/clean/3b3d3caac7` — header logo sits 12pt low, covering the title (54.62)

School letterhead (`CHIEF LESCHI SCHOOLS`), 2 = 2 pages. The logo is an
anchored image in `header1.xml`.

- **Word**: logo at y=23.9 (anchored above the body title).
- **jubarte**: logo at y=**36.0** — the nominal `w:header=720` twips line —
  12.1 pt lower, **on top of the title text** (the user's "overwriting
  picture"). Overlap set is otherwise identical (same 2 spans touched).
- **Fix**: honor the anchor's own offset math inside headers
  (position relative to the header paragraph / margin), not the nominal
  header distance.

## `corpus/clean/bb5b3dffec` — margins/spacing arithmetic drift (42.76)

6 = 6 pages, same 72pt margins, but per-page content redistributes: p1 has
76 lines in Word vs 66 in jubarte; the big vector block swaps pages (draws
p3: 154↔299, p4: 301↔178); jub p2's text runs to x=545.9 — ~3pt past the
543pt right text edge used everywhere else; p5's 20 gray `#595959` styled
spans reduce to 1 (styled text loses its color). Everything consistent with
paragraph-spacing/margin arithmetic differing slightly from Word and
compounding across a dense 6-page doc. **Fix**: align line/after-spacing
rounding with Word (compare e5d81e791e, same family); clamp justified lines
to the text width.

---

# Batch 4 — 2026-10-11/12 (five redlines: truth directives, watermark, checks)

## Author-color palette — extended evidence (batch 4 adds 5 rows, incl. a contradiction)

| fixture | author(s) | Word paint | jubarte paint | score |
|---|---|---|---|---|
| 9abf4fa5b5 | Comparison | `#d13438` red | red — match | 83.15 |
| 6532beda4d | Comparison | `#d13438` red | red — **match** | 88.19 |
| **18533edab7** | **Comparison** | **`#cc3595` magenta** | red | 82.07 |
| 3f74e8a0d4 | MacLachlan | `#4e6aed` blue | red | 76.90 |
| 15a27d9c50 | Arun Kamble | `#4e6aed` blue | red | 43.19 |
| 42878027b0 | Martinez | `#005b70` teal | red | 72.03 |
| 754a666443 | Bo Hurkmans | `#005b70` teal | red | 39.95 |
| c9b73cc74a | Author + Online User | `#5c2e91`/`#881798` | red/#0078d4 | 82.85 |
| 450945a41c | PG3646 | `#5d5a58` gray | red | 46.32 |
| 06e28e4cef | Vicky Wragg | `#b146c2` purple | red | 58.63 |

**Key finding**: the same author name ("Comparison") receives **red in two
documents and magenta in a third** — Word's by-author markup color is
assigned per export session (it is not derivable from the document alone;
no color is stored in the DOCX). Consequence: jubarte cannot statically
match Word's revision colors for every document; the achievable target is
Word's observed palette rotation (`#d13438, #4e6aed, #005b70, #5c2e91,
#5d5a58, #cc3595, #b146c2, …`) with a per-document choice, accepting some
mismatches — or dropping color matching in favor of `conventional` mode for
fixtures where the user designates another source of truth.

## `redlines/…/450945a41c` — PANSS supplementary tables (score 46.32; docxodus as truth)

Scientific S2 table (10 tables, 607 ins / 329 del by "PG3646"). Word paints
the changes **gray `#5d5a58`**, jubarte red; table row heights differ →
Word 4 pages vs jubarte 3 (Word's p4 table content merges up); 1228
reflowed diff lines. **User directive**: use **docxodus as the source of
truth for this pair (better quality)** — i.e. score/handle via jubarte's
other (`conventional`) behavior rather than `--revisions word`
(conventional scores 45.99, word 46.32 — the delta is not the mode; the
directive is about which reference is authoritative).

## `redlines/…/18533edab7` — two-col tab positions demo (82.07; word as truth)

Tiny super_editor test (1 ins + 10 del by "Comparison"). Defects: Word
paints the changes **magenta `#cc3595`** vs jubarte red (see session-color
finding above); TOC dot-leader lines ("Document without sectPrPage …. 1")
extract differently; jubarte p1 draws 27 rules vs Word's 8 (per-word
underline splitting). Page 2 scores 100. **Directive**: Word stays the
source of truth — the color finding above bounds how closely it can be
followed.

## `redlines/with_comments_tracking/6532beda4d` — conversion check: essentially CORRECT (88.19)

"word_tolerated" pair with real comments. Verified: 2 = 2 pages; author
"Comparison" painted **red `#d13438` in BOTH renderers** (the one palette
match of the batch); **comment texts render in both** ('A tachyon walks
into a bar', 'Fin' present in both PDFs); text near-identical (2628 vs 2555
chars). Residual deltas: jubarte draws ~6× more thin rules (63→401 on p1 —
underlines split per word instead of per run) and minor reflow. **Verdict:
no material defect; closest-to-correct fixture of this batch.**

## `redlines/…/06e28e4cef` — check conversion (58.63)

4 = 4 pages, text near-identical; one image per page in both. Differences:
Word paints "Vicky Wragg"'s 93 ins / 58 del in **purple `#b146c2`**,
jubarte red; jubarte p3/p4 draw 839/404 rules vs Word's 35/40 (again
per-word underline/strike splitting); minor reflow. Same class as the
palette finding; no structural conversion defect.

## `redlines/…/754a666443` — "DRAFT" watermark dropped entirely (39.95, 60 pp)

The package's three headers each carry the classic **VML WordArt watermark**:
`<v:shape id="PowerPlusWaterMarkObject…" type="#_x0000_t136" fillcolor="silver"
style="…rotation:315;…mso-position-horizontal:center…">` with
`<v:fill opacity=".5"/><v:textpath style="font-family:Arial" string="DRAFT"/>`,
z-index negative (behind text), 507.6×203 pt centered on the margin.

- **Word**: "DRAFT" diagonally across **all 60 pages** (exported as a big
  translucent PNG, 636×636 pt placement).
- **jubarte**: **no watermark anywhere** — VML `v:textpath` watermarks are
  dropped wholesale (0 images on jubarte's pages).
- Secondary: author "Bo Hurkmans" teal `#005b70` vs jubarte red (palette
  finding), 60 pages of accumulated reflow — but the watermark is the
  headline loss.
- **Fix**: render `PowerPlusWaterMarkObject`-style VML textpath shapes from
  header parts: text from `v:textpath/@string`, `fillcolor` + `v:fill
  @opacity`, rotated per `rotation:315`, centered on the page/margin,
  behind the text layer, on every page that references the header.

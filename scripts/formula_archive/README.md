# Formula scripts archive — jubarte-redlines 0.11.2

Archived as recovered, not maintained: run nothing here without reading it.
The topic folders sit beside this file.

These are the scripts that derived the engine's Word-layout and Word-compare
laws for the 0.11.2 release: probe generators (small docx files varying one
thing), measurers (PyMuPDF/fitz readers of Word's PDFs), reducers (cut a real
document while a behaviour persists), fitters and surveys.

Recovered from four sources, in order:

1. **bench repo** `/Users/arthrod/temp/T/neurotic_docx_bench/scripts/` —
   committed probe scripts (commit given per file). **Caution:** eight
   verdict-era scripts there are still **untracked** — this archive may be
   their only durable copy.
2. **engine worktree** `/Users/arthrod/temp/T/jr-pdf` (`scripts/`,
   `tools/redline40/`).
3. **`/Users/arthrod/temp/T/jubarte-loop/`** — the 2026-09-22..30 campaign.
4. **assistant session transcripts** (`.claude/projects/…jubarte-redlines*.jsonl`)
   — every script whose only home was `/tmp` (wiped by the 2026-10-03/04
   reboot) was replayed from `Write`/`Bash`-heredoc events, with `Edit`
   calls applied in order. Inline `python3 - <<EOF` blocks that were the
   only record of a fit are saved as `inline-<slug>-<timestamp>.py`.

Files that lacked SPDX headers received `AGPL-3.0-only` /
`SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC` lines. Nothing here
was executed. Rotating one-shot generators recovered version by version are
`mk-<timestamp>.py` etc. (latest = highest timestamp).

Engine citations are `grep -n` line numbers in `/Users/arthrod/temp/T/jr-pdf/src`
on branch `feat/pdf-layout-content-controls` (2026-10-03 checkout).


## verdict_kept_span_015

Moved 2026-10-06 to `../../../predict_redline/archive/word-verdict-waves/scripts/formula_archive/verdict_kept_span_015/`, with the verdict-era scripts and its source table (`archive/word-verdict-waves/README.md`). The law it documents is `WORD_LEVEL_KEPT_RATIO = 0.15` in jubarte `src/comparer/mod.rs` (PR #345).

## justify_squeeze_0345

**Law:** Justified-line squeeze: spaces narrow up to 0.25 of their width and the overflow must stay within 0.345 of (last word + 1 space) — `src/convert/mod.rs:31626-31662` (`JUSTIFY_SQUEEZE` :31631, `SQUEEZE_WORD_SHARE = 0.345` :31662, applied :31986-31992). Commit fb2dac33.

| file | provenance | note |
|---|---|---|
| `inline-justify3-boundaries-20261003T1431.py` | inline python (never a file) in session 04b835d2 @ 2026-10-03 14:31 |  |
| `inline-justify4-groups-20261003T1438.py` | inline python (never a file) in session 04b835d2 @ 2026-10-03 14:38 |  |
| `inline-word-space-fit-20261003T1440.py` | inline python (never a file) in session 04b835d2 @ 2026-10-03 14:40 |  |
| `inline-word-space-fit-np-20261003T1440.py` | inline python (never a file) in session 04b835d2 @ 2026-10-03 14:40 |  |
| `probe_justify.py` | bench `scripts/probe_justify.py` — committed e9d13466d | round 1: generator + measure (4 faces, 4-25 spaces) |
| `probe_justify2.py` | bench `scripts/probe_justify2.py` — committed e9d13466d | round 2 |
| `probe_justify3.py` | bench `scripts/probe_justify3.py` — committed e9d13466d | round 3: 23 boundaries at 0.2pt steps → 0.3425..0.35 |
| `probe_justify4.py` | bench `scripts/probe_justify4.py` — committed e9d13466d | round 4: words of 10..38pt |
| `probe_justify_corpus_census.py` | /tmp (wiped by reboot) — transcript | first probe: census of already-squeezed lines in corpus Word PDFs |
| `probe_justify_eval.py` | bench `scripts/probe_justify_eval.py` — committed e9d13466d | eval of justify rounds (741 probes) |


## wp_justify_104

**Law:** WordPerfect justification (`w:wpJustification`): the last word is kept while the line is within 1.04 of its measure — `src/convert/mod.rs:31636-31651` (`WP_SQUEEZE`, line_share 0.04). Commit 17bd3dc7.

| file | provenance | note |
|---|---|---|
| `inline-wpt2-measure-20261003T1902.py` | inline python (never a file) in session 04b835d2 @ 2026-10-03 19:02 |  |
| `probe_wp_justify.py` | bench `scripts/probe_wp_justify.py` — committed 54fd3a3f7 |  |


## markup_pane_scale

**Law:** Word Save-as-PDF All-Markup page scale: k = floor(300·(W−8.64)/(W−mr+265.68))/300, pane 257.3pt wide at 9.15pt past the text edge from x=0.96, top placed by the exact fit half-grid down — `src/convert/pdf.rs:209-282` (`MARKUP_PANE_W` :225, `MARKUP_FIT_INSET = 8.64` :232, `MARKUP_FIT_SPAN = 265.68` :233, `MARKUP_PANE_TABLE` :240-255, `markup_chrome` :257), test at :2092. Commits 250a8045 (exact fit) and 04d7be90 (measured table, 14 geometries, 410 corpus PDFs).

| file | provenance | note |
|---|---|---|
| `inline-pane-fit-iter1-20261003T1513.py` | inline python (never a file) in session 04b835d2 @ 2026-10-03 15:13 |  |
| `inline-pane-fit-iter2-20261003T1514.py` | inline python (never a file) in session 04b835d2 @ 2026-10-03 15:14 |  |
| `inline-pane-fit-iter3-20261003T1515.py` | inline python (never a file) in session 04b835d2 @ 2026-10-03 15:15 |  |
| `inline-pane-fit-np-20261003T1516.py` | inline python (never a file) in session 04b835d2 @ 2026-10-03 15:16 | the least-squares fit that produced a=36, b=1106 300-dpi px = 8.64/265.68 pt over 14 geometries |
| `inline-pane-fit-weighted-20261003T1517.py` | inline python (never a file) in session 04b835d2 @ 2026-10-03 15:17 |  |
| `inline-pane-geo-groups-20261003T1458.py` | inline python (never a file) in session 04b835d2 @ 2026-10-03 14:58 |  |
| `inline-pane-geometry-table-20261003T1455.py` | inline python (never a file) in session 04b835d2 @ 2026-10-03 14:55 |  |
| `inline-pane-harvest-300-20261003T1453.py` | inline python (never a file) in session 04b835d2 @ 2026-10-03 14:53 |  |
| `inline-pane-landscape-fit-20261003T1457.py` | inline python (never a file) in session 04b835d2 @ 2026-10-03 14:57 |  |
| `inline-pane-math-fit-20261003T1454.py` | inline python (never a file) in session 04b835d2 @ 2026-10-03 14:54 |  |
| `inline-pane-validation-harvest-20261003T1457.py` | inline python (never a file) in session 04b835d2 @ 2026-10-03 14:57 | validation set: every corpus comment doc with a Word PDF |
| `paneev.py` | jubarte-loop/paneev.py (on disk) |  |
| `word_balloon_spec.py` | bench `scripts/word_balloon_spec.py` — committed 3f0c5247b | harvests pane/balloon geometry from every corpus comment PDF (writes /tmp/balloon_spec.json) |


## comment_balloons

**Law:** Comment balloon liveness (range end live inside a w:p with content or its own start before it) and balloon geometry (pitch, author colours, labels) — engine `src/convert/mod.rs` `word_balloon_comments` / balloon painter; laws in `docs/WORD_COMMENT_BALLOONS.md`. Commits 4b081e7e (paint balloons), 64088237 (resolved fading, body-level ranges, numbers), c1de25f7 (empty range, round 6), 570e053a (range brackets).

| file | provenance | note |
|---|---|---|
| `comment_balloons_0929/README.md` | bench `scripts/comment_balloons_0929/README.md` — committed d854977a4 (doc) | round-by-round balloon table (doc, not a script) |
| `comment_balloons_0929/ab.py` | bench `scripts/comment_balloons_0929/ab.py` — committed d854977a4 (2026-09-30) |  |
| `comment_balloons_0929/blocklib.py` | bench `scripts/comment_balloons_0929/blocklib.py` — committed d854977a4 (2026-09-30) |  |
| `comment_balloons_0929/round1.py` | bench `scripts/comment_balloons_0929/round1.py` — committed d854977a4 (2026-09-30) |  |
| `comment_balloons_0929/round2.py` | bench `scripts/comment_balloons_0929/round2.py` — committed d854977a4 (2026-09-30) |  |
| `comment_balloons_0929/round3.py` | bench `scripts/comment_balloons_0929/round3.py` — committed d854977a4 (2026-09-30) |  |
| `comment_balloons_0929/round4.py` | bench `scripts/comment_balloons_0929/round4.py` — committed d854977a4 (2026-09-30) |  |
| `comment_balloons_0929/round5.py` | bench `scripts/comment_balloons_0929/round5.py` — committed d854977a4 (2026-09-30) |  |
| `comment_balloons_0929/round6.py` | bench `scripts/comment_balloons_0929/round6.py` — committed f2518bdf5 | round 6: an empty range with its own start gets its balloon (13 shapes, 151/151) |
| `comment_balloons_0929/survey.py` | bench `scripts/comment_balloons_0929/survey.py` — committed d854977a4 (2026-09-30) |  |
| `comment_balloons_0929/survey2.py` | bench `scripts/comment_balloons_0929/survey2.py` — committed d854977a4 (2026-09-30) |  |
| `comment_balloons_0929/survey3.py` | bench `scripts/comment_balloons_0929/survey3.py` — committed d854977a4 (2026-09-30) |  |
| `comment_balloons_0929/survey4.py` | bench `scripts/comment_balloons_0929/survey4.py` — committed d854977a4 (2026-09-30) |  |
| `comment_balloons_0929/survey5.json` | bench `scripts/comment_balloons_0929/survey5.json` — committed f2518bdf5 (data) |  |
| `comment_balloons_0929/survey5.py` | bench `scripts/comment_balloons_0929/survey5.py` — committed d854977a4 (2026-09-30) |  |
| `comment_balloons_0929/survey6.json` | bench `scripts/comment_balloons_0929/survey6.json` — committed f2518bdf5 |  |
| `comment_balloons_0929/survey6.py` | bench `scripts/comment_balloons_0929/survey6.py` — committed f2518bdf5 | survey 6: 151/151 corpus prediction check |
| `detect_review_balloons.py` | bench `scripts/detect_review_balloons.py` — committed b5c99a8ff | finds PDFs where Word shrank the page and drew balloons (the 55-78% gutter law) |
| `inline-balloon-author-colors-20261003T1215.py` | inline python (never a file) in session 04b835d2 @ 2026-10-03 12:15 |  |
| `inline-balloon-census-20261003T1212.py` | inline python (never a file) in session 04b835d2 @ 2026-10-03 12:12 |  |
| `inline-balloon-labels-20261003T1306.py` | inline python (never a file) in session 04b835d2 @ 2026-10-03 13:06 |  |
| `inline-balloon-pitch-fit-20261003T1215.py` | inline python (never a file) in session 04b835d2 @ 2026-10-03 12:15 |  |
| `inline-balloon-spec-vs-docs-20261003T1322.py` | inline python (never a file) in session 04b835d2 @ 2026-10-03 13:22 |  |
| `inline-balloon-spread-stats-20261003T1154.py` | inline python (never a file) in session 04b835d2 @ 2026-10-03 11:54 |  |
| `round6_app_draft.py` | transcript 04b835d2 @ 2026-10-03T13:16 (jubarte-app/round6.py; wiped) | earlier session draft (differs); the FINAL round 6 is bench `comment_balloons_0929/round6.py` (f2518bdf5) |


## footnote_separator

**Law:** Footnote area: separator rule 2in (144pt) wide, the separator note's own paragraph is its height, a last body line brings its space-after over the note area — `src/convert/mod.rs:1578, 1721-1724`; separator strikeout draw `src/convert/font.rs:711-712`. Commit a6fd6d7e; endnote area under the last body line (9134397db6) same commit.

| file | provenance | note |
|---|---|---|
| `enprobe_measure.py` | /tmp (wiped by reboot) — transcript | endnote-area measurer under the last body line |
| `probe_endnote_sep.py` | bench `scripts/probe_endnote_sep.py` — committed fce3fb7cf |  |
| `probe_footnote_sep.py` | bench `scripts/probe_footnote_sep.py` — committed 47e20ef13 |  |


## header_page_break

**Law:** A page/column break in a header/footer paragraph is a line break — `src/convert/mod.rs:21273`. Commit 96dd5227. Header push (content pushes the first line down) and the 75252a6bb0 Texas-statute variants — bench commit 54fd3a3f7, engine in the same 0.11.2 fix series.

| file | provenance | note |
|---|---|---|
| `hpprobe_measure.py` | /tmp (wiped by reboot) — transcript | header-push measurer (line origins per PDF) |
| `probe_header_752.py` | bench `scripts/probe_header_752.py` — committed 54fd3a3f7 |  |
| `probe_header_br.py` | bench `scripts/probe_header_br.py` — committed 716f50455 |  |
| `probe_header_push.py` | bench `scripts/probe_header_push.py` — committed 54fd3a3f7 |  |


## table_top_border

**Law:** A double cell/table border takes three strokes of `sz` of room — `src/convert/mod.rs:3698-3700`. Commit 7d82ab10.

| file | provenance | note |
|---|---|---|
| `oracle30_compare.py` | /tmp (wiped by reboot) — transcript | 30-oracle PDF line comparison used while fitting the border room |
| `probe_table_top.py` | bench `scripts/probe_table_top.py` — committed 666ca3d36 |  |


## list_labels_gutter

**Law:** List labels: a numbering label tabs to a typed left stop inside its hanging gutter (`src/convert/mod.rs:981, 23999` `marker_gutter_stop`), a right-aligned label ends on the first-line indent, a typed label right-aligns on its own stop (`src/convert/mod.rs:967-969, 11963` `list_jc_right`). Commits 5556e51d, ce42256f, 9a307c41; deeper list start c8719ff3; short row spans its grid columns b01bcf9a; right stop wraps 81fb9006.

| file | provenance | note |
|---|---|---|
| `inline-gutter-left-stop-census-20261003T1434.py` | inline python (never a file) in session 04b835d2 @ 2026-10-03 14:34 | corpus census behind 5556e51d (LEFT stop inside the hanging gutter) |
| `inline-numbering-levels-survey-20261003T1358.py` | inline python (never a file) in session 04b835d2 @ 2026-10-03 13:58 | numbering level/start survey behind c8719ff3 (ed36b607e8) |
| `inline-numbering-stops-survey-20261003T1542.py` | inline python (never a file) in session 04b835d2 @ 2026-10-03 15:42 |  |
| `inline-right-label-meetings-probe-20261003T1544.py` | inline python (never a file) in session 04b835d2 @ 2026-10-03 15:44 |  |
| `inline-right-label-roman-probe-20261003T1543.py` | inline python (never a file) in session 04b835d2 @ 2026-10-03 15:43 | right-aligned roman labels behind ce42256f |
| `inline-short-row-grid-survey-20261003T1346.py` | inline python (never a file) in session 04b835d2 @ 2026-10-03 13:46 | short-row vs grid-columns survey behind b01bcf9a (25f1d311bd) |
| `probe_list_label.py` | bench `scripts/probe_list_label.py` — on disk, **untracked** (never committed) |  |
| `survey_deeperfirst.py` | /tmp/survey_deeperfirst.py (wiped by reboot) — sessions 04b835d2, last 2026-10-03T14:02 |  |


## fonts_embedded

**Law:** Fonts: an installed family wins over the document's embedded copy (commit f4d83c85, `src/convert/font.rs:1213-1217`), Times New Roman for a font-less rPrDefault (733599a0), Courier New letter-space Tc≈-0.0015 at 11.04pt and -0.0018 at 16.08 (`src/convert/font.rs:264-280`), Word's own substitutes for absent fonts (94252fb5), number labels/scripts paint in Word's faces (7346398d).

| file | provenance | note |
|---|---|---|
| `fontscan.py` | /tmp/fontscan.py (wiped by reboot) — sessions 789a7d33,a44a16de, last 2026-09-25T02:19 |  |
| `inline-fonts-census-pdfs-20261003T1327.py` | inline python (never a file) in session 04b835d2 @ 2026-10-03 13:27 |  |
| `inline-fonts-dfonts-widths-20261003T1424.py` | inline python (never a file) in session 04b835d2 @ 2026-10-03 14:24 | measures Word's bundled DFonts faces (widths, line gap) |
| `inline-fonts-embedded-survey-20261003T1328.py` | inline python (never a file) in session 04b835d2 @ 2026-10-03 13:28 | embedded vs painted fonts (8c11ad13af embeds TNR 7.00) |
| `inline-fonts-rprdefault-survey-20261003T1333.py` | inline python (never a file) in session 04b835d2 @ 2026-10-03 13:33 |  |
| `model_pspacing.py` | /tmp/model_pspacing.py (wiped by reboot) — sessions 33fff59e, last 2026-09-27T07:33 |  |
| `survey_courier.py` | /tmp/survey_courier.py (wiped by reboot) — sessions 04b835d2, last 2026-10-03T14:09 | Courier New spans in corpus PDFs → the Tc≈-0.0015 re-verification |
| `survey_defaults.py` | /tmp/survey_defaults.py (wiped by reboot) — sessions 04b835d2, last 2026-10-03T13:27 |  |
| `survey_stalespan.py` | /tmp/survey_stalespan.py (wiped by reboot) — sessions 04b835d2, last 2026-10-03T13:47 |  |


## html_auto_spacing

**Law:** HTML auto spacing: fixed `w:beforeAutospacing`/`w:afterAutospacing` keeps the explicit before/after; without it paragraph spacing adds up; attributes inherit one by one — `src/convert/mod.rs:902, 3408, 3464, 3548-3556`. Commits b9315128, 6bb7f8b8, c84dd3db.

| file | provenance | note |
|---|---|---|
| `inline-autospacing-census-20261003T1437.py` | inline python (never a file) in session 04b835d2 @ 2026-10-03 14:37 |  |


## punct_squeeze_compat14

**Law:** Before compatibility mode 15, `compressPunctuation` narrows a line's spaces by a fifth (Times/Arial faces) — `src/convert/mod.rs:31664-31680` (`PUNCT_SQUEEZE`, `compressed_space_face`). Commit 77b8404f (probes at 12pt compat 14).

| file | provenance | note |
|---|---|---|
| `mk13.py` | /Users/arthrod/temp/T/jubarte-redlines/mk13.py (no longer on disk) — transcript ad855928 (2026-10-01/02) |  |
| `mk14.py` | /Users/arthrod/temp/T/jubarte-redlines/mk14.py (no longer on disk) — transcript ad855928 (2026-10-01/02) |  |
| `mk15.py` | /Users/arthrod/temp/T/jubarte-redlines/mk15.py (no longer on disk) — transcript ad855928 (2026-10-01/02) |  |
| `mk16.py` | /Users/arthrod/temp/T/jubarte-redlines/mk16.py (no longer on disk) — transcript ad855928 (2026-10-01/02) |  |
| `mk6.py` | /Users/arthrod/temp/T/jubarte-redlines/mk6.py (no longer on disk) — transcript ad855928 (2026-10-01/02) |  |
| `mk8.py` | /Users/arthrod/temp/T/jubarte-redlines/mk8.py (no longer on disk) — transcript ad855928 (2026-10-01/02) |  |
| `mk9.py` | /Users/arthrod/temp/T/jubarte-redlines/mk9.py (no longer on disk) — transcript ad855928 (2026-10-01/02) |  |
| `sqprobe.py` | /Users/arthrod/temp/T/jubarte-redlines/sqprobe.py (no longer on disk) — transcript ad855928 (2026-10-01/02) | square-shape squeeze probe (conejo) |


## word_classes

**Law:** A Word-Compare word is a maximal run of one character class — engine `src/comparer/units.rs` `word_class`; law + fixtures `tokens/classes_*` in `docs/WORD_COMPARE_RULES.md`. Commit c885710a (2026-10-01).

| file | provenance | note |
|---|---|---|
| `mk3.py` | /Users/arthrod/temp/T/jubarte-redlines/mk3.py (no longer on disk) — transcript ad855928 (2026-10-01/02) | character-class pair table → tokens/classes fixtures |
| `mk4.py` | /Users/arthrod/temp/T/jubarte-redlines/mk4.py (no longer on disk) — transcript ad855928 (2026-10-01/02) |  |
| `mk5.py` | /Users/arthrod/temp/T/jubarte-redlines/mk5.py (no longer on disk) — transcript ad855928 (2026-10-01/02) |  |
| `mk7.py` | /Users/arthrod/temp/T/jubarte-redlines/mk7.py (no longer on disk) — transcript ad855928 (2026-10-01/02) |  |


## misc_layout_probes_1001

**Law:** The 2026-10-01/02 layout probes named in `docs/WORD_LAYOUT_RULES.md`: probe_adj (adjacent centred tables, :295), probe_cx (contextual spacing, :420), probe_sum (exact lines + before/after, :429), probe_il (inline pictures, :535), plus sdt-wrapped rows (8332c2df), VML/AlternateContent pictures, autofit tables, grid probes.

| file | provenance | note |
|---|---|---|
| `conejo_boxpos.py` | /tmp/conejo/… (wiped) — transcript ad855928 |  |
| `conejo_chars.py` | /tmp/conejo/… (wiped) — transcript ad855928 |  |
| `conejo_fontpar.py` | /tmp/conejo/… (wiped) — transcript ad855928 |  |
| `conejo_glyphfont.py` | /tmp/conejo/… (wiped) — transcript ad855928 |  |
| `conejo_gp_mk.py` | /tmp/conejo/… (wiped) — transcript ad855928 |  |
| `conejo_hira.py` | /tmp/conejo/… (wiped) — transcript ad855928 |  |
| `conejo_probecmp.py` | /tmp/conejo/… (wiped) — transcript ad855928 |  |
| `floor.py` | /Users/arthrod/temp/T/jubarte-redlines/floor.py (no longer on disk) — transcript ad855928 (2026-10-01/02) |  |
| `gen-20261001T1345.py` | /Users/arthrod/temp/T/jubarte-redlines/gen-20261001T1345.py (no longer on disk) — transcript ad855928 (2026-10-01/02) |  |
| `gen-20261001T2340.py` | /Users/arthrod/temp/T/jubarte-redlines/gen-20261001T2340.py (no longer on disk) — transcript ad855928 (2026-10-01/02) |  |
| `gen-20261001T2357.py` | /Users/arthrod/temp/T/jubarte-redlines/gen-20261001T2357.py (no longer on disk) — transcript ad855928 (2026-10-01/02) |  |
| `gen-20261002T0006.py` | /Users/arthrod/temp/T/jubarte-redlines/gen-20261002T0006.py (no longer on disk) — transcript ad855928 (2026-10-01/02) |  |
| `gen2.py` | /Users/arthrod/temp/T/jubarte-redlines/gen2.py (no longer on disk) — transcript ad855928 (2026-10-01/02) |  |
| `gen3.py` | /Users/arthrod/temp/T/jubarte-redlines/gen3.py (no longer on disk) — transcript 6cc5b2a3 (2026-09-30, floating-table/text-box era) |  |
| `gen4.py` | /Users/arthrod/temp/T/jubarte-redlines/gen4.py (no longer on disk) — transcript 6cc5b2a3 (2026-09-30, floating-table/text-box era) |  |
| `hint.py` | /Users/arthrod/temp/T/jubarte-redlines/hint.py (no longer on disk) — transcript ad855928 (2026-10-01/02) |  |
| `inline-sdt-cell-probe-20261003T1139.py` | inline python (never a file) in session 04b835d2 @ 2026-10-03 11:39 | sdt-wrapped table rows (8332c2df) |
| `mk-20261001T092131.py` | /Users/arthrod/temp/T/jubarte-redlines/mk.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk-20261001T092843.py` | /Users/arthrod/temp/T/jubarte-redlines/mk.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk-20261001T095943.py` | /Users/arthrod/temp/T/jubarte-redlines/mk.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk-20261001T111928.py` | /Users/arthrod/temp/T/jubarte-redlines/mk.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk-20261001T130137.py` | /Users/arthrod/temp/T/jubarte-redlines/mk.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk-20261001T141041.py` | /Users/arthrod/temp/T/jubarte-redlines/mk.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk-20261001T141059.py` | /Users/arthrod/temp/T/jubarte-redlines/mk.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk-20261001T141625.py` | /Users/arthrod/temp/T/jubarte-redlines/mk.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk-20261001T142653.py` | /Users/arthrod/temp/T/jubarte-redlines/mk.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk-20261001T142755.py` | /Users/arthrod/temp/T/jubarte-redlines/mk.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk-20261001T145947.py` | /Users/arthrod/temp/T/jubarte-redlines/mk.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk-20261001T151730.py` | /Users/arthrod/temp/T/jubarte-redlines/mk.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk-20261001T152647.py` | /Users/arthrod/temp/T/jubarte-redlines/mk.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk-20261001T152845.py` | /Users/arthrod/temp/T/jubarte-redlines/mk.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk-20261001T152932.py` | /Users/arthrod/temp/T/jubarte-redlines/mk.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk-20261001T155912.py` | /Users/arthrod/temp/T/jubarte-redlines/mk.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk-20261001T172938.py` | /Users/arthrod/temp/T/jubarte-redlines/mk.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk-20261001T173000.py` | /Users/arthrod/temp/T/jubarte-redlines/mk.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk-20261002T041300.py` | /Users/arthrod/temp/T/jubarte-redlines/mk.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk-20261002T053436.py` | /Users/arthrod/temp/T/jubarte-redlines/mk.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk-20261002T053820.py` | /Users/arthrod/temp/T/jubarte-redlines/mk.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk-20261002T054955.py` | /Users/arthrod/temp/T/jubarte-redlines/mk.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk-20261002T055657.py` | /Users/arthrod/temp/T/jubarte-redlines/mk.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk-20261002T060421.py` | /Users/arthrod/temp/T/jubarte-redlines/mk.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk-20261002T061002.py` | /Users/arthrod/temp/T/jubarte-redlines/mk.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk-20261002T062653.py` | /Users/arthrod/temp/T/jubarte-redlines/mk.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk-20261002T083541.py` | /Users/arthrod/temp/T/jubarte-redlines/mk.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk-20261002T092356.py` | /Users/arthrod/temp/T/jubarte-redlines/mk.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk-20261002T135138.py` | /Users/arthrod/temp/T/jubarte-redlines/mk.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk-20261002T135224.py` | /Users/arthrod/temp/T/jubarte-redlines/mk.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk-20261002T135932.py` | /Users/arthrod/temp/T/jubarte-redlines/mk.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk-20261002T140005.py` | /Users/arthrod/temp/T/jubarte-redlines/mk.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk-20261002T141824.py` | /Users/arthrod/temp/T/jubarte-redlines/mk.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk-20261002T142203.py` | /Users/arthrod/temp/T/jubarte-redlines/mk.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk-20261002T143224.py` | /Users/arthrod/temp/T/jubarte-redlines/mk.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk-20261002T143359.py` | /Users/arthrod/temp/T/jubarte-redlines/mk.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk-20261002T143759.py` | /Users/arthrod/temp/T/jubarte-redlines/mk.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk2-20261001T142823.py` | /Users/arthrod/temp/T/jubarte-redlines/mk2.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk2-20261001T142851.py` | /Users/arthrod/temp/T/jubarte-redlines/mk2.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk2-20261001T142910.py` | /Users/arthrod/temp/T/jubarte-redlines/mk2.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk2-20261001T143016.py` | /Users/arthrod/temp/T/jubarte-redlines/mk2.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk2-20261001T150121.py` | /Users/arthrod/temp/T/jubarte-redlines/mk2.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk2-20261002T085756.py` | /Users/arthrod/temp/T/jubarte-redlines/mk2.py version (rotating file, no longer on disk) — transcript ad855928 |  |
| `mk49d.py` | /Users/arthrod/temp/T/jubarte-redlines/mk49d.py (no longer on disk) — transcript ad855928 (2026-10-01/02) |  |
| `mk_adj.py` | /Users/arthrod/temp/T/jubarte-redlines/mk_adj.py (no longer on disk) — transcript ad855928 (2026-10-01/02) | probe_adj: centred 453pt table then 441pt |
| `mk_adj2.py` | /Users/arthrod/temp/T/jubarte-redlines/mk_adj2.py (no longer on disk) — transcript ad855928 (2026-10-01/02) |  |
| `mk_adj3.py` | /Users/arthrod/temp/T/jubarte-redlines/mk_adj3.py (no longer on disk) — transcript ad855928 (2026-10-01/02) |  |
| `mk_adj4.py` | /Users/arthrod/temp/T/jubarte-redlines/mk_adj4.py (no longer on disk) — transcript ad855928 (2026-10-01/02) |  |
| `mk_af.py` | /Users/arthrod/temp/T/jubarte-redlines/mk_af.py (no longer on disk) — transcript ad855928 (2026-10-01/02) |  |
| `mk_il.py` | /Users/arthrod/temp/T/jubarte-redlines/mk_il.py (no longer on disk) — transcript ad855928 (2026-10-01/02) | probe_il: inline pictures with/without trailing space |
| `mkp.py` | /Users/arthrod/temp/T/jubarte-redlines/mkp.py (no longer on disk) — transcript ad855928 (2026-10-01/02) |  |
| `zedit.py` | /Users/arthrod/temp/T/jubarte-redlines/zedit.py (no longer on disk) — transcript ad855928 (2026-10-01/02) |  |


## stories_vml_probes_0928

**Law:** Story/VML/OLE probes behind the 5a6c parity fixes: OLE pictures kept in redlines (#337, 5d69b1ff), VML descent (#336, 6999951c), whole-document story edits.

| file | provenance | note |
|---|---|---|
| `py_whole.py` | /tmp/py_whole.py (wiped by reboot) — sessions 868e6e2a, last 2026-09-28T21:46 |  |
| `stories_edit1.py` | /tmp/stories_edit1.py (wiped by reboot) — sessions 868e6e2a, last 2026-09-28T21:58 |  |
| `stories_edit2.py` | /tmp/stories_edit2.py (wiped by reboot) — sessions 868e6e2a, last 2026-09-28T21:59 |  |
| `stories_edit3.py` | /tmp/stories_edit3.py (wiped by reboot) — sessions 868e6e2a, last 2026-09-28T22:00 |  |
| `stories_edit4.py` | /tmp/stories_edit4.py (wiped by reboot) — sessions 868e6e2a, last 2026-09-28T22:01 |  |
| `stories_inspect.py` | /tmp/stories_inspect.py (wiped by reboot) — sessions 868e6e2a, last 2026-09-28T21:57 |  |
| `whole_docs.py` | /tmp/whole_docs.py (wiped by reboot) — sessions 868e6e2a, last 2026-09-28T21:46 |  |
| `whole_edit.py` | /tmp/whole_edit.py (wiped by reboot) — sessions 868e6e2a, last 2026-09-28T21:41 |  |
| `whole_edit2.py` | /tmp/whole_edit2.py (wiped by reboot) — sessions 868e6e2a, last 2026-09-28T21:42 |  |
| `whole_edit3.py` | /tmp/whole_edit3.py (wiped by reboot) — sessions 868e6e2a, last 2026-09-28T21:42 |  |


## word_drivers

**Law:** The Word automation drivers every probe above runs through (Word for Mac Quartz print path). Not a law themselves; they are the measurement instrument.

| file | provenance | note |
|---|---|---|
| `ab.sh` | jubarte-loop/ab.sh (on disk) |  |
| `check_redline_identity.py` | bench `scripts/check_redline_identity.py` — committed b5c99a8ff |  |
| `endpoint_word.py` | moved 2026-10-04 to `../../../predict_redline/methodology/endpoint_word.py` | compare and convert client. A copy may remain under `formula_archive/` as the older snapshot. |
| `redline_word_measure.sh` | /tmp/redline_word_measure.sh (wiped by reboot) — sessions 33fff59e, last 2026-09-26T19:13 | measure driver, 4 revisions (0926 campaign) |
| `run_pdf4_chain.sh` | /tmp/run_pdf4_chain.sh (wiped by reboot) — sessions 04b835d2, last 2026-10-03T12:50 |  |
| `run_pdf5_chain.sh` | /tmp/run_pdf5_chain.sh (wiped by reboot) — sessions 04b835d2, last 2026-10-03T13:08 |  |
| `run_pdf6_chain.sh` | /tmp/run_pdf6_chain.sh (wiped by reboot) — sessions 04b835d2, last 2026-10-03T13:19 |  |
| `run_pdf7_chain.sh` | /tmp/run_pdf7_chain.sh (wiped by reboot) — sessions 04b835d2, last 2026-10-03T13:38 |  |
| `run_pdf8_chain.sh` | /tmp/run_pdf8_chain.sh (wiped by reboot) — sessions 04b835d2, last 2026-10-03T13:52 |  |
| `run_pdf9_chain.sh` | /tmp/run_pdf9_chain.sh (wiped by reboot) — sessions 04b835d2, last 2026-10-03T14:02 |  |
| `run_pdfcomments_chain.sh` | /tmp/run_pdfcomments_chain.sh (wiped by reboot) — sessions 04b835d2, last 2026-10-03T12:42 |  |
| `run_pdflist.sh` | /tmp/run_pdflist.sh (wiped by reboot) — sessions 04b835d2, last 2026-10-03T17:35 |  |
| `word-open-probe.sh` | jr-pdf `scripts/word-open-probe.sh` — committed 16de3f89 (2026-07-24) |  |
| `word-probe-sweep.sh` | jr-pdf `scripts/word-probe-sweep.sh` — committed a90f0129 (2026-09-05) |  |
| `word_ab_ext.sh` | jubarte-loop/word_ab_ext.sh (on disk) |  |
| `word_pdf.py` | bench `scripts/word_pdf.py` — committed a426ed950 | the audited Word→PDF driver (drives Word for Mac; every PDF probe runs through it) |
| `word_pdf_focus.py` | bench `scripts/word_pdf_focus.py` — committed 8dfd615d2 |  |
| `word_redline.py` | bench `scripts/word_redline.py` — committed a426ed950 | the audited Word Compare driver |
| `word_validate_batch.py` | bench `scripts/word_validate_batch.py` — committed d46e9183b |  |
| `word_watchdog.sh` | jubarte-loop/word_watchdog.sh (on disk) |  |
| `wordlane.sh` | /tmp/wordlane.sh (wiped by reboot) — sessions 04b835d2, last 2026-10-03T20:50 |  |


## sample_holdout_score

**Law:** Sample/holdout drawing and scoring used to validate every law against Word (300-doc control, holdout gate, 40-pair guard).

| file | provenance | note |
|---|---|---|
| `holdchain.sh` | /tmp/holdchain.sh (wiped by reboot) — sessions 04b835d2, last 2026-10-03T17:43 |  |
| `holdchain2.sh` | /tmp/holdchain2.sh (wiped by reboot) — sessions 04b835d2, last 2026-10-03T19:21 |  |
| `holdchain3.sh` | /tmp/holdchain3.sh (wiped by reboot) — sessions 04b835d2, last 2026-10-03T20:41 |  |
| `pdf_sample_report.py` | bench `scripts/pdf_sample_report.py` — committed fb69f1aff |  |
| `redline40.py` | jr-pdf `tools/redline40/redline40.py` — committed 7ad7ef68 (2026-09-28) |  |
| `redline_sample_score.py` | bench `scripts/redline_sample_score.py` — committed 1cb68485a |  |
| `run_pdf300.sh` | /tmp/run_pdf300.sh (wiped by reboot) — sessions 04b835d2, last 2026-10-03T12:37 |  |
| `select_holdout.py` | /tmp (wiped by reboot) — transcript | drew the holdout list after the pool baseline |


## pdf300_diagnosis

**Law:** Word-vs-ours PDF measurers used across the /tmp/pdf-300 build loop (line dumps, tail lines, per-doc diagnosis, side-by-side compositing).

| file | provenance | note |
|---|---|---|
| `pdfdiag.py` | /tmp/pdfdiag.py (wiped by reboot) — sessions 04b835d2, last 2026-10-03T14:47 |  |
| `pdflines.py` | /tmp/pdflines.py (wiped by reboot) — sessions 04b835d2, last 2026-10-03T16:43 |  |
| `pdftail.py` | /tmp/pdftail.py (wiped by reboot) — sessions 04b835d2, last 2026-10-03T16:42 |  |
| `sbs.py` | /tmp (wiped by reboot) — transcript |  |


## loop_surveys_0922_0930

**Law:** Earlier campaign (2026-09-22..30) surveys and builders: pane/picture events over fixtures_500, line pitch, line agreement, rule censuses, docx builders.

| file | provenance | note |
|---|---|---|
| `base.py` | jubarte-loop/base.py (on disk) |  |
| `ceiling.py` | jubarte-loop/ceiling.py (on disk) |  |
| `docxedit.py` | jubarte-loop/docxedit.py (on disk) |  |
| `en_pages.py` | jubarte-loop/en_pages.py (on disk) |  |
| `en_pdf_identity.py` | /tmp (wiped by reboot) — transcript |  |
| `exactev.py` | jubarte-loop/exactev.py (on disk) |  |
| `groupdocs_compare.py` | jubarte-loop/groupdocs_compare.py (on disk) |  |
| `holdcmp.py` | jubarte-loop/holdcmp.py (on disk) |  |
| `lineagree.py` | jubarte-loop/lineagree.py (on disk) |  |
| `metrics4.py` | jubarte-loop/metrics4.py (on disk) |  |
| `mkdocx.py` | /tmp/mkdocx.py (wiped by reboot) — sessions 789a7d33, last 2026-09-24T18:10 | the minimal docx builder every loop-era probe used |
| `mkdocx_tmp.py` | /tmp (wiped by reboot) — transcript |  |
| `mknum.py` | /tmp/mknum.py (wiped by reboot) — sessions 789a7d33,a44a16de, last 2026-09-24T20:42 |  |
| `mkset.py` | /tmp/mkset.py (wiped by reboot) — sessions 789a7d33,a44a16de, last 2026-09-24T23:17 |  |
| `pdf_identity.py` | jubarte-loop/pdf_identity.py (on disk) |  |
| `pdfcmp.py` | jubarte-loop/pdfcmp.py (on disk) |  |
| `pitch.py` | /tmp (wiped by reboot) — transcript |  |
| `rules3.py` | jubarte-loop/rules3.py (on disk) |  |
| `wordflag.py` | jubarte-loop/wordflag.py (on disk) |  |


## Inputs the scripts need, and whether they still exist

- `neurotic_docx_bench/corpus/word/` (documents.csv, comparisons.csv, per-state
  docx + Word PDFs) — **exists**. Used by corpus_verdicts, word_balloon_spec,
  surveys, justify census, fonts surveys, balloon rounds.
- `jubarte-app/_scratch/redline-traversal-flow/probes/` (waves wave1..8,
  short1/2, asym1, denom1, edge1, edits1, prose1, tokens, variants, punct1,
  with A/B docx, Word redlines and Word verdict CSVs; `WORD_RULE.md` is the
  law's lab notebook) — **exists** on disk in the canonical checkout.
- `/Users/arthrod/temp/T/grok_run_archive/justify_1003 … justify4_1003,
  comment_balloons_0929` — **exists** (probe docx + manifests + Word PDFs for
  the squeeze rounds and the balloon rounds).
- `neurotic_docx_bench/grok_run/fixtures_500` — **exists** (loop-era surveys).
- Word work dirs under `/tmp`: `pdf-300` (300-doc control), `wpt2` (WordPerfect),
  `hpprobe`, `enprobe`, `oracle30`, `pdf-hold`, `balloon_spec.json`,
  `heckel_rows.json`, `measure_rows*.json`, `charfit_rows.json` (charfit_rows
  also survives in the probes dir) — **gone** (reboot). The scripts that read
  them are kept for the record; rerunning means regenerating the dirs with the
  drivers in `word_drivers/` and `sample_holdout_score/`.

## Laws cited in commits / CHANGELOG / WORD_DIFFERENCES with NO recovered script

- **Pattern shading (`w:shd`) and auto-text-on-dark luma < 75**
  (WORD_LAYOUT_RULES; commits 22a7d85, 6457d28) — probes predate the
  2026-09-20 transcripts available here; not recovered.
- **Revision "by author" 20-colour palette** (8cc34c4) — same era; not recovered.
- **gridBefore/gridAfter skip as wide as its grid columns** (0ffbfc28) — no
  dedicated probe generator existed; the evidence is corpus documents
  (ed36b607e8) measured through the inline surveys exported under
  `list_labels_gutter/` and the engine fix itself.
- **Bracket-pair squeeze beside another bracket** (861f4740,
  `src/convert/mod.rs:6733-6734`) — derived in inline transcript blocks not
  preserved as files; not recovered as a script.
- **word_device_pt: Word paints text snapped to 1/300in grid units**
  (`src/convert/mod.rs:807-810`, 72/300 = 0.24) — measured in inline blocks
  over corpus PDFs; no standalone script recovered.
- **5a6c parity: header STYLEREF, WMF text, VML 143-dpi pixel snap**
  (45c82440 / b967b96c / d194c185) — probes lived in worktree scratch dirs;
  only the story/VML family (`stories_vml_probes_0928/`) was recovered.
- **East-Asian ascii-face retention and the Latin↔CJK half-gap**
  (69f30e27) — partially covered by the `word_classes/` and rotating `mk`
  versions; the specific fit scripts were inline and are not recovered.
- **cell hang `hang_spaces` probes c028/n028** (`src/convert/mod.rs:31676`,
  Word probes 2026-10-02) — generated by rotating `mk`/`mk2` versions of
  2026-10-02 (exported under `misc_layout_probes_1001/`) but not separable
  by name; treat those versions as the closest record.

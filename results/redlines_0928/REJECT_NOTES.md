# Rejected track, 2026-09-29: why jubarte-rust trails

Scores (pagefair, MPS scorer): jubarte-rust 100/100, mean 64.55, median 58.29;
docxodus 96/100 (4 redlines Word cannot open), mean 73.22, median 78.23;
superdoc 8/8, mean 97.63.

Word's own Reject All of its compare reproduces the base document (checked on 029c0275ad: 1
page, same text as the base's Word PDF). docxodus's reject does the same there; jubarte's
reject runs to 4 pages.

Measured over all 100 pairs (Word's rejected DOCX against jubarte's rejected DOCX):

| check | pairs | mean score | pairs under 60 |
|---|---|---|---|
| text after reject identical to Word's | 99 | 65.0 | 51 |
| text differs | 1 | 24.6 | 1 |
| any style definition differs after reject | 74 | 53.9 | 51 |
| no style definition differs | 26 | 94.9 | 1 |
| run rPr differs | 69 | 56.6 | 44 |
| paragraph pPr differs | 70 | 59.7 | 42 |
| page geometry (pgSz, pgMar, cols) differs | 10 | 49.2 | 9 |
| more paragraphs than Word's reject | 11 | | 6 of the 52 under 60 |

So jubarte's redline rejects to the right text, but the style definitions Word keeps
after rejecting it are not the base's: 51 of the 52 pairs under 60 have a style that differs.
jubarte does write style-level change records (styles.xml `w:rPrChange`/`w:pPrChange` in 58
of its 100 redlines, Word in 63, both in 57), so the gap is in what those records hold, not
whether they exist. Next step for jubarte-redlines: diff one pair's styles.xml records
against Word's (see the style-collision memory: Word keeps B live and records A per
attribute).

The first hypothesis tried (untracked paragraph marks, table rows and section breaks
surviving the reject, seen on 029c0275ad) explains only 6 of the 52 low pairs.

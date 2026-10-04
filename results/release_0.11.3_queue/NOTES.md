# Conversion queue after 0.11.2: what is measured, what is only suspected

Source: `queue.tsv` (550 documents, worst first), `control50.txt` (49 documents
never diagnosed), `prediction.json`, `first_divergence.jsonl`.
Binary: the 0.11.2 candidate (`jubarte-pdf29`, sha256 07d95d28…, engine 14bf38cf).

## Measured

1. **A page count that is not Word's costs about 37 points.** 529 matching
   documents score a median 81.13, 22 differing ones 44.16 (gap 36.97, 95%
   interval 28.29 to 38.31). The control holds one mismatch, too few to test
   the claim there; it is a claim about the queue only.
2. **A page break ending the last body paragraph is not a rule.** 3 of 7,138
   corpus documents have the shape: one is +1 page in jubarte (ea023ca156,
   queue rank 1), one matches Word (e015887f5e, the page exists in both), one
   is −1. Refuted as stated. ea023ca156 differs from the other two by a
   comment reference in that paragraph and a table before it; n = 1, no rule.
3. **Ranks 15 to 19 are one base document** (file_114/115, file_99/100,
   file_195/196, small_font_size_demo ×2): 14 pages in Word, 13 in jubarte,
   scores 43.45 to 44.58. Page by page on 0aa6426932 (rank 15):
   - Word's page 6 ends before "Save time in Word…"; jubarte fits that line
     on page 6. On page 6 Word paints the OMML equation built up, about five
     text lines tall; jubarte paints it as one linear line
     ("x+an=∑k=0nnkxkan-k").
   - Page 7, Word: list ends y 197.2, text box text y 218.9, the embedded
     Excel sheet's cells y 343.6 to 388.5, then a page break before
     "Heading1". jubarte: list ends y 177.0, text box text y 198.5,
     "Heading1" at y 333.5 on the same page.
   - The sheet is a `w:object` with a VML shape of 362.05 × 146.1 pt.
     jubarte paints an image of 288 × 116 pt there (384 × 171 px at 96 × 106
     ppi), a scale of 0.795.
   - After the table of contents Word starts a page at "Heading 1"; jubarte
     keeps the four headings on the page of the contents.

## Suspected, not tested (each needs a rebuild or a Word probe)

- H-math: a display equation's height is the built-up height, not one line.
  Corpus test available without Word: documents with `m:oMathPara` against
  the base rate of −1 page.
- H-object: an inline `w:object` takes the size its VML style states; the
  0.795 scale is ours. Corpus test available: documents with `w:object`.
- H-box: Word keeps a `spAutoFit` text box at its stored extent for layout
  (110.6 pt here: the sheet starts about 125 pt under the box's text), where
  jubarte shrinks it. Needs a Word probe; the stored extent may simply be what
  Word last computed.
- Unexplained: why Word breaks before "Heading1" with about 245 pt left on
  page 7. No hypothesis survives the numbers above; do not code against it.

Nothing above has been turned into engine code. Cargo was held by the 0.11.2
release run while this was written.

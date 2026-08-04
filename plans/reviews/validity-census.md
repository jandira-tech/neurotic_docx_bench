# Schema-validity census — and why this benchmark cannot price it

Measured 2026-08-04 by the `stage2-R2-inplace-rust` session across 504 pairs, recorded
here because it is a programme-level fact and was otherwise living only in
`NOTES-deferred.md` on an unmerged branch.

## The census

| population | invalid | rate |
|---|---:|---:|
| a **source** document is already invalid | 226 / 504 | 44.8% |
| **our** output is invalid | 157 / 504 | 31.2% |
| our output is invalid **from clean inputs** | **55 / 504** | **10.9%** |
| **Word's own comparison output** is invalid | **49 / 504** | **9.7%** |

Four readings, in order of how much they should change behaviour:

1. **55/504 is the number that isolates us.** Invalid output from valid input is
   unambiguously our defect — no upstream excuse, no inherited breakage. It is the
   figure to drive to zero, and it is the only one of the four that is purely ours.

2. **Word's own output is invalid on 9.7% of pairs.** The oracle we are scored against
   does not itself hold byte-level schema validity. That is not a licence to be sloppy,
   but it does mean **"match Word" and "be schema-valid" are not the same target**, and a
   plan that assumes they are will chase the wrong one. Where they conflict, Arthur's
   definition of *Word valid* — opens in Microsoft Word with no warning, error, or repair
   offer — is the governing standard, not the XSD.

3. **44.8% of source documents are already invalid.** The corpus is largely built from
   real-world and adversarial documents, so this is a property of the input, not a corpus
   defect. It does mean a validity metric must always be reported as a *delta* against
   the input, never as an absolute.

4. Our 31.2% absolute minus the 10.9% clean-input figure is mostly inherited invalidity
   passing through. Passing invalid input through unchanged is defensible; **introducing**
   invalidity is not.

## Why the benchmark cannot see any of this

**Our oracle renders through LibreOffice.** Every score in this programme is a pixel
comparison of a LibreOffice render against a LibreOffice render. Schema validity does not
appear in that measurement at any point.

This was proved today, not assumed. The jubarte-first fix `d99ccb5b3` took dangling
`Ttulo1..9` references in `word/numbering.xml` from **7 → 0**, with `numbering.xml` a
changed part on all seven repaired documents — and **all seven scored bit-identically
before and after**, contributing to a corpus-wide delta of exactly **0.0000 across all
763 documents**. LibreOffice does not read the style→numbering binding
(`w:lvl/w:pStyle`, `w:styleLink`, `w:numStyleLink`), so a correct repair to it is
invisible by construction.

### The defects this blinds us to

Four found in one day, all real in Word, all unpriceable here:

| defect | status |
|---|---|
| dangling style refs in `numbering.xml` after a styleId rename | fixed (`d99ccb5b3`), scored **0.0000** |
| `w:numPr` children emitted `numId,ilvl` — `CT_NumPr` sequence is `ilvl,numId` | fixed on `feat/numpr-child-order`; Word's oracle 0/504 |
| `w:tblGridChange` carrying `w:author`/`w:date` — `CT_TblGridChange` is the one revision element **not** extending `CT_TrackChange` | fixed; Word's oracle writes `w:id` alone on all 45 elements across 34 documents |
| `word/people.xml` dropped while `w:ins`/`w:del` author attributes are retained | open |

The third overturned an existing repo assertion that demanded `author`/`date` with the
comment "Word records both." The repo's own schema says `['w:id']` and the oracle agrees.
**A test encoding an assumption, refuted by the oracle, is the right kind of test to
change** — and it is recorded as an overturn rather than a quiet edit.

Measured effect of those two Rust fixes: invalid **103 → 93**, author/date **55 → 0**,
ordering **287 → 244**, all other classes unchanged, and **zero documents gained an
error**.

## The consequence, stated plainly

**A pixel score against a LibreOffice oracle is structurally incapable of measuring Word
validity, and this programme's headline numbers therefore say nothing about it.** Every
engine could be driven to a perfect score while emitting documents Word offers to repair,
and nothing in the current benchmark would notice.

Two things follow, and neither is optional if these numbers are published:

- The validity census belongs **alongside** the score table, not in a plan appendix. It
  is the only evidence we have on a dimension the score cannot reach.
- **Whether the oracle should be Word rather than LibreOffice is now the largest open
  question in the programme** — larger than any individual engine fix, because it
  determines whether a whole class of real defect is measurable at all. Raised for
  Arthur's decision; not actionable unilaterally, since it would invalidate every
  recorded score.

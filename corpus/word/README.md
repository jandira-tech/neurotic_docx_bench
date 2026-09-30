# The Word corpus

What Microsoft Word produced, gathered from its working folders by `bench corpus build`
(the set table is `DOCSETS` in `neurotic_docx_bench/word_corpus.py`). Every file here is a
copy; the origins were not moved or deleted. Only what Word finished is here: a docx Word
could not open, a document or compare it did not render in a render run, a blacklisted
document with the pairs that touch it, and a PDF another producer made are listed per set in
`PROVENANCE.json` (`excluded`, `absent`, `refused`) and not copied. `bench corpus check`
verifies the tree against `MANIFEST.sha256.json`; `bench corpus list` prints the table below.

Files are named by the id of their docx and live by state; `notices/README.md` has the
scheme and `notices/RENAMED.csv` the rename record. `documents.csv` and
`comparisons.csv` list every entry with its state, sets, origin names, sha256 and the
producer of its Word PDF. `pools/<set>_pairs.csv` (key, base, next, ...) is the manifest a
generator takes with `--source-dir` pointing here, and `pools/<set>_renders.csv` lists the
docx that set's Word run rendered with their PDFs.

Everything here is tracked, docx and PDF files included; this tree is the source of truth.
The origin folders named below are relative to the `--origins` root of the build (Word's
working folders, not part of the repository).

| set | documents | comparisons | docset id | absent | superseded | filled | unresolved | excluded | refused |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|
| sources_500 | 500 | 0 | 29e26304c8ad | 0 | 18 | 0 | 0 | 0 | 0 |
| en_pairs_500 | 1000 | 0 | fec675dffc49 | 0 | 0 | 4 | 0 | 0 | 0 |
| redlines_a100_b10 | 0 | 965 | c507a7eef23d | 4 | 0 | 0 | 0 | 0 | 0 |
| redlines_en_500 | 0 | 451 | 947122b42898 | 18 | 0 | 0 | 0 | 1 | 0 |
| word_based | 194 | 227 | 477c5f19f71b | 3 | 0 | 0 | 2 | 0 | 0 |
| word_based_randomized | 199 | 196 | 1892074cca61 | 0 | 0 | 0 | 0 | 0 | 0 |
| word_redlines_superdoc | 210 | 399 | 5c286d4a4ad9 | 1 | 0 | 0 | 0 | 0 | 0 |
| word_based_accepted_word | 166 | 0 | 1d111c4d275c | 0 | 0 | 0 | 0 | 0 | 0 |
| word_based_0926 | 0 | 196 | 6c45909f0203 | 2 | 0 | 0 | 2 | 0 | 0 |
| word_based_randomized_0926 | 0 | 185 | 718e98c4452f | 0 | 0 | 0 | 0 | 0 | 0 |
| word_redlines_superdoc_0926 | 0 | 361 | e512e5f3427c | 1 | 0 | 0 | 0 | 0 | 0 |
| nocomments | 194 | 228 | 496a0782b581 | 2 | 3 | 0 | 2 | 0 | 0 |
| nocomments_randomized | 199 | 196 | 61778f5d5461 | 0 | 1 | 0 | 0 | 0 | 0 |
| fixtures_originals | 196 | 0 | 08fb9032341a | 0 | 0 | 0 | 0 | 11 | 0 |
| fixtures_word_compares | 0 | 164 | a251277596bd | 0 | 0 | 0 | 2 | 0 | 0 |
| pdf_fill_0928 | 608 | 106 | df018bfc7332 | 1 | 8 | 0 | 0 | 11 | 0 |
| accepted_tracking_0928 | 100 | 0 | c9cfd04d45a4 | 0 | 0 | 0 | 0 | 0 | 0 |
| rejected_tracking_0928 | 100 | 0 | ec0859439dfc | 0 | 0 | 0 | 0 | 0 | 0 |
| comment_balloons_0929 | 59 | 0 | eb94ee26a164 | 0 | 6 | 0 | 0 | 0 | 0 |

## Sets

### sources_500

500 docx sampled from the superdoc docx-corpus with their Word PDFs; the stems a later Word build re-rendered keep the earlier render under pdf_prior.

* documents: `fixtures_500`
* their Word PDFs: `fixtures_500_pdf`

### en_pairs_500

1000 English docx (500 base/next pairs, parts a and b) with the Word PDFs of the first Word pass; the second pass (run2) fills the stems the first pass lacks and otherwise stays behind.

* documents: `500_docx_part_a_original`, `500_docx_part_b_original`
* their Word PDFs: `500_pdf_part_a_original`, `500_pdf_part_b_original`
* filling the gaps: `500_pdf_part_a_run2`, `500_pdf_part_b_run2`

### redlines_a100_b10

Word compares of 100 base documents against 10 next documents of sources_500 (a__vs__b) with the Word PDF of each compared document.

* comparisons: `compared_a_100_vs_b_10_docx`
* their Word PDFs: `compared_a_100_vs_b_10_pdf`
* base/next documents: the `sources_500` set

### redlines_en_500

Word compares of the en_pairs_500 base/next pairs with the Word PDF of each compared document; the pairs of a blacklisted document and the rejected compares are left out.

* comparisons: `500_extra_docx_redlines`
* their Word PDFs: `500_extra_pdf_redlines`
* base/next documents: the `en_pairs_500` set

### word_based

The word_based documents (docx_source) and Word's compares of their pairs (docx_redlines_word) with the September 2026 Word renders of those compares.

* documents: `word_based/docx_source`
* comparisons: `word_based/docx_redlines_word`
* their Word PDFs: `wordpdf_redline_oracles/word_based`
* pairs: `word_based/centralized_mapping.csv`
* base/next documents: the `word_based` set

### word_based_randomized

The randomized word_based documents and Word's compares of their pairs with the September 2026 Word renders.

* documents: `word_based/docx_source_randomized`
* comparisons: `word_based/docx_redlines_randomized`
* their Word PDFs: `wordpdf_redline_oracles/word_based_randomized`
* pairs: `word_based/centralized_mapping_randomized.csv`
* base/next documents: the `word_based_randomized` set

### word_redlines_superdoc

The superdoc documents and Word's compares of their pairs with the September 2026 Word renders.

* documents: `word_redlines_superdoc/docx_source`
* comparisons: `word_redlines_superdoc/docx_redlines_word`
* their Word PDFs: `wordpdf_redline_oracles/word_redlines_superdoc`
* pairs: `word_redlines_superdoc/centralized_mapping.csv`
* base/next documents: the `word_redlines_superdoc` set

### word_based_accepted_word

Word compares of the word_based pairs with every tracked change accepted in Word (word_working_roundtrip, named <pair>_word_redline_accepted), with the Word PDFs of the September 29 2026 render; the LibreOffice render of each was the visual_accepted_changes oracle.

* documents: `word_based/word_working_roundtrip`
* their Word PDFs: `wr0929/word_based_accepted_word_pdf`

### word_based_0926

The September 2026 compare run of the word_based pairs: fresh Word compares with their Word PDFs.

* comparisons: `wr0926/word_based/docx`
* their Word PDFs: `wr0926/word_based/pdf`
* pairs: `word_based/centralized_mapping.csv`
* base/next documents: the `word_based` set

### word_based_randomized_0926

The September 2026 compare run of the randomized word_based pairs.

* comparisons: `wr0926/word_based_randomized/docx`
* their Word PDFs: `wr0926/word_based_randomized/pdf`
* pairs: `word_based/centralized_mapping_randomized.csv`
* base/next documents: the `word_based_randomized` set

### word_redlines_superdoc_0926

The September 2026 compare run of the superdoc pairs.

* comparisons: `wr0926/word_redlines_superdoc/docx`
* their Word PDFs: `wr0926/word_redlines_superdoc/pdf`
* pairs: `word_redlines_superdoc/centralized_mapping.csv`
* base/next documents: the `word_redlines_superdoc` set

### nocomments

The July 2026 Word run over word_based with comments stripped: the documents with their Word PDFs and the compares (tracked changes, no comments) with theirs.

* documents: `no_comments_pdf_was_generated_by_word/docx_source`
* their Word PDFs: `no_comments_pdf_was_generated_by_word/pdf_source`
* comparisons: `no_comments_pdf_was_generated_by_word/docx_redlines_word`
* their Word PDFs: `no_comments_pdf_was_generated_by_word/pdf_redlines_word`
* pairs: `no_comments_pdf_was_generated_by_word/centralized_mapping.csv`
* base/next documents: the `nocomments` set

### nocomments_randomized

The July 2026 Word run over the randomized word_based pairs with comments stripped.

* documents: `no_comments_pdf_was_generated_by_word/docx_source_randomized`
* their Word PDFs: `no_comments_pdf_was_generated_by_word/pdf_source_randomized`
* comparisons: `no_comments_pdf_was_generated_by_word/docx_redlines_randomized`
* their Word PDFs: `no_comments_pdf_was_generated_by_word/pdf_redlines_randomized`
* pairs: `no_comments_pdf_was_generated_by_word/centralized_mapping_randomized.csv`
* base/next documents: the `nocomments_randomized` set

### fixtures_originals

The original fixtures of jubarte-first (_fixtures/original_fixtures): the docx the word_based documents were made from, some under their original names; no Word PDF of them exists.

* documents: `_fixtures/original_fixtures`

### fixtures_word_compares

Word compares of the original fixtures (_fixtures/word_redlined_fixtures) resolved through the word_based mapping; no Word PDF of them exists.

* comparisons: `_fixtures/word_redlined_fixtures`
* pairs: `word_based/centralized_mapping.csv`
* base/next documents: the `word_based` set

### pdf_fill_0928

The September 28 2026 Word render of the documents and compares that had no Word PDF (notices/audit_2026-09-28_docx_without_word_pdf.csv); word_refused holds the documents Word would not open, left out through the word_invalid list.

* documents: `wr0928/pdf_fill/documents_docx`, `wr0928/pdf_fill/word_refused`
* their Word PDFs: `wr0928/pdf_fill/documents_pdf`
* comparisons: `wr0928/pdf_fill/comparisons_docx`
* their Word PDFs: `wr0928/pdf_fill/comparisons_pdf`
* pairs: `wr0928/pdf_fill/mapping.csv`
* base/next documents: the `pdf_fill_0928` set

### accepted_tracking_0928

100 Word compares (40 with comments, 60 without; accepted_tracking_selection.csv) with every tracked change accepted by Word, named <compare id>_accepted_tracking, with their Word PDFs.

* documents: `wr0928/accepted_tracking/docx`
* their Word PDFs: `wr0928/accepted_tracking/pdf`

### rejected_tracking_0928

100 more Word compares (25 with comments, 75 without; rejected_tracking_selection.csv), none of them in accepted_tracking_0928, with every tracked change rejected by Word, named <compare id>_rejected_tracking, with their Word PDFs.

* documents: `wr0928/rejected_tracking/docx`
* their Word PDFs: `wr0928/rejected_tracking/pdf`

### comment_balloons_0929

Synthetic A/B documents from the September 29 2026 investigation of when Word draws no comment balloon (a commentRangeEnd at body level or first in its paragraph), with their Word PDFs; the generators, truth tables and findings are in comment_balloons_0929.md. word_invalid holds variants with a dangling commentReference, which Word offers to repair.

* documents: `comment_balloons_0929/docx`, `comment_balloons_0929/ab_docx`
* their Word PDFs: `comment_balloons_0929/pdf`, `comment_balloons_0929/ab_pdf`

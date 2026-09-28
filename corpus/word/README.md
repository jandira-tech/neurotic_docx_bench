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

docx and PDF files are gitignored (they live in the fixtures dataset on the Hub); the
manifest, provenance, tables, pools and notices are tracked.

| set | documents | comparisons | docset id | absent | superseded | filled | unresolved | excluded | refused |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|
| sources_500 | 448 | 0 | db3f71a066b1 | 52 | 18 | 0 | 0 | 0 | 52 |
| en_pairs_500 | 785 | 0 | e0c2040c90b0 | 215 | 0 | 3 | 0 | 0 | 215 |
| redlines_a100_b10 | 0 | 604 | 69ae4b3b1088 | 361 | 0 | 0 | 4 | 0 | 357 |
| redlines_en_500 | 0 | 191 | dc30aba2d312 | 276 | 0 | 0 | 2 | 1 | 257 |
| word_based | 194 | 214 | 37fae20b629d | 17 | 0 | 0 | 1 | 0 | 14 |
| word_based_randomized | 199 | 178 | ceb524116e1a | 18 | 0 | 0 | 0 | 0 | 18 |
| word_redlines_superdoc | 210 | 0 | c45369ff5c32 | 7 | 0 | 0 | 393 | 0 | 6 |
| word_based_0926 | 0 | 183 | fc606370508d | 16 | 0 | 0 | 1 | 0 | 14 |
| word_based_randomized_0926 | 0 | 172 | d5d8d193de2c | 13 | 0 | 0 | 0 | 0 | 13 |
| word_redlines_superdoc_0926 | 0 | 0 | e3b0c44298fc | 7 | 0 | 0 | 355 | 0 | 6 |
| nocomments | 192 | 215 | bdac56835236 | 20 | 2 | 0 | 2 | 0 | 18 |
| nocomments_randomized | 194 | 179 | b26e3d6114e9 | 22 | 1 | 0 | 0 | 0 | 22 |
| fixtures_originals | 207 | 0 | c555d1b4d484 | 0 | 0 | 0 | 0 | 0 | 0 |
| fixtures_word_compares | 0 | 164 | a251277596bd | 0 | 0 | 0 | 2 | 0 | 0 |

## Sets

### sources_500

500 docx sampled from the superdoc docx-corpus with their Word PDFs; the stems a later Word build re-rendered keep the earlier render under pdf_prior.

* documents: `grok_run/fixtures_500`
* their Word PDFs: `grok_run/fixtures_500_pdf`

### en_pairs_500

1000 English docx (500 base/next pairs, parts a and b) with the Word PDFs of the first Word pass; the second pass (run2) fills the stems the first pass lacks and otherwise stays behind.

* documents: `grok_run/500_docx_part_a_original`, `grok_run/500_docx_part_b_original`
* their Word PDFs: `grok_run/500_pdf_part_a_original`, `grok_run/500_pdf_part_b_original`
* filling the gaps: `grok_run/500_pdf_part_a_run2`, `grok_run/500_pdf_part_b_run2`

### redlines_a100_b10

Word compares of 100 base documents against 10 next documents of sources_500 (a__vs__b) with the Word PDF of each compared document.

* comparisons: `grok_run/compared_a_100_vs_b_10_docx`
* their Word PDFs: `grok_run/compared_a_100_vs_b_10_pdf`
* base/next documents: the `sources_500` set

### redlines_en_500

Word compares of the en_pairs_500 base/next pairs with the Word PDF of each compared document; the pairs of a blacklisted document and the rejected compares are left out.

* comparisons: `grok_run/500_extra_docx_redlines`
* their Word PDFs: `grok_run/500_extra_pdf_redlines`
* base/next documents: the `en_pairs_500` set

### word_based

The word_based documents (docx_source) and Word's compares of their pairs (docx_redlines_word) with the September 2026 Word renders of those compares.

* documents: `corpus/word_based/docx_source`
* comparisons: `corpus/word_based/docx_redlines_word`
* their Word PDFs: `grok_run/wordpdf_redline_oracles/word_based`
* pairs: `corpus/word_based/centralized_mapping.csv`
* base/next documents: the `word_based` set

### word_based_randomized

The randomized word_based documents and Word's compares of their pairs with the September 2026 Word renders.

* documents: `corpus/word_based/docx_source_randomized`
* comparisons: `corpus/word_based/docx_redlines_randomized`
* their Word PDFs: `grok_run/wordpdf_redline_oracles/word_based_randomized`
* pairs: `corpus/word_based/centralized_mapping_randomized.csv`
* base/next documents: the `word_based_randomized` set

### word_redlines_superdoc

The superdoc documents and Word's compares of their pairs with the September 2026 Word renders.

* documents: `corpus/word_redlines_superdoc/docx_source`
* comparisons: `corpus/word_redlines_superdoc/docx_redlines_word`
* their Word PDFs: `grok_run/wordpdf_redline_oracles/word_redlines_superdoc`
* pairs: `corpus/word_redlines_superdoc/centralized_mapping.csv`
* base/next documents: the `word_redlines_superdoc` set

### word_based_0926

The September 2026 compare run of the word_based pairs: fresh Word compares with their Word PDFs.

* comparisons: `grok_run/wr0926/word_based/docx`
* their Word PDFs: `grok_run/wr0926/word_based/pdf`
* pairs: `corpus/word_based/centralized_mapping.csv`
* base/next documents: the `word_based` set

### word_based_randomized_0926

The September 2026 compare run of the randomized word_based pairs.

* comparisons: `grok_run/wr0926/word_based_randomized/docx`
* their Word PDFs: `grok_run/wr0926/word_based_randomized/pdf`
* pairs: `corpus/word_based/centralized_mapping_randomized.csv`
* base/next documents: the `word_based_randomized` set

### word_redlines_superdoc_0926

The September 2026 compare run of the superdoc pairs.

* comparisons: `grok_run/wr0926/word_redlines_superdoc/docx`
* their Word PDFs: `grok_run/wr0926/word_redlines_superdoc/pdf`
* pairs: `corpus/word_redlines_superdoc/centralized_mapping.csv`
* base/next documents: the `word_redlines_superdoc` set

### nocomments

The July 2026 Word run over word_based with comments stripped: the documents with their Word PDFs and the compares (tracked changes, no comments) with theirs.

* documents: `corpus/no_comments_pdf_was_generated_by_word/docx_source`
* their Word PDFs: `corpus/no_comments_pdf_was_generated_by_word/pdf_source`
* comparisons: `corpus/no_comments_pdf_was_generated_by_word/docx_redlines_word`
* their Word PDFs: `corpus/no_comments_pdf_was_generated_by_word/pdf_redlines_word`
* pairs: `corpus/no_comments_pdf_was_generated_by_word/centralized_mapping.csv`
* base/next documents: the `nocomments` set

### nocomments_randomized

The July 2026 Word run over the randomized word_based pairs with comments stripped.

* documents: `corpus/no_comments_pdf_was_generated_by_word/docx_source_randomized`
* their Word PDFs: `corpus/no_comments_pdf_was_generated_by_word/pdf_source_randomized`
* comparisons: `corpus/no_comments_pdf_was_generated_by_word/docx_redlines_randomized`
* their Word PDFs: `corpus/no_comments_pdf_was_generated_by_word/pdf_redlines_randomized`
* pairs: `corpus/no_comments_pdf_was_generated_by_word/centralized_mapping_randomized.csv`
* base/next documents: the `nocomments_randomized` set

### fixtures_originals

The original fixtures of jubarte-first (_fixtures/original_fixtures): the docx the word_based documents were made from, some under their original names; no Word PDF of them exists.

* documents: `_fixtures/original_fixtures`

### fixtures_word_compares

Word compares of the original fixtures (_fixtures/word_redlined_fixtures) resolved through the word_based mapping; no Word PDF of them exists.

* comparisons: `_fixtures/word_redlined_fixtures`
* pairs: `corpus/word_based/centralized_mapping.csv`
* base/next documents: the `word_based` set


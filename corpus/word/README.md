# Word corpus

Reference material produced by Microsoft Word, gathered from its working folders by
`bench corpus build` (see `neurotic_docx_bench/word_corpus.py` for the docset table). Every
file here is a copy; the origins were not moved or deleted. Only what Word finished is here:
a docx Word could not open, a document or compare it did not render, and a blacklisted
document with the pairs that touch it are listed in each docset's `PROVENANCE.json`
(`excluded`, `absent`) and not copied. `bench corpus check` verifies the tree against
`MANIFEST.sha256.json`; `bench corpus list` prints the table below from the
`PROVENANCE.json` of each docset.

Every document row carries its state, read from the docx XML: `tracked_changes`, `comments`
and `pdf_markup`, the markup Word printed into the PDF (`none`, `tracked`, `comments`,
`tracked_comments`). `index.csv` lists every document of every docset with it, so a
state is a filter over the corpus rather than a folder of it.

docx and PDF files are gitignored (they live in the fixtures dataset on the Hub); the
manifests, provenance, tables and notes are tracked.

| docset | family | keys | docset id | counts | tracked | comments | absent | superseded |
|---|---|---:|---|---|---:|---:|---:|---:|
| sources_500 | render | 500 | 403295884e59 | docx 500, pdf_word 500, pdf_word_prior 18 | 4 | 1 | 0 | 18 |
| en_pairs_500 | render | 1000 | 6b4fcb4b90ee | docx 1000, pdf_word 1000 | 28 | 10 | 0 | 0 |
| redlines_a100_b10 | redline | 965 | e5302ff95869 | docx_redline 965, pdf_redline_word 965 | 965 | 0 | 4 | 0 |
| redlines_en_500 | redline | 450 | 381ef584a2f7 | docx_redline 450, pdf_redline_word 450 | 450 | 9 | 19 | 0 |
| oracles_wordpdf | redline | 799 | b90b4fc19112 | pdf_redline_word 824 | 822 | 170 | 4 | 0 |
| oracles_wordpdf_nocomments | redline | 205 | fa7911683bfd | pdf_redline_word 230 | 228 | 0 | 2 | 0 |

## Docsets

### sources_500

500 docx sampled from the superdoc docx-corpus, each with its Word PDF; 18 stems were re-rendered by a later Word build (the earlier render is kept under pdf_word_prior).

* `docx/` from `grok_run/fixtures_500`
* `pdf_word/` from `grok_run/fixtures_500_pdf`
* `pdf_word_prior/` from `grok_run/fixtures_500_pdf`
* license ODC-By-1.0 (superdoc-dev/docx-corpus); see `LICENSE-ODC-BY-1.0.txt`

### en_pairs_500

1000 English docx (500 base/next pairs, parts a and b) with Word PDFs from the first Word pass; the second pass (run2, same Word build, the same render up to live date fields) fills the stems the first pass lacks and is otherwise left in grok_run.

* `docx/` from `grok_run/500_docx_part_a_original`, `grok_run/500_docx_part_b_original`
* `pdf_word/` from `grok_run/500_pdf_part_a_original`, `grok_run/500_pdf_part_b_original`, `grok_run/500_pdf_part_a_run2`, `grok_run/500_pdf_part_b_run2`
* license ODC-By-1.0 (superdoc-dev/docx-corpus); see `LICENSE-ODC-BY-1.0.txt`

### redlines_a100_b10

Word compares of 100 base documents against 10 next documents from sources_500 (a__vs__b), each with the Word PDF of the compared document; a pair Word did not render is left out.

* `docx_redline/` from `grok_run/compared_a_100_vs_b_10_docx`
* `pdf_redline_word/` from `grok_run/compared_a_100_vs_b_10_pdf`
* base/next docx: `sources_500/docx/`
* license ODC-By-1.0 (superdoc-dev/docx-corpus); see `LICENSE-ODC-BY-1.0.txt`

### redlines_en_500

Word compares of the en_pairs_500 base/next pairs, each with the Word PDF of the compared document; a pair Word did not render, and the pairs of a blacklisted document, are left out.

* `docx_redline/` from `grok_run/500_extra_docx_redlines`
* `pdf_redline_word/` from `grok_run/500_extra_pdf_redlines`
* base/next docx: `en_pairs_500/docx/`
* license ODC-By-1.0 (superdoc-dev/docx-corpus); see `LICENSE-ODC-BY-1.0.txt`

### oracles_wordpdf

Word renders (September 2026) of the tracked redline docx of word_based, word_based_randomized and word_redlines_superdoc, comments printed where the docx carries them: the Word PDF oracle for those corpora, keyed like the scorer keys them.

* `pdf_redline_word/` from `grok_run/wordpdf_redline_oracles/word_based`, `grok_run/wordpdf_redline_oracles/word_based_randomized`, `grok_run/wordpdf_redline_oracles/word_redlines_superdoc`

### oracles_wordpdf_nocomments

Word renders (July 2026) of the word_based tracked redline docx with their comments stripped: the same pairs as oracles_wordpdf in the state 'tracked changes, no comments'. The origin is the tracked folder corpus/no_comments_pdf_was_generated_by_word (which stays where it is).

* `pdf_redline_word/` from `corpus/no_comments_pdf_was_generated_by_word/pdf_redlines_word`


# Word files not yet indexed by `bench corpus build`

Word-made DOCX and Word-printed PDFs left in the grok_run working folders
(`~/temp/T/grok_run_archive`) after `corpus/word` was built, gathered here on 2026-10-11
before those folders were cleaned. Each file is here because:

* its producer is Microsoft Word: `<Application>` in `docProps/app.xml` names Word for a
  DOCX; the PDF producer is Word or the macOS Quartz PDFContext Word for Mac prints with.
  LibreOffice, jubarte, docxside-pdf and other tool renders were left out;
* its sha256 is not already a file under `corpus/` (no byte duplicates);
* its origin folder holds Word fixtures, not a tool's output.

Paths keep the origin folder layout, minus the `grok_run/` prefix. `sources.tsv` has the
origin path, sha256, size and producer of every file; `MANIFEST.sha256.json` pins them.

| folder | what it is |
|---|---|
| `no_comments_pdf_was_generated_by_word/docx_accepted_word`, `pdf_accepted_word` | the `accepted` pool of the DOCX→PDF Word-oracle track; the PDFs match `docx_to_pdf_oracle_sha256.json` (232/232) |
| `no_comments_pdf_was_generated_by_word/*.txt, *.json, *.csv` | that track's fixture lists, sha256 pins and mappings, as found |
| `no_comments_pdf_was_generated_by_word/word_working_roundtrip` | Word accept-all round trips of the word_based compares and their Word PDFs, other bytes than `corpus/word` holds |
| `word_based/docx_accepted_word` | a second Word accept-all pass of the same compares (different bytes, no PDFs) |
| `*_redlines_word`, `500_extra_*`, `compared_a_100_vs_b_10_*`, `_fixtures/word_redlined_fixtures`, `wordpdf_redline_oracles` | Word compares and Word PDFs the corpus build left out (no Word PDF, unresolved base/next, rejected) |
| `comment_balloons_0929/r6`, `comment_balloons_0929/pdf` | round 6 of the comment-balloon probes and one more Word PDF |
| `rev`, `slow` | docx-corpus sources kept aside by earlier runs |

Not here on purpose: Word-invalid and blacklisted documents, Word's second renders of
documents `corpus/word` already has a Word PDF for (`500_pdf_part_*_run2`,
`word_captures_superdoc_style`), and Word renders of tool outputs.

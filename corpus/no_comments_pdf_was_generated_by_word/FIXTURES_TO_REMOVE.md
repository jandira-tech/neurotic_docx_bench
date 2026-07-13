# Fixtures To Remove

These fixtures failed the SuperDoc official Word-baseline sidecar run on
2026-07-08. Microsoft Word opened them through the SuperDoc AppleScript
harness, but PDF export failed with:

`Microsoft Word got an error: active document doesn't understand the "save as" message. (-1708)`

Because no Word baseline pages were produced, the SuperDoc comparison stage
reported `No Word pages found` and skipped scoring for these documents.

Remove these source fixtures from `corpus/word_based/docx_source/` before the
next market-method baseline run:

- `corpus/word_based/docx_source/annotations_orphan_rel.docx`
- `corpus/word_based/docx_source/drawing_scalar_whitespace.docx`
- `corpus/word_based/docx_source/empty_filetime_customprops.docx`
- `corpus/word_based/docx_source/math_body_level.docx`
- `corpus/word_based/docx_source/sample_document_our_repaired_word_broken.docx`
- `corpus/word_based/docx_source/unknown_element.docx`

Evidence:

- SuperDoc run summary: `corpus/word_based/superdoc_visual_benchmark/SUMMARY.md`
- Machine-readable run summary: `corpus/word_based/superdoc_visual_benchmark/summary.json`
- Word baseline sidecar: `corpus/word_based/superdoc_visual_benchmark/reports/word-captures/`

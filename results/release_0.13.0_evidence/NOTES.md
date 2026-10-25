# 0.13.0 release evidence: notes

## The LibreOffice sample result leaves out two crashed conversions (2026-10-25, PR #64 review)

`docx_to_pdf_soffice_0.13.0_sample.json` reports `n: 598`, `failures: 0`, `itt_n: 598`,
mean 54.7897, median 47.8877. The sample has 600 documents (`sample_meta.json`), and
`convert_soffice.log` shows LibreOffice 26.8.0.3 killed by signal 6 on two of them
(`tracking_without_comments__8e534b49f0_…_redline_aeff6a9631` and `…_redline_510bcf9432`).

The score-only selection dropped both with a warning instead of counting them as failures,
so the file is not on the same population as `docx_to_pdf_jubarte_0.13.0_sample.json`
(`itt_n: 600`). Recomputed from its own `per_doc` with the two crashes scored 0, as the
intention-to-treat rule requires, the LibreOffice row is **itt_n 600, mean 54.6071, median
47.8822**.

The JSON stays as the scorer wrote it. The scorer fix, the regenerated result and the
corrected `results/converters.jsonl` line are issue #69.

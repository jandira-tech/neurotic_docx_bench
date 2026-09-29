# The LibreOffice corpus

LibreOffice renders of Word files that the bench once used as its source of truth, each
filed under the stem its docx has in `corpus/word`, so the render and the Word PDF of the
same docx share a name. `word_map.csv` maps every render to that Word docx and Word PDF
(`word_pdf` empty where Word never printed the docx). Built by `bench corpus libreoffice`
(`neurotic_docx_bench/libreoffice_corpus.py`); `PROVENANCE.json` lists what was left out.

| set | renders | with a Word PDF | unmatched | refused | used as |
|---|---:|---:|---:|---:|---|
| word_based_redlines | 228 | 227 | 4 | 0 | script_redlines and visual_redlines oracle (bench.yaml source_of_truth) |
| word_based_randomized_redlines | 196 | 196 | 0 | 0 | script_redlines oracle (bench.yaml extra_oracle_dirs) |
| word_redlines_superdoc_redlines | 399 | 399 | 1 | 0 | script_redlines oracle (bench.yaml extra_oracle_dirs) |
| word_based_sources | 194 | 194 | 6 | 0 | visual_rendering oracle |
| word_based_accepted_word | 166 | 0 | 0 | 0 | visual_accepted_changes oracle |

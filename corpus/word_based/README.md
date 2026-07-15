# corpus/word_based

The original benchmark corpus. `.docx` files retain their **Word comments
intact**; PDFs were rendered by **LibreOffice** (`soffice`).

The sibling directory `corpus/no_comments_pdf_was_generated_by_word/` is a
derived copy where comments were stripped from every `.docx` and all PDFs
were exported directly by Microsoft Word. Files that share a name between
the two directories are **not** byte-identical.

---

## Directory guide

### Source documents

| Directory | Contents |
|---|---|
| `docx_source/` | Base `.docx` documents with comments intact. 199 files. |
| `docx_source_randomized/` | Same documents renamed to `file_N.docx` in randomized order, for blind A/B testing. |

### Word oracle redlines (ground truth)

| Directory | Contents |
|---|---|
| `docx_redlines_word/` | Microsoft Word's own document-compare output — the canonical tracked-change `.docx` for each `base → next` pair. |
| `docx_accepted_word/` | Word redlines with all tracked changes accepted (for the `accepted_changes` benchmark). |

### LibreOffice-rendered PDFs

| Directory | Contents |
|---|---|
| `pdf_source/` | Each `docx_source/*.docx` rendered to PDF by LibreOffice. |
| `pdf_redlines_word/` | Each `docx_redlines_word/*.docx` rendered to PDF by LibreOffice. These are the **pixel-scoring oracle** for the default bench config. |
| `pdf_accepted_word/` | Each `docx_accepted_word/*.docx` rendered to PDF by LibreOffice. |
| `pdf_redlines_randomized/` | Redlines for randomized pairs, rendered to PDF by LibreOffice. |

### Manifest

| File | Purpose |
|---|---|
| `centralized_mapping.csv` | Authoritative pairing table (`pair_stem`, `base`, `next`, `origin`, paths, `missing`). |
| `centralized_mapping_randomized.csv` | Same schema, keyed to the randomized `file_N.docx` naming. |

### Artifacts (not used by scoring)

| Directory | Contents |
|---|---|
| `word_captures_superdoc_style/` | Per-document Word screen captures and repair-dialog evidence from earlier SuperDoc fidelity debugging. |
| `word_working_roundtrip/` | Intermediate DOCX files from Word open → edit → save roundtrip experiments. |

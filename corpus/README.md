---
license: odc-by
pretty_name: neurotic_docx_bench fixtures (Microsoft Word DOCX, PDF and redline corpus)
language:
- en
- multilingual
task_categories:
- other
size_categories:
- 10K<n<100K
source_datasets:
- superdoc-dev/docx-corpus
tags:
- docx
- ooxml
- pdf
- benchmark
- redline
- tracked-changes
- document-comparison
- document-rendering
- docx-to-pdf
- microsoft-word
- legal
configs:
- config_name: documents
  default: true
  data_files:
  - split: train
    path: data/documents.parquet
- config_name: comparisons
  data_files:
  - split: train
    path: data/comparisons.parquet
- config_name: accept_reject
  data_files:
  - split: train
    path: data/accept_reject.parquet
- config_name: libreoffice
  data_files:
  - split: train
    path: data/libreoffice.parquet
- config_name: word_unindexed
  data_files:
  - split: train
    path: data/word_unindexed.parquet
---

# neurotic_docx_bench fixtures

**Real-world DOCX files and what Microsoft Word itself makes of them**: Word's own PDF of every
document, Word's own *Compare* (redline) of document pairs with Word's PDF of each redline, and
Word's *Accept All* / *Reject All* of 400 redlines. It is the ground truth of
[neurotic_docx_bench](https://github.com/jandira-tech/neurotic_docx_bench), which scores DOCX→PDF
converters (jubarte, LibreOffice, docxide-pdf, …) and redline engines (jubarte, docxodus, …) against
Word, and of the published comparison site
[jandira-tech.github.io/neurotic_docx_bench](https://jandira-tech.github.io/neurotic_docx_bench/).

Every PDF here was printed by **Microsoft Word for Mac** (macOS Quartz PDFContext, macOS 26.5.1
and 26.6.2); every redline was made by Word's *Compare Documents*. No PDF from another producer is
in `word/` or `word_unindexed/`; LibreOffice renders are kept apart in `libreoffice/`.

| | |
|---|---|
| Files | 16,853 (2.72 GB), every one pinned in `MANIFEST.sha256.json` |
| Documents (`word/`) | 2,925 DOCX, each with Word's PDF |
| Word compares (`word/`) | 3,503 redline DOCX (base vs next), 3,502 with Word's PDF |
| Accept All / Reject All | 800 DOCX + PDF (400 redlines × 2) |
| LibreOffice renders | 1,183 PDF, mapped to their Word DOCX/PDF |
| Not yet indexed Word files | 1,082 (Word-made DOCX/PDF awaiting indexing) |
| Languages | 47 detected; English 2,148 of 2,925 documents, Portuguese 38 |
| Pages (Word PDF) | documents: median 1, max 343; redlines: median 2, max 425 |

## Quick start

```python
from datasets import load_dataset
from huggingface_hub import hf_hub_download

docs = load_dataset("arthrod/neurotic_docx_bench-fixtures", "documents", split="train")       # one row per DOCX
row = docs.filter(lambda r: r["lang"] == "pt")[0]
docx = hf_hub_download("arthrod/neurotic_docx_bench-fixtures", row["docx_repo_path"], repo_type="dataset")
pdf  = hf_hub_download("arthrod/neurotic_docx_bench-fixtures", row["pdf_repo_path"],  repo_type="dataset")   # Word's PDF of it

pairs = load_dataset("arthrod/neurotic_docx_bench-fixtures", "comparisons", split="train")    # one row per Word compare
```

The whole tree, verified against the manifest (what the bench does):

```bash
git clone https://github.com/jandira-tech/neurotic_docx_bench && cd neurotic_docx_bench
uv run bench fixtures download          # snapshot into corpus/, refuses any sha256 mismatch
uv run bench corpus check               # re-checks word/ against word/MANIFEST.sha256.json
```

## Layout

```
word/                      the Word corpus (source of truth of the bench)
  <state>/docx/            DOCX, named <id>_<name>.docx
  <state>/pdf/             Word's PDF of each, same stem
  <state>/pdf_prior/       an earlier Word build's PDF of the same DOCX (36 files)
  accept_all/{docx,pdf}    Word's Accept All of 400 redlines, and its PDF
  reject_all/{docx,pdf}    Word's Reject All of the same 400, and its PDF
  documents.csv            every document: id, stem, state, paths, sets, origin names, sha256, PDF producer
  comparisons.csv          every compare: id, key, base_id, next_id, state, paths, sets, sha256, producer
  pools/                   per-set manifests the bench runs on (<set>_pairs.csv, <set>_renders.csv), holdout.txt
  notices/                 naming scheme, RENAMED.csv, docx-corpus license/NOTICE, compare-run logs
  PROVENANCE.json          origins, counts, what was left out and why, per set
libreoffice/<state>/       LibreOffice renders of Word DOCX, under the Word stem; word_map.csv
word_unindexed/            Word-made DOCX/PDF gathered before the working folders were cleaned; sources.tsv
mutation_probes/           one seed DOCX and 13 single-edit mutations (insert, delete, move, split, merge, format)
canary_expected.json       canary hashes a bench run must reproduce
holdout_combined.txt       the sealed holdout list
data/*.parquet             the tables above as viewer configs (derived; the CSVs are the originals)
```

### States

A file lives under the **state of its DOCX, read from its XML**, not from where it came from:

| state | documents | compares |
|---|---:|---:|
| `clean` | 2,478 | 2 |
| `tracking_without_comments` | 237 | 3,174 |
| `with_comments_clean` | 112 | 5 |
| `with_comments_tracking` | 98 | 322 |

`clean`: no tracked changes, no comments. `tracking_*`: has tracked changes (`w:ins`/`w:del`/…).
`with_comments_*`: has comments. A compare lives in the state of the redline Word produced.

### Names and ids

An **id** is the first 10 hex digits of the sha256 of the DOCX bytes.

* Document: `<id>_<name>` (`<name>` is the original file name, lower-cased, `[a-z0-9_-]`, cut at 48 chars; the
  docx-corpus documents use their dataset sha256 as name). Its Word PDF has the same stem.
* Compare: `<idA>_<a>__vs__<idB>_<b>_redline_<idC>`: base, next, and the id of the redline DOCX itself.
* Byte-identical DOCX from several origins are one file; every origin name and set is in the `names`/`sets` columns.
  Original names are in `word/notices/RENAMED.csv`.

## Configs (dataset viewer)

| config | rows | one row per | key columns |
|---|---:|---|---|
| `documents` (default) | 2,925 | DOCX with its Word PDF | `id`, `state`, `docx_repo_path`, `pdf_repo_path`, `sets`, `sha256`, `producer`, `lang`, `type`, `topic`, `pages` |
| `comparisons` | 3,503 | Word compare (redline) | `id`, `base_id`, `next_id`, `state`, `docx_repo_path`, `pdf_repo_path`, `lang`, `type`, `pages` |
| `accept_reject` | 800 | Accept All / Reject All of a redline | `key`, `operation`, `status`, `docx_repo_path`, `pdf_repo_path`, `source_docx_repo_path` |
| `libreoffice` | 1,183 | LibreOffice render | `libreoffice_pdf_repo_path`, `word_docx_repo_path`, `word_pdf_repo_path`, `set`, `used_as` |
| `word_unindexed` | 1,082 | unindexed Word file | `repo_path`, `sha256`, `bytes`, `producer` |

`*_repo_path` columns are paths in this repo (pass them to `hf_hub_download`); the plain path columns are
relative to the folder of their CSV, as in the original tables.

`lang`, `type`, `topic`, `pages` were added for sampling the comparison site and are **approximate**:
`lang` comes from the docx-corpus metadata where it exists and from text detection otherwise (`?` = undetected);
`type` is the docx-corpus document type, or `synthetic` for the generated test documents; `pages` is the page count
of Word's PDF.

## Composition

* **Languages** (documents): en 2,148, unknown 161, ru 42, da 41, es 38, pt 38, fr 37, de 37, nl 35, cs 32, pl 31, zh 30.
* **Document types**: synthetic 1,425, legal 232, forms 226, educational 206, administrative 190, policies 158, reports 129, correspondence 120, reference 120, technical 74, creative 45.
* **Sources**: 19 build sets (see `word/README.md` and `word/PROVENANCE.json`): 1,500 real DOCX from
  [superdoc-dev/docx-corpus](https://huggingface.co/datasets/superdoc-dev/docx-corpus) (collected from the public
  web): 500 sampled across languages and types, compared 100 base × 10 next, and 1,000 English documents
  compared as 500 base/next pairs; synthetic documents written to
  stress OOXML features (lists, numbering, tables, fields, headers/footers, comments, tracked-change edge cases,
  comment balloons) and their mutated versions; Word's accept/reject of 400 compares.
* **What was left out on purpose**: DOCX Word could not open cleanly, blacklisted documents and every pair that
  touches them, compares or renders Word did not finish, and any PDF not printed by Word. Each is listed per set in
  `word/PROVENANCE.json` (`excluded`, `absent`, `refused`).

## How it was made

1. Documents were opened in Microsoft Word for Mac and printed to PDF through macOS (Quartz PDFContext) with
   AppleScript drivers (`scripts/word_pdf.py` in the bench repo).
2. Pairs were compared with Word's *Compare Documents* (`scripts/word_redline.py`), saving the redline DOCX and
   Word's PDF of it.
3. `bench corpus build` gathered Word's working folders, read each DOCX's state from its XML, deduplicated by
   sha256, renamed by id and wrote the tables and manifests.

## Intended use and limits

* **Use**: reference renders for DOCX→PDF converters and redline/compare engines; layout-fidelity and
  tracked-change research; testing OOXML parsers on real and adversarial documents.
* **One Word, one machine**: the PDFs are Word for Mac's. Word for Windows, other Word builds and other font sets
  produce different line breaks and pagination; `pdf_prior/` shows how much two Word builds already differ.
* **Fonts**: documents asking for fonts the Mac did not have were rendered with Word's substitutes.
* **Redlines**: Word's compare output depends on its settings and version; these are one Word's opinion of the
  differences, not a canonical diff.
* **Personal data**: the docx-corpus documents were collected from the public web and may contain names or contact
  details of the people who wrote them. Do not use this dataset to identify or profile individuals.

## License

The collection (selection, arrangement, tables, Word renders and compares made for this bench) is released under the
**[ODC Attribution License (ODC-By 1.0)](https://opendatacommons.org/licenses/by/1.0/)** (`LICENSE-ODC-BY-1.0.txt`).
It contains information from [docx-corpus](https://huggingface.co/datasets/superdoc-dev/docx-corpus) by SuperDoc,
also ODC-By 1.0 (`NOTICE`). ODC-By covers the database; it does not license copyright in the individual DOCX files,
which were collected from the public web and may have their own rights (section 2.4 of the license).
Microsoft Word is a trademark of Microsoft; this dataset is not affiliated with or endorsed by Microsoft.

## Related

| Repo | Role |
|---|---|
| [arthrod/neurotic_docx_bench](https://huggingface.co/datasets/arthrod/neurotic_docx_bench) | Results: run records, every tool's outputs, published pages |
| [jandira-tech/neurotic_docx_bench](https://github.com/jandira-tech/neurotic_docx_bench) | The bench harness (AGPL-3.0) |
| [jandira-tech.github.io/neurotic_docx_bench](https://jandira-tech.github.io/neurotic_docx_bench/) | Side-by-side viewer of the scores |
| [superdoc-dev/docx-corpus](https://huggingface.co/datasets/superdoc-dev/docx-corpus) | Upstream source of the real-world DOCX |

**Earlier layout**: until 2026-10-10 this repo was organised by origin folder (`word_based/`,
`no_comments_pdf_was_generated_by_word/`, …, with renders by other tools mixed in). That snapshot is kept at the tag
[`layout-2026-10-10`](https://huggingface.co/datasets/arthrod/neurotic_docx_bench-fixtures/tree/layout-2026-10-10).

## Citation

```bibtex
@misc{neurotic_docx_bench_fixtures,
  title  = {neurotic\_docx\_bench fixtures: DOCX documents with Microsoft Word's PDFs and redlines},
  author = {Rodrigues, Arthur},
  year   = {2026},
  howpublished = {\url{https://huggingface.co/datasets/arthrod/neurotic_docx_bench-fixtures}},
}
```

Please also cite docx-corpus (`superdoc-dev/docx-corpus`, SuperDoc) when you use its documents.

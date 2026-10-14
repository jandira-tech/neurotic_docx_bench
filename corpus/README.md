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

## Schema

All columns are strings. Paths in `docx`/`pdf`/… are relative to the state folder; the `*_repo_path` columns are full paths inside this repo, usable directly with `hf_hub_download`. Missing values are `null`.

### `documents` (2,925 rows)

| column | type | example |
|---|---|---|
| `id` | string | `a67dcf9e05` |
| `stem` | string | `a67dcf9e05_000014a959f5225c658740fd7915cd50c5728c9cbe06c7d7` |
| `state` | string | `clean` |
| `docx` | string | `clean/docx/a67dcf9e05_000014a959f5225c658740fd7915cd50c5728c9cbe06c7d7…` |
| `pdf` | string | `clean/pdf/a67dcf9e05_000014a959f5225c658740fd7915cd50c5728c9cbe06c7d7.…` |
| `pdf_prior` | string | `null` |
| `sets` | string | `sources_500` |
| `names` | string | `000014a959f5225c658740fd7915cd50c5728c9cbe06c7d72d79a9708244ec1f` |
| `sha256` | string | `a67dcf9e05226e3cc9750a9f10816b9fd01ca1b7452daa479ed22f46745d9fbb` |
| `producer` | string | `macOS Version 26.6.2 (Build 25G83) Quartz PDFContext` |
| `docx_repo_path` | string | `word/clean/docx/a67dcf9e05_000014a959f5225c658740fd7915cd50c5728c9cbe0…` |
| `pdf_repo_path` | string | `word/clean/pdf/a67dcf9e05_000014a959f5225c658740fd7915cd50c5728c9cbe06…` |
| `pdf_prior_repo_path` | string | `null` |
| `lang` | string | `fr` |
| `type` | string | `legal` |
| `topic` | string | `legal_judicial` |
| `pages` | string | `2` |

### `comparisons` (3,503 rows)

| column | type | example |
|---|---|---|
| `id` | string | `82630d00f7` |
| `key` | string | `a67dcf9e05_000014a959f5225c658740fd7915cd50c5728c9cbe06c7d7__vs__2773a…` |
| `base_id` | string | `a67dcf9e05` |
| `next_id` | string | `2773adf157` |
| `state` | string | `tracking_without_comments` |
| `docx` | string | `tracking_without_comments/docx/a67dcf9e05_000014a959f5225c658740fd7915…` |
| `pdf` | string | `tracking_without_comments/pdf/a67dcf9e05_000014a959f5225c658740fd7915c…` |
| `pdf_prior` | string | `null` |
| `sets` | string | `redlines_a100_b10` |
| `names` | string | `000014a959f5225c658740fd7915cd50c5728c9cbe06c7d72d79a9708244ec1f__vs__…` |
| `sha256` | string | `82630d00f7a870b90d09cc150e7bd0357c0938bb17db55c723baabc5c633581f` |
| `producer` | string | `macOS Version 26.6.2 (Build 25G83) Quartz PDFContext` |
| `docx_repo_path` | string | `word/tracking_without_comments/docx/a67dcf9e05_000014a959f5225c658740f…` |
| `pdf_repo_path` | string | `word/tracking_without_comments/pdf/a67dcf9e05_000014a959f5225c658740fd…` |
| `pdf_prior_repo_path` | string | `null` |
| `lang` | string | `fr` |
| `type` | string | `legal` |
| `pages` | string | `3` |

### `accept_reject` (800 rows)

| column | type | example |
|---|---|---|
| `key` | string | `00da16e738_heading_4_style_demo_id_paraid_overflow_2__vs__82928b2e05_h…` |
| `pool` | string | `word_based` |
| `state` | string | `tracking_without_comments` |
| `status` | string | `ok` |
| `docx` | string | `accept_all/docx/00da16e738_heading_4_style_demo_id_paraid_overflow_2__…` |
| `pdf` | string | `accept_all/pdf/00da16e738_heading_4_style_demo_id_paraid_overflow_2__v…` |
| `source_docx` | string | `tracking_without_comments/docx/00da16e738_heading_4_style_demo_id_para…` |
| `operation` | string | `accept_all` |
| `docx_repo_path` | string | `word/accept_all/docx/00da16e738_heading_4_style_demo_id_paraid_overflo…` |
| `pdf_repo_path` | string | `word/accept_all/pdf/00da16e738_heading_4_style_demo_id_paraid_overflow…` |
| `source_docx_repo_path` | string | `word/tracking_without_comments/docx/00da16e738_heading_4_style_demo_id…` |

### `libreoffice` (1,183 rows)

| column | type | example |
|---|---|---|
| `libreoffice_pdf` | string | `tracking_without_comments/pdf/70bed70fac_1_5_line_spacing_id_paraid_ov…` |
| `key` | string | `70bed70fac_1_5_line_spacing_id_paraid_overflow__vs__6a65e5219d_24_id_p…` |
| `kind` | string | `comparison` |
| `word_id` | string | `b3682dd36b` |
| `word_docx` | string | `tracking_without_comments/docx/70bed70fac_1_5_line_spacing_id_paraid_o…` |
| `word_pdf` | string | `tracking_without_comments/pdf/70bed70fac_1_5_line_spacing_id_paraid_ov…` |
| `word_pdf_producer` | string | `macOS Version 26.6.2 (Build 25G83) Quartz PDFContext` |
| `set` | string | `word_based_redlines` |
| `used_as` | string | `script_redlines and visual_redlines oracle (bench.yaml source_of_truth…` |
| `producer` | string | `LibreOffice 26.2.4.2 (AARCH64)` |
| `sha256` | string | `8551792adab6d54bcfe8685297c65bbfaff3d6dc21f92989b434fccac2339fbb` |
| `libreoffice_pdf_repo_path` | string | `libreoffice/tracking_without_comments/pdf/70bed70fac_1_5_line_spacing_…` |
| `word_docx_repo_path` | string | `word/tracking_without_comments/docx/70bed70fac_1_5_line_spacing_id_par…` |
| `word_pdf_repo_path` | string | `word/tracking_without_comments/pdf/70bed70fac_1_5_line_spacing_id_para…` |

### `word_unindexed` (1,082 rows)

| column | type | example |
|---|---|---|
| `path` | string | `comment_balloons_0929/r6/docx/R6_01_empty_range_ref.docx` |
| `sha256` | string | `58e76c03f925de93a1b5c2b7d71a3a5d36b8436021e5142dc636c9af05af0211` |
| `bytes` | string | `168826` |
| `producer` | string | `Microsoft Office Word/16.0000` |
| `repo_path` | string | `word_unindexed/comment_balloons_0929/r6/docx/R6_01_empty_range_ref.doc…` |

## Examples

Two rows from each config (long values truncated with `…`).

<details><summary><code>documents</code></summary>

```json
[
 {
  "id": "a67dcf9e05",
  "stem": "a67dcf9e05_000014a959f5225c658740fd7915cd50c5728c9cbe06c7d7",
  "state": "clean",
  "docx": "clean/docx/a67dcf9e05_000014a959f5225c658740fd7915cd50c5728c9cbe06c7d7.docx",
  "pdf": "clean/pdf/a67dcf9e05_000014a959f5225c658740fd7915cd50c5728c9cbe06c7d7.pdf",
  "pdf_prior": null,
  "sets": "sources_500",
  "names": "000014a959f5225c658740fd7915cd50c5728c9cbe06c7d72d79a9708244ec1f",
  "sha256": "a67dcf9e05226e3cc9750a9f10816b9fd01ca1b7452daa479ed22f46745d9fbb",
  "producer": "macOS Version 26.6.2 (Build 25G83) Quartz PDFContext",
  "docx_repo_path": "word/clean/docx/a67dcf9e05_000014a959f5225c658740fd7915cd50c5728c9cbe06c7d7.docx",
  "pdf_repo_path": "word/clean/pdf/a67dcf9e05_000014a959f5225c658740fd7915cd50c5728c9cbe06c7d7.pdf",
  "pdf_prior_repo_path": null,
  "lang": "fr",
  "type": "legal",
  "topic": "legal_judicial",
  "pages": "2"
 },
 {
  "id": "3bfcb371e2",
  "stem": "3bfcb371e2_00003fff80a444ad2f706c74f3c0d9fbef00d7a99ba0c105",
  "state": "clean",
  "docx": "clean/docx/3bfcb371e2_00003fff80a444ad2f706c74f3c0d9fbef00d7a99ba0c105.docx",
  "pdf": "clean/pdf/3bfcb371e2_00003fff80a444ad2f706c74f3c0d9fbef00d7a99ba0c105.pdf",
  "pdf_prior": null,
  "sets": "sources_500",
  "names": "00003fff80a444ad2f706c74f3c0d9fbef00d7a99ba0c105e7baa0574df63393",
  "sha256": "3bfcb371e2fc81584268c37f0312cccd2f8f20850dbc7e2aa834a72b33254235",
  "producer": "macOS Version 26.6.2 (Build 25G83) Quartz PDFContext",
  "docx_repo_path": "word/clean/docx/3bfcb371e2_00003fff80a444ad2f706c74f3c0d9fbef00d7a99ba0c105.docx",
  "pdf_repo_path": "word/clean/pdf/3bfcb371e2_00003fff80a444ad2f706c74f3c0d9fbef00d7a99ba0c105.pdf",
  "pdf_prior_repo_path": null,
  "lang": "es",
  "type": "educational",
  "topic": "education",
  "pages": "6"
 }
]
```

</details>

<details><summary><code>comparisons</code></summary>

```json
[
 {
  "id": "82630d00f7",
  "key": "a67dcf9e05_000014a959f5225c658740fd7915cd50c5728c9cbe06c7d7__vs__2773adf157_0004c94ca2a868…",
  "base_id": "a67dcf9e05",
  "next_id": "2773adf157",
  "state": "tracking_without_comments",
  "docx": "tracking_without_comments/docx/a67dcf9e05_000014a959f5225c658740fd7915cd50c5728c9cbe06c7d7…",
  "pdf": "tracking_without_comments/pdf/a67dcf9e05_000014a959f5225c658740fd7915cd50c5728c9cbe06c7d7_…",
  "pdf_prior": null,
  "sets": "redlines_a100_b10",
  "names": "000014a959f5225c658740fd7915cd50c5728c9cbe06c7d72d79a9708244ec1f__vs__0004c94ca2a8684d4744…",
  "sha256": "82630d00f7a870b90d09cc150e7bd0357c0938bb17db55c723baabc5c633581f",
  "producer": "macOS Version 26.6.2 (Build 25G83) Quartz PDFContext",
  "docx_repo_path": "word/tracking_without_comments/docx/a67dcf9e05_000014a959f5225c658740fd7915cd50c5728c9cbe0…",
  "pdf_repo_path": "word/tracking_without_comments/pdf/a67dcf9e05_000014a959f5225c658740fd7915cd50c5728c9cbe06…",
  "pdf_prior_repo_path": null,
  "lang": "fr",
  "type": "legal",
  "pages": "3"
 },
 {
  "id": "8fff070a61",
  "key": "3bfcb371e2_00003fff80a444ad2f706c74f3c0d9fbef00d7a99ba0c105__vs__2773adf157_0004c94ca2a868…",
  "base_id": "3bfcb371e2",
  "next_id": "2773adf157",
  "state": "tracking_without_comments",
  "docx": "tracking_without_comments/docx/3bfcb371e2_00003fff80a444ad2f706c74f3c0d9fbef00d7a99ba0c105…",
  "pdf": "tracking_without_comments/pdf/3bfcb371e2_00003fff80a444ad2f706c74f3c0d9fbef00d7a99ba0c105_…",
  "pdf_prior": null,
  "sets": "redlines_a100_b10",
  "names": "00003fff80a444ad2f706c74f3c0d9fbef00d7a99ba0c105e7baa0574df63393__vs__0004c94ca2a8684d4744…",
  "sha256": "8fff070a611b42fe987d0c37d6e798e94296a52fd35fb898c4be0119e959e664",
  "producer": "macOS Version 26.6.2 (Build 25G83) Quartz PDFContext",
  "docx_repo_path": "word/tracking_without_comments/docx/3bfcb371e2_00003fff80a444ad2f706c74f3c0d9fbef00d7a99ba…",
  "pdf_repo_path": "word/tracking_without_comments/pdf/3bfcb371e2_00003fff80a444ad2f706c74f3c0d9fbef00d7a99ba0…",
  "pdf_prior_repo_path": null,
  "lang": "es",
  "type": "educational",
  "pages": "7"
 }
]
```

</details>

<details><summary><code>accept_reject</code></summary>

```json
[
 {
  "key": "00da16e738_heading_4_style_demo_id_paraid_overflow_2__vs__82928b2e05_heading_4_style_demo_…",
  "pool": "word_based",
  "state": "tracking_without_comments",
  "status": "ok",
  "docx": "accept_all/docx/00da16e738_heading_4_style_demo_id_paraid_overflow_2__vs__82928b2e05_headi…",
  "pdf": "accept_all/pdf/00da16e738_heading_4_style_demo_id_paraid_overflow_2__vs__82928b2e05_headin…",
  "source_docx": "tracking_without_comments/docx/00da16e738_heading_4_style_demo_id_paraid_overflow_2__vs__8…",
  "operation": "accept_all",
  "docx_repo_path": "word/accept_all/docx/00da16e738_heading_4_style_demo_id_paraid_overflow_2__vs__82928b2e05_…",
  "pdf_repo_path": "word/accept_all/pdf/00da16e738_heading_4_style_demo_id_paraid_overflow_2__vs__82928b2e05_h…",
  "source_docx_repo_path": "word/tracking_without_comments/docx/00da16e738_heading_4_style_demo_id_paraid_overflow_2__…"
 },
 {
  "key": "01d1b3da75_table_bookmark_end__vs__45c1c5abec_table_vmerge_colspan_redline_6e159e8a9b",
  "pool": "word_based",
  "state": "tracking_without_comments",
  "status": "ok",
  "docx": "accept_all/docx/01d1b3da75_table_bookmark_end__vs__45c1c5abec_table_vmerge_colspan_redline…",
  "pdf": "accept_all/pdf/01d1b3da75_table_bookmark_end__vs__45c1c5abec_table_vmerge_colspan_redline_…",
  "source_docx": "tracking_without_comments/docx/01d1b3da75_table_bookmark_end__vs__45c1c5abec_table_vmerge_…",
  "operation": "accept_all",
  "docx_repo_path": "word/accept_all/docx/01d1b3da75_table_bookmark_end__vs__45c1c5abec_table_vmerge_colspan_re…",
  "pdf_repo_path": "word/accept_all/pdf/01d1b3da75_table_bookmark_end__vs__45c1c5abec_table_vmerge_colspan_red…",
  "source_docx_repo_path": "word/tracking_without_comments/docx/01d1b3da75_table_bookmark_end__vs__45c1c5abec_table_vm…"
 }
]
```

</details>

<details><summary><code>libreoffice</code></summary>

```json
[
 {
  "libreoffice_pdf": "tracking_without_comments/pdf/70bed70fac_1_5_line_spacing_id_paraid_overflow__vs__6a65e521…",
  "key": "70bed70fac_1_5_line_spacing_id_paraid_overflow__vs__6a65e5219d_24_id_paraid_overflow_redli…",
  "kind": "comparison",
  "word_id": "b3682dd36b",
  "word_docx": "tracking_without_comments/docx/70bed70fac_1_5_line_spacing_id_paraid_overflow__vs__6a65e52…",
  "word_pdf": "tracking_without_comments/pdf/70bed70fac_1_5_line_spacing_id_paraid_overflow__vs__6a65e521…",
  "word_pdf_producer": "macOS Version 26.6.2 (Build 25G83) Quartz PDFContext",
  "set": "word_based_redlines",
  "used_as": "script_redlines and visual_redlines oracle (bench.yaml source_of_truth)",
  "producer": "LibreOffice 26.2.4.2 (AARCH64)",
  "sha256": "8551792adab6d54bcfe8685297c65bbfaff3d6dc21f92989b434fccac2339fbb",
  "libreoffice_pdf_repo_path": "libreoffice/tracking_without_comments/pdf/70bed70fac_1_5_line_spacing_id_paraid_overflow__…",
  "word_docx_repo_path": "word/tracking_without_comments/docx/70bed70fac_1_5_line_spacing_id_paraid_overflow__vs__6a…",
  "word_pdf_repo_path": "word/tracking_without_comments/pdf/70bed70fac_1_5_line_spacing_id_paraid_overflow__vs__6a6…"
 },
 {
  "libreoffice_pdf": "tracking_without_comments/pdf/6a65e5219d_24_id_paraid_overflow__vs__8df6dfa8d7_alternate_c…",
  "key": "6a65e5219d_24_id_paraid_overflow__vs__8df6dfa8d7_alternate_content_redline_52a957c23d",
  "kind": "comparison",
  "word_id": "52a957c23d",
  "word_docx": "tracking_without_comments/docx/6a65e5219d_24_id_paraid_overflow__vs__8df6dfa8d7_alternate_…",
  "word_pdf": "tracking_without_comments/pdf/6a65e5219d_24_id_paraid_overflow__vs__8df6dfa8d7_alternate_c…",
  "word_pdf_producer": "macOS Version 26.6.2 (Build 25G83) Quartz PDFContext",
  "set": "word_based_redlines",
  "used_as": "script_redlines and visual_redlines oracle (bench.yaml source_of_truth)",
  "producer": "LibreOffice 26.2.4.2 (AARCH64)",
  "sha256": "f53275e06fbbcf0b03aaa0da61128c246b5cd6ff827b917910ecb6141931d9dd",
  "libreoffice_pdf_repo_path": "libreoffice/tracking_without_comments/pdf/6a65e5219d_24_id_paraid_overflow__vs__8df6dfa8d7…",
  "word_docx_repo_path": "word/tracking_without_comments/docx/6a65e5219d_24_id_paraid_overflow__vs__8df6dfa8d7_alter…",
  "word_pdf_repo_path": "word/tracking_without_comments/pdf/6a65e5219d_24_id_paraid_overflow__vs__8df6dfa8d7_altern…"
 }
]
```

</details>

<details><summary><code>word_unindexed</code></summary>

```json
[
 {
  "path": "comment_balloons_0929/r6/docx/R6_01_empty_range_ref.docx",
  "sha256": "58e76c03f925de93a1b5c2b7d71a3a5d36b8436021e5142dc636c9af05af0211",
  "bytes": "168826",
  "producer": "Microsoft Office Word/16.0000",
  "repo_path": "word_unindexed/comment_balloons_0929/r6/docx/R6_01_empty_range_ref.docx"
 },
 {
  "path": "comment_balloons_0929/r6/docx/R6_02_empty_t_between.docx",
  "sha256": "bab5f0b879905aa43b2ce0f088ec5b5e1c5585bf076f4cf0b7e651ab06fbe2f9",
  "bytes": "168828",
  "producer": "Microsoft Office Word/16.0000",
  "repo_path": "word_unindexed/comment_balloons_0929/r6/docx/R6_02_empty_t_between.docx"
 }
]
```

</details>

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

## Limitations

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

## Related repos

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

"""Publish corpus/ to the public HF dataset arthrod/neurotic_docx_bench-fixtures (2026-10-11).

    uv run --with polars --with huggingface_hub python scripts/hf_fixtures/hf_fixtures.py build    # data/*.parquet, README.md, MANIFEST
    uv run --with polars --with huggingface_hub python scripts/hf_fixtures/hf_fixtures.py upload   # one commit, replaces the old layout
    uv run --with polars --with huggingface_hub python scripts/hf_fixtures/hf_fixtures.py verify   # every local sha256 against the hub's LFS sha256

inv_documents.csv / inv_comparisons.csv (beside this script) give the lang, type, topic and pages
columns: the inventory made for sampling the 2026-10-11 site. The previous by-origin layout stays on the hub under the tag `layout-2026-10-10`.
"""

from __future__ import annotations

import hashlib
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

import polars as pl

BENCH = Path(__file__).resolve().parents[2]
CORPUS = BENCH / "corpus"
H = Path(__file__).parent
REPO = "arthrod/neurotic_docx_bench-fixtures"
SKIP_NAMES = {".DS_Store"}
SKIP_SUFFIXES = {".log", ".lock"}


def files() -> list[Path]:
    return sorted((p for p in CORPUS.rglob("*") if p.is_file() and p.name not in SKIP_NAMES
                   and p.suffix not in SKIP_SUFFIXES and ".cache" not in p.parts),
                  key=lambda p: p.relative_to(CORPUS).as_posix())


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def table(path: Path, sep: str = ",") -> pl.DataFrame:
    return pl.read_csv(path, separator=sep, infer_schema_length=0)  # every column as text, as written


def with_repo_paths(df: pl.DataFrame, prefix: str, cols: list[str]) -> pl.DataFrame:
    """Paths in the CSVs are relative to their folder; add the path in the repo next to each."""
    return df.with_columns([
        pl.when(pl.col(c).is_null() | (pl.col(c) == "")).then(None).otherwise(pl.lit(prefix) + pl.col(c)).alias(f"{c}_repo_path")
        for c in cols if c in df.columns])


def build() -> None:
    data = CORPUS / "data"
    data.mkdir(exist_ok=True)
    inv_d = table(H / "inv_documents.csv").select("id", "lang", "type", "topic", "pages")
    inv_c = table(H / "inv_comparisons.csv").select("id", "lang", "type", "pages")
    docs = with_repo_paths(table(CORPUS / "word/documents.csv"), "word/", ["docx", "pdf", "pdf_prior"]).join(inv_d, on="id", how="left")
    cmps = with_repo_paths(table(CORPUS / "word/comparisons.csv"), "word/", ["docx", "pdf", "pdf_prior"]).join(inv_c, on="id", how="left")
    acc = pl.concat([table(CORPUS / f"word/pools/{k}.csv").with_columns(pl.lit(k).alias("operation")) for k in ("accept_all", "reject_all")])
    acc = with_repo_paths(acc.drop("origin_docx", "origin_pdf"), "word/", ["docx", "pdf", "source_docx"])
    lo = with_repo_paths(table(CORPUS / "libreoffice/word_map.csv").drop("origin", "docx_origin"),
                         "libreoffice/", ["libreoffice_pdf"])
    lo = lo.with_columns((pl.lit("word/") + pl.col("word_docx")).alias("word_docx_repo_path"),
                         pl.when(pl.col("word_pdf").is_null() | (pl.col("word_pdf") == "")).then(None)
                         .otherwise(pl.lit("word/") + pl.col("word_pdf")).alias("word_pdf_repo_path"))
    un = table(CORPUS / "word_unindexed/sources.tsv", "\t").drop("origin_path")
    un = un.with_columns((pl.lit("word_unindexed/") + pl.col("path")).alias("repo_path"))
    for name, df in {"documents": docs, "comparisons": cmps, "accept_reject": acc, "libreoffice": lo, "word_unindexed": un}.items():
        df.write_parquet(data / f"{name}.parquet")
    card = CORPUS / "README.md"
    card.write_text(render_card(docs, cmps, acc, lo, un))
    manifest = {p.relative_to(CORPUS).as_posix(): sha256(p) for p in files() if p.name != "MANIFEST.sha256.json" or p.parent != CORPUS}
    (CORPUS / "MANIFEST.sha256.json").write_text(json.dumps(
        {"version": 1, "algorithm": "sha256", "files": manifest}, indent=1) + "\n")
    print(f"{len(manifest)} files in the manifest, {sum(p.stat().st_size for p in files()) / 1e9:.2f} GB")


def counts(series, top: int | None = None) -> list[tuple[str, int]]:
    return Counter(x or "unknown" for x in series).most_common(top)


def render_card(docs, cmps, acc, lo, un) -> str:
    n_files = len(files())
    size = sum(p.stat().st_size for p in files()) / 1e9
    by_state = {s: (sum(1 for x in docs["state"] if x == s), sum(1 for x in cmps["state"] if x == s))
                for s in ("clean", "tracking_without_comments", "with_comments_clean", "with_comments_tracking")}
    langs = counts(list(docs["lang"].replace("?", None)), 12)
    n_lang = len({x for x in docs["lang"] if x and x != "?"})
    types = counts(list(docs["type"]), 12)
    pages = [int(x) for x in docs["pages"] if x and x.isdigit() and int(x) > 0]
    cpages = [int(x) for x in cmps["pages"] if x and x.isdigit() and int(x) > 0]
    en = sum(1 for x in docs["lang"] if x == "en")
    pt = sum(1 for x in docs["lang"] if x == "pt")
    state_rows = "\n".join(f"| `{s}` | {d:,} | {c:,} |" for s, (d, c) in by_state.items())
    lang_rows = ", ".join(f"{k} {v:,}" for k, v in langs)
    type_rows = ", ".join(f"{k} {v:,}" for k, v in types)
    n_sets = len({s for t in (docs, cmps) for v in t["sets"] for s in (v or "").split(";") if s})
    c_pdf = sum(1 for x in cmps["pdf"] if x)
    return f"""---
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
| Files | {n_files:,} ({size:.2f} GB), every one pinned in `MANIFEST.sha256.json` |
| Documents (`word/`) | {len(docs):,} DOCX, each with Word's PDF |
| Word compares (`word/`) | {len(cmps):,} redline DOCX (base vs next), {c_pdf:,} with Word's PDF |
| Accept All / Reject All | {len(acc):,} DOCX + PDF (400 redlines × 2) |
| LibreOffice renders | {len(lo):,} PDF, mapped to their Word DOCX/PDF |
| Not yet indexed Word files | {len(un):,} (Word-made DOCX/PDF awaiting indexing) |
| Languages | {n_lang} detected; English {en:,} of {len(docs):,} documents, Portuguese {pt} |
| Pages (Word PDF) | documents: median {statistics.median(pages):.0f}, max {max(pages)}; redlines: median {statistics.median(cpages):.0f}, max {max(cpages)} |

## Quick start

```python
from datasets import load_dataset
from huggingface_hub import hf_hub_download

docs = load_dataset("{REPO}", "documents", split="train")       # one row per DOCX
row = docs.filter(lambda r: r["lang"] == "pt")[0]
docx = hf_hub_download("{REPO}", row["docx_repo_path"], repo_type="dataset")
pdf  = hf_hub_download("{REPO}", row["pdf_repo_path"],  repo_type="dataset")   # Word's PDF of it

pairs = load_dataset("{REPO}", "comparisons", split="train")    # one row per Word compare
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
  <state>/pdf_prior/       an earlier Word build's PDF of the same DOCX ({sum(1 for x in docs['pdf_prior'] if x) + sum(1 for x in cmps['pdf_prior'] if x)} files)
  accept_all/{{docx,pdf}}    Word's Accept All of 400 redlines, and its PDF
  reject_all/{{docx,pdf}}    Word's Reject All of the same 400, and its PDF
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
{state_rows}

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
| `documents` (default) | {len(docs):,} | DOCX with its Word PDF | `id`, `state`, `docx_repo_path`, `pdf_repo_path`, `sets`, `sha256`, `producer`, `lang`, `type`, `topic`, `pages` |
| `comparisons` | {len(cmps):,} | Word compare (redline) | `id`, `base_id`, `next_id`, `state`, `docx_repo_path`, `pdf_repo_path`, `lang`, `type`, `pages` |
| `accept_reject` | {len(acc):,} | Accept All / Reject All of a redline | `key`, `operation`, `status`, `docx_repo_path`, `pdf_repo_path`, `source_docx_repo_path` |
| `libreoffice` | {len(lo):,} | LibreOffice render | `libreoffice_pdf_repo_path`, `word_docx_repo_path`, `word_pdf_repo_path`, `set`, `used_as` |
| `word_unindexed` | {len(un):,} | unindexed Word file | `repo_path`, `sha256`, `bytes`, `producer` |

`*_repo_path` columns are paths in this repo (pass them to `hf_hub_download`); the plain path columns are
relative to the folder of their CSV, as in the original tables.

`lang`, `type`, `topic`, `pages` were added for sampling the comparison site and are **approximate**:
`lang` comes from the docx-corpus metadata where it exists and from text detection otherwise (`?` = undetected);
`type` is the docx-corpus document type, or `synthetic` for the generated test documents; `pages` is the page count
of Word's PDF.

## Composition

* **Languages** (documents): {lang_rows}.
* **Document types**: {type_rows}.
* **Sources**: {n_sets} build sets (see `word/README.md` and `word/PROVENANCE.json`): 1,500 real DOCX from
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
[`layout-2026-10-10`](https://huggingface.co/datasets/{REPO}/tree/layout-2026-10-10).

## Citation

```bibtex
@misc{{neurotic_docx_bench_fixtures,
  title  = {{neurotic\\_docx\\_bench fixtures: DOCX documents with Microsoft Word's PDFs and redlines}},
  author = {{Rodrigues, Arthur}},
  year   = {{2026}},
  howpublished = {{\\url{{https://huggingface.co/datasets/{REPO}}}}},
}}
```

Please also cite docx-corpus (`superdoc-dev/docx-corpus`, SuperDoc) when you use its documents.
"""


def upload() -> None:
    from huggingface_hub import HfApi
    api = HfApi()
    # upload mirrors corpus/ (delete_patterns="*"): a corpus without its binaries would wipe them on the hub.
    want = json.loads((CORPUS / "MANIFEST.sha256.json").read_text())["files"]
    have = {p.relative_to(CORPUS).as_posix() for p in files()}
    if missing := sorted(set(want) - have):
        raise SystemExit(f"{len(missing)} manifest files are not in corpus/ (e.g. {missing[0]}): "
                         "run `uv run bench fixtures download` first, then build, then upload")
    n = len(files())
    api.upload_folder(repo_id=REPO, repo_type="dataset", folder_path=CORPUS,
                      ignore_patterns=["*.log", "*.lock", ".DS_Store", "**/.DS_Store", ".cache/**"],
                      delete_patterns=["*"],  # remote files not in corpus/ go; the old layout stays at the tag
                      commit_message=f"corpus/ by state and id: {n} files, dataset card, viewer configs (2026-10-11)")
    print("uploaded", n)


def verify() -> None:
    from huggingface_hub import HfApi
    remote = {}
    for x in HfApi().list_repo_tree(REPO, repo_type="dataset", recursive=True):
        if getattr(x, "size", None) is not None:
            remote[x.path] = (x.lfs.sha256 if x.lfs else None, x.blob_id)
    bad, small = [], 0
    for p in files():
        k = p.relative_to(CORPUS).as_posix()
        r = remote.get(k)
        if r is None:
            bad.append(("missing", k))
        elif r[0] is not None:
            if r[0] != sha256(p):
                bad.append(("sha256", k))
        else:  # a plain git file: compare the git blob id
            b = p.read_bytes()
            small += 1
            if hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest() != r[1]:
                bad.append(("blob", k))
    extra = set(remote) - {p.relative_to(CORPUS).as_posix() for p in files()} - {".gitattributes"}
    print(f"{len(files())} local, {len(remote)} remote, {len(bad)} bad, {small} of them plain git files checked by blob id, {len(extra)} remote-only")
    for b in bad[:20]:
        print(*b)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    {"build": build, "upload": upload, "verify": verify}[sys.argv[1]]()

"""Base PDFs and source docx of each pair, read from the corpus pool tables.

With ``oracle_roots`` the pairs are the rows of the ``corpora:`` pool CSVs
(``key, base, next``, paths relative to the corpus root without a suffix): the base
PDF comes from the oracle root of the renderer in use, the docx from the Word corpus.
"""

from __future__ import annotations

import csv
from pathlib import Path

from neurotic_docx_bench import cli
from neurotic_docx_bench.config import load_config

KEY = "aaaaaaaaaa_x__vs__bbbbbbbbbb_y_redline_cccccccccc"


def _tree(tmp_path: Path) -> Path:
    for root in ("corpus/word", "corpus/libreoffice"):
        for state in ("clean", "tracking_without_comments"):
            (tmp_path / root / state / "pdf").mkdir(parents=True, exist_ok=True)
        (tmp_path / root / "clean/pdf/aaaaaaaaaa_x.pdf").write_bytes(b"%PDF " + root.encode())
    docx = tmp_path / "corpus/word/clean/docx"
    docx.mkdir(parents=True)
    for stem in ("aaaaaaaaaa_x", "bbbbbbbbbb_y", "dddddddddd_gone_base"):
        (docx / f"{stem}.docx").write_bytes(b"PK")
    pools = tmp_path / "corpus/word/pools"
    pools.mkdir()
    with (pools / "p_pairs.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(("key", "base", "next", "base_name", "next_name", "docx", "pdf", "state"))
        w.writerow((KEY, "clean/docx/aaaaaaaaaa_x", "clean/docx/bbbbbbbbbb_y", "x", "y", "", "", ""))
        w.writerow(("eeeeeeeeee_q__vs__ffffffffff_r_redline_1111111111", "clean/docx/missing",
                    "clean/docx/bbbbbbbbbb_y", "q", "r", "", "", ""))
    p = tmp_path / "bench.yaml"
    p.write_text(
        "renderer: soffice\n"
        "oracle_roots: {word: corpus/word, soffice: corpus/libreoffice}\n"
        "source_of_truth: tracking_without_comments/pdf\n"
        "corpora:\n"
        "  - {name: p, manifest: corpus/word/pools/p_pairs.csv, source_dir: corpus/word}\n"
        "runs: []\n"
    )
    return p


def test_base_pdfs_come_from_the_oracle_root_of_the_renderer(tmp_path: Path) -> None:
    cfg = load_config(_tree(tmp_path))
    assert cli._base_pdf_map(cfg) == {KEY: tmp_path / "corpus/libreoffice/clean/pdf/aaaaaaaaaa_x.pdf"}


def test_source_docx_come_from_the_word_corpus(tmp_path: Path) -> None:
    cfg = load_config(_tree(tmp_path))
    docx = tmp_path / "corpus/word/clean/docx"
    assert cli._source_docx_map(cfg) == {KEY: (docx / "aaaaaaaaaa_x.docx", docx / "bbbbbbbbbb_y.docx")}


def test_word_pdfs_beside_the_ground_truth_seed_the_word_cache(tmp_path: Path) -> None:
    # Word already printed its accept-all; the Word renderer skips what is in its cache
    truth = tmp_path / "accept_all"
    (truth / "docx").mkdir(parents=True)
    (truth / "pdf").mkdir()
    (truth / "docx/k1.docx").write_bytes(b"PK")
    (truth / "docx/k2.docx").write_bytes(b"PK")
    (truth / "pdf/k1.pdf").write_bytes(b"%PDF word")
    cache = tmp_path / "cache"
    assert cli._seed_word_pdfs(truth / "docx", cache, "word") == 1
    assert (cache / "pdf/k1.pdf").read_bytes() == b"%PDF word"
    assert not (cache / "pdf/k2.pdf").exists()
    assert cli._seed_word_pdfs(truth / "docx", tmp_path / "lo", "soffice") == 0
    assert not (tmp_path / "lo").exists()

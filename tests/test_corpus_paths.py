"""corpus_paths: the corpus/word pools (and corpus/libreoffice renders) as the one source of files."""

import csv
from pathlib import Path

import pytest

from neurotic_docx_bench import corpus_paths

K = "aaaaaaaaaa_one__vs__bbbbbbbbbb_two_redline_cccccccccc"
BASE = "clean/docx/aaaaaaaaaa_one"
NEXT = "clean/docx/bbbbbbbbbb_two"
RED = f"tracking_without_comments/docx/{K}.docx"
RED_PDF = f"tracking_without_comments/pdf/{K}.pdf"


def _csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


@pytest.fixture()
def roots(tmp_path: Path) -> tuple[Path, Path]:
    word, lo = tmp_path / "word", tmp_path / "libreoffice"
    _csv(word / "pools/demo_pairs.csv", ["key", "base", "next", "base_name", "next_name", "docx", "pdf", "state"],
         [[K, BASE, NEXT, "one", "two", RED, RED_PDF, "tracking_without_comments"]])
    _csv(word / "pools/demo_renders.csv", ["key", "kind", "docx", "pdf", "state"],
         [["aaaaaaaaaa_one", "document", f"{BASE}.docx", "clean/pdf/aaaaaaaaaa_one.pdf", "clean"],
          ["bbbbbbbbbb_two", "document", f"{NEXT}.docx", "clean/pdf/bbbbbbbbbb_two.pdf", "clean"],
          [K, "comparison", RED, RED_PDF, "tracking_without_comments"]])
    _csv(lo / "word_map.csv", ["libreoffice_pdf", "key", "kind", "word_docx", "set"],
         [[f"tracking_without_comments/pdf/{K}.pdf", K, "comparison", RED, "demo_redlines"],
          ["clean/pdf/aaaaaaaaaa_one.pdf", "aaaaaaaaaa_one", "document", f"{BASE}.docx", "demo_sources"]])
    return word, lo


def test_pairs_resolve_every_path_under_the_corpus(roots):
    word, lo = roots
    (p,) = corpus_paths.pairs("demo", word=word, libreoffice=lo)
    assert p.key == K and p.set == "demo" and p.state == "tracking_without_comments"
    assert p.stem == "one_two"  # the pre-corpus pair stem, base_name + "_" + next_name
    assert (p.base_name, p.next_name) == ("one", "two")
    assert p.base == word / f"{BASE}.docx" and p.next == word / f"{NEXT}.docx"
    assert p.redline == word / RED and p.redline_pdf == word / RED_PDF
    assert p.libreoffice_pdf == lo / f"tracking_without_comments/pdf/{K}.pdf"
    assert p.base_pdf == word / "clean/pdf/aaaaaaaaaa_one.pdf"
    assert p.base_libreoffice_pdf == lo / "clean/pdf/aaaaaaaaaa_one.pdf"
    assert p.next_libreoffice_pdf is None  # no LibreOffice render filed for it


def test_stem_is_the_legacy_redline_name_the_rename_record_kept(roots):
    """The corpus names a document once per distinct bytes, so base_name/next_name can differ
    from the names the compare had; notices/RENAMED.csv holds the file it was copied from."""
    word, lo = roots
    _csv(word / "notices/RENAMED.csv", ["original", "new", "id", "sha256", "set"],
         [["old/docx_redlines_word/other_one_two_word_redline.docx", RED, "cccccccccc", "x", "elsewhere"],
          ["old/docx_redlines_word/one_renamed_two_redline.docx", RED, "cccccccccc", "x", "demo"]])
    (p,) = corpus_paths.pairs("demo", word=word, libreoffice=lo)
    assert p.stem == "one_renamed_two"  # the set's own row wins
    _csv(word / "notices/RENAMED.csv", ["original", "new", "id", "sha256", "set"],
         [["old/docx_redlines_word/other_one_two_word_redline.docx", RED, "cccccccccc", "x", "elsewhere"]])
    corpus_paths.clear_caches()
    (p,) = corpus_paths.pairs("demo", word=word, libreoffice=lo)
    assert p.stem == "other_one_two"  # else any set's


def test_documents_and_comparisons_of_a_set(roots):
    word, lo = roots
    docs = corpus_paths.documents("demo", word=word, libreoffice=lo)
    assert [d.docx for d in docs] == [word / f"{BASE}.docx", word / f"{NEXT}.docx"]
    assert docs[0].libreoffice_pdf == lo / "clean/pdf/aaaaaaaaaa_one.pdf" and docs[1].libreoffice_pdf is None
    (c,) = corpus_paths.comparisons("demo", word=word, libreoffice=lo)
    assert c.docx == word / RED and c.pdf == word / RED_PDF


def test_unknown_set_names_the_pools_there_are(roots):
    word, lo = roots
    with pytest.raises(corpus_paths.UnknownSet, match="demo"):
        corpus_paths.pairs("nope", word=word, libreoffice=lo)


def test_redline_sets_are_the_three_word_compare_sets():
    assert corpus_paths.REDLINE_SETS == ("word_based", "word_based_randomized", "word_redlines_superdoc")


@pytest.mark.skipif(not (corpus_paths.WORD / "pools/word_based_pairs.csv").is_file(), reason="needs corpus/word")
def test_real_word_based_pairs_exist_on_disk():
    ps = corpus_paths.pairs("word_based")
    assert len(ps) == 227
    assert "1_5_line_spacing_id_paraid_overflow_24_id_paraid_overflow" in {p.stem for p in ps}
    assert all(p.base.is_file() and p.next.is_file() and p.redline.is_file() for p in ps)
    assert sum(p.libreoffice_pdf is not None for p in ps) == 227


def test_by_stem_keeps_one_pair_per_legacy_stem_preferring_the_word_capture(roots):
    """Old folders held a pair twice (``<stem>_redline.docx`` and ``<stem>_word_redline.docx``);
    the corpus keeps both compares. Scripts keyed by stem took the ``_word_redline`` capture."""
    word, lo = roots
    k2 = "aaaaaaaaaa_one__vs__bbbbbbbbbb_two_redline_dddddddddd"
    red2 = f"tracking_without_comments/docx/{k2}.docx"
    with open(word / "pools/demo_pairs.csv", "a", newline="") as f:
        csv.writer(f).writerow([k2, BASE, NEXT, "one", "two", red2, f"tracking_without_comments/pdf/{k2}.pdf",
                                "tracking_without_comments"])
    _csv(word / "notices/RENAMED.csv", ["original", "new", "id", "sha256", "set"],
         [["old/docx_redlines_word/one_two_word_redline.docx", RED, "cccccccccc", "x", "demo"],
          ["old/docx_redlines_word/one_two_redline.docx", red2, "dddddddddd", "y", "demo"]])
    corpus_paths.clear_caches()
    assert len(corpus_paths.pairs("demo", word=word, libreoffice=lo)) == 2
    by = corpus_paths.by_stem("demo", word=word, libreoffice=lo)
    assert list(by) == ["one_two"] and by["one_two"].redline == word / RED  # the word capture, though listed first


@pytest.mark.skipif(not (corpus_paths.WORD / "pools/word_based_pairs.csv").is_file(), reason="needs corpus/word")
def test_real_word_based_by_stem_is_202_stems_all_word_captures_where_both_exist():
    assert len(corpus_paths.by_stem("word_based")) == 202

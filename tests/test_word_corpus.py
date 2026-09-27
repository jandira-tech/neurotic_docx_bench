"""The Word corpus (PR 12): one canonical tree for what Word produced.

The fake tree below mirrors the shape of ``grok_run/`` and the corpus folders it
draws from. docx files are real zips (the plan reads their XML for the document
state); every file has its own bytes, so copies can be checked by content and
origins can be checked for being left alone.
"""

from __future__ import annotations

import csv
import json
import zipfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from neurotic_docx_bench import word_corpus
from neurotic_docx_bench.cli import app
from neurotic_docx_bench.ledger import docset as docset_mod

A = "a" * 8
B = "b" * 8
C = "c" * 8
D = "d" * 8
F = "f" * 8
G = "g" * 8
NC = "corpus/no_comments_pdf_was_generated_by_word"


def _put(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _docx(path: Path, text: str, *, tracked: bool = False, comments: bool = False) -> Path:
    """A minimal docx: ``word/document.xml`` carrying ``text``, a tracked insertion when asked,
    and a ``word/comments.xml`` part with one comment when asked."""
    path.parent.mkdir(parents=True, exist_ok=True)
    body = f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>"
    if tracked:
        body += '<w:p><w:ins w:id="1" w:author="x"><w:r><w:t>added</w:t></w:r></w:ins></w:p>'
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        zf.writestr("word/document.xml", f'<w:document xmlns:w="w"><w:body>{body}</w:body></w:document>')
        if comments:
            zf.writestr("word/comments.xml", '<w:comments xmlns:w="w"><w:comment w:id="0"/></w:comments>')
    return path


def make_tree(root: Path) -> Path:
    """A miniature of the material the docsets draw from; every file has its own bytes."""
    g = root / "grok_run"
    # sources_500: docx + Word PDFs; B re-rendered by a later build; C has no PDF at all
    _docx(g / "fixtures_500" / f"{A}.docx", f"docx {A}", tracked=True)
    _docx(g / "fixtures_500" / f"{B}.docx", f"docx {B}", comments=True)
    _docx(g / "fixtures_500" / f"{C}.docx", f"docx {C}")
    _docx(g / "fixtures_500" / f"{G}.docx", f"docx {G}")
    _put(g / "fixtures_500_pdf" / f"{A}.pdf", f"word pdf {A}")
    _put(g / "fixtures_500_pdf" / f"{B}.w26092233.pdf", f"word pdf {B} new build")
    _put(g / "fixtures_500_pdf" / f"{B}.outdated.pdf", f"word pdf {B} old build")
    _put(g / "fixtures_500_pdf" / f"{G}.pdf", f"word pdf {G}")
    _put(g / "fixtures_500_pdf" / "EXTRA_REFERENCES.md", "# Extra Word references\n")
    _put(g / "fixtures_500" / "LICENSE-ODC-BY-1.0.txt", "ODC-By 1.0\n")
    _put(g / "fixtures_500" / "manifest.jsonl", json.dumps({"id": A, "language": "en"}) + "\n")
    _put(g / "MANIFEST.json", json.dumps({"dataset": "superdoc-dev/docx-corpus"}))
    # en_pairs_500: part a/b docx, two Word passes; F was rendered by the second pass only
    for part, stem in (("a", C), ("b", D)):
        _docx(g / f"500_docx_part_{part}_original" / f"{stem}.docx", f"docx part {part} {stem}")
        _put(g / f"500_pdf_part_{part}_original" / f"{stem}.pdf", f"word pdf pass 1 {stem}")
        _put(g / f"500_pdf_part_{part}_run2" / f"{stem}.pdf", f"word pdf pass 2 {stem}")
    _docx(g / "500_docx_part_b_original" / f"{F}.docx", f"docx part b {F}", tracked=True, comments=True)
    _put(g / "500_pdf_part_b_run2" / f"{F}.pdf", f"word pdf pass 2 {F}")
    _put(g / "500_en_sources.jsonl", json.dumps({"part": "a", "id": C}) + "\n")
    _put(g / "500_docx_part_a_word_invalid" / f"{'e' * 8}.docx", "docx word refused")
    # redlines_a100_b10: Word compares of sources_500 documents; A__vs__C has no PDF, G is blacklisted
    _docx(g / "compared_a_100_vs_b_10_docx" / f"{A}__vs__{B}.docx", "word compare a b", tracked=True)
    _docx(g / "compared_a_100_vs_b_10_docx" / f"{A}__vs__{C}.docx", "word compare a c", tracked=True)
    _docx(g / "compared_a_100_vs_b_10_docx" / f"{G}__vs__{B}.docx", "word compare g b", tracked=True)
    _put(g / "compared_a_100_vs_b_10_pdf" / f"{A}__vs__{B}.pdf", "word pdf compare a b")
    _put(g / "compared_a_100_vs_b_10_pdf" / f"{G}__vs__{B}.pdf", "word pdf compare g b")
    _put(g / "compared_a_100_vs_b_10_pdf" / "NOTE", "Expected PDF absences: 1\n")
    # redlines_en_500: Word compares of the en pairs
    _docx(g / "500_extra_docx_redlines" / f"{C}__vs__{D}.docx", "word compare c d", tracked=True, comments=True)
    _put(g / "500_extra_pdf_redlines" / f"{C}__vs__{D}.pdf", "word pdf compare c d")
    _put(g / "word_blacklist" / "blacklist.tsv", f"{G}\tWord hangs\n")
    # oracles_wordpdf: Word renders of the corpus redline docx sets (with their comments)
    _put(g / "wordpdf_redline_oracles" / "word_based" / "x_y_redline.pdf", "word pdf x_y")
    _put(g / "wordpdf_redline_oracles" / "word_based_randomized" / "file_1_file_2_redline.pdf", "word pdf 1_2")
    _put(g / "wordpdf_redline_oracles" / "word_redlines_superdoc" / "p_q_redline.pdf", "word pdf p_q")
    _put(g / "wordpdf_redline_oracles" / "word_based.log", "ERROR something\n")
    wb = root / "corpus" / "word_based"
    _docx(wb / "docx_redlines_word" / "x_y_redline.docx", "docx x_y", tracked=True, comments=True)
    _docx(wb / "docx_redlines_randomized" / "file_1_file_2_redline.docx", "docx 1_2", tracked=True)
    superdoc = root / "corpus" / "word_redlines_superdoc"
    _docx(superdoc / "docx_redlines_word" / "p_q_redline.docx", "docx p_q", tracked=True)
    # oracles_wordpdf_nocomments: the July renders of the same word_based redlines, comments stripped
    _docx(root / NC / "docx_redlines_word" / "x_y_redline.docx", "docx x_y no comments", tracked=True)
    _put(root / NC / "pdf_redlines_word" / "x_y_redline.pdf", "word pdf x_y july")
    return root


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    return make_tree(tmp_path)


def _snapshot(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


# --- the docset table ---------------------------------------------------------


def test_docsets_are_well_formed() -> None:
    names = [d.name for d in word_corpus.DOCSETS]
    assert len(names) == len(set(names))
    by_name = {d.name: d for d in word_corpus.DOCSETS}
    for d in word_corpus.DOCSETS:
        assert d.family in ("render", "redline")
        for s in d.sources:
            assert s.dest in word_corpus.DESTS, (d.name, s.dest)
            assert not (s.fallback and s.dest != "pdf_word"), (d.name, s.origin)
        if d.oracles:
            # Word renders of docx tracked in corpus/: every source names the docx folder it renders
            assert all(s.docx_dir and s.prefix for s in d.sources), d.name
        elif d.family == "redline":
            assert d.sources_docset is not None
            assert by_name[d.sources_docset].family == "render"
    assert word_corpus.docset("sources_500").family == "render"
    assert word_corpus.docset("oracles_wordpdf_nocomments").oracles
    with pytest.raises(word_corpus.CorpusError, match="unknown docset"):
        word_corpus.docset("nope")


# --- the document state ---------------------------------------------------------


def test_docx_state_reads_tracked_changes_and_comments(tmp_path: Path) -> None:
    assert word_corpus.docx_state(_docx(tmp_path / "plain.docx", "t")) == word_corpus.DocxState(False, False)
    assert word_corpus.docx_state(_docx(tmp_path / "ins.docx", "t", tracked=True)) == word_corpus.DocxState(True, False)
    assert word_corpus.docx_state(_docx(tmp_path / "both.docx", "t", tracked=True, comments=True)) == (True, True)
    # an empty comments part is not a commented document
    with zipfile.ZipFile(tmp_path / "empty.docx", "w") as zf:
        zf.writestr("word/document.xml", '<w:document><w:body><w:p><w:del w:id="2"/></w:p></w:body></w:document>')
        zf.writestr("word/comments.xml", "<w:comments/>")
    assert word_corpus.docx_state(tmp_path / "empty.docx") == (True, False)
    # tracked changes in a header count; a docx without a document part is a plain document
    with zipfile.ZipFile(tmp_path / "header.docx", "w") as zf:
        zf.writestr("word/document.xml", "<w:document/>")
        zf.writestr("word/header1.xml", '<w:hdr><w:p><w:rPrChange w:id="3"/></w:p></w:hdr>')
    assert word_corpus.docx_state(tmp_path / "header.docx") == (True, False)
    _put(tmp_path / "broken.docx", "not a zip")
    with pytest.raises(word_corpus.CorpusError, match="not a docx"):
        word_corpus.docx_state(tmp_path / "broken.docx")
    assert word_corpus.markup(word_corpus.DocxState(False, False)) == "none"
    assert word_corpus.markup(word_corpus.DocxState(True, False)) == "tracked"
    assert word_corpus.markup(word_corpus.DocxState(False, True)) == "comments"
    assert word_corpus.markup(word_corpus.DocxState(True, True)) == "tracked_comments"


# --- planning ------------------------------------------------------------------


def test_plan_render_docset_picks_the_current_word_reference(tree: Path) -> None:
    plan = word_corpus.plan(tree, word_corpus.docset("sources_500"))
    dst = {item.dst: item.src.as_posix() for item in plan.items}
    assert dst[f"docx/{A}.docx"] == f"grok_run/fixtures_500/{A}.docx"
    assert dst[f"pdf_word/{A}.pdf"] == f"grok_run/fixtures_500_pdf/{A}.pdf"
    assert dst[f"pdf_word/{B}.pdf"] == f"grok_run/fixtures_500_pdf/{B}.w26092233.pdf"
    assert dst[f"pdf_word_prior/{B}.pdf"] == f"grok_run/fixtures_500_pdf/{B}.outdated.pdf"
    assert "notes/EXTRA_REFERENCES.md" in dst
    assert dst["LICENSE-ODC-BY-1.0.txt"] == "grok_run/fixtures_500/LICENSE-ODC-BY-1.0.txt"
    # C has no Word PDF: it is not part of the docset (not a key, not copied)
    assert plan.keys == (A, B, G)
    assert plan.absent == (C,)
    assert f"docx/{C}.docx" not in dst
    assert plan.superseded == (B,)
    assert plan.filled == ()
    states = {d.key: (d.tracked_changes, d.comments, d.pdf_markup) for d in plan.documents}
    assert states == {A: (True, False, "tracked"), B: (False, True, "comments"), G: (False, False, "none")}


def test_plan_render_docset_uses_the_first_word_pass_and_fills_from_the_second(tree: Path) -> None:
    plan = word_corpus.plan(tree, word_corpus.docset("en_pairs_500"))
    dst = {item.dst: item.src.as_posix() for item in plan.items}
    assert dst[f"pdf_word/{C}.pdf"] == f"grok_run/500_pdf_part_a_original/{C}.pdf"
    assert dst[f"pdf_word/{F}.pdf"] == f"grok_run/500_pdf_part_b_run2/{F}.pdf"
    assert dst[f"docx/{D}.docx"] == f"grok_run/500_docx_part_b_original/{D}.docx"
    assert not any(k.startswith("pdf_word_prior/") for k in dst)
    assert plan.keys == (C, D, F)
    assert plan.absent == ()
    assert plan.filled == (F,)
    assert plan.excluded == {"500_docx_part_a_word_invalid": ("e" * 8,)}
    origins = {d.key: d.pdf_word_origin for d in plan.documents}
    assert origins == {
        C: "grok_run/500_pdf_part_a_original",
        D: "grok_run/500_pdf_part_b_original",
        F: "grok_run/500_pdf_part_b_run2",
    }
    assert {d.key: d.pdf_markup for d in plan.documents}[F] == "tracked_comments"


def test_plan_redline_docset_keeps_only_pairs_word_rendered(tree: Path) -> None:
    plan = word_corpus.plan(tree, word_corpus.docset("redlines_a100_b10"))
    assert [(p.pair_stem, p.base, p.next, p.pdf, p.tracked_changes, p.comments, p.pdf_markup) for p in plan.pairs] == [
        (f"{A}__vs__{B}", A, B, f"pdf_redline_word/{A}__vs__{B}.pdf", True, False, "tracked"),
    ]
    assert plan.keys == (f"{A}__vs__{B}",)
    assert plan.absent == (f"{A}__vs__{C}",)
    # G is blacklisted: the pair that touches it leaves with it, PDF or not
    assert plan.excluded == {"word_blacklist": (G,), "word_blacklist_pairs": (f"{G}__vs__{B}",)}
    dst = {item.dst for item in plan.items}
    assert f"docx_redline/{A}__vs__{B}.docx" in dst
    assert f"docx_redline/{A}__vs__{C}.docx" not in dst
    assert f"docx_redline/{G}__vs__{B}.docx" not in dst and f"pdf_redline_word/{G}__vs__{B}.pdf" not in dst
    assert "notes/NOTE" in dst


def test_plan_oracles_docset_keys_are_the_corpus_pair_keys(tree: Path) -> None:
    plan = word_corpus.plan(tree, word_corpus.docset("oracles_wordpdf"))
    dst = {item.dst: item.src.as_posix() for item in plan.items}
    origin = "grok_run/wordpdf_redline_oracles/word_based"
    assert dst["word_based/pdf_redline_word/x_y_redline.pdf"] == f"{origin}/x_y_redline.pdf"
    assert "word_based.log" not in " ".join(dst)
    # pipeline.oracle_pair_key("file_1_file_2_redline") is "file_1_file_2": the pair
    # key the scorer uses, so an oracles docset id lines up with a run's docset id.
    assert plan.keys == ("file_1_file_2", "p_q", "x_y")
    markup = {d.stem: d.pdf_markup for d in plan.documents}
    assert markup == {"x_y_redline": "tracked_comments", "file_1_file_2_redline": "tracked", "p_q_redline": "tracked"}
    # the July renders of the same pairs, comments stripped: same key, another state
    july = word_corpus.plan(tree, word_corpus.docset("oracles_wordpdf_nocomments"))
    assert july.keys == ("x_y",)
    assert [(d.key, d.docx, d.pdf_markup) for d in july.documents] == [
        ("x_y", f"{NC}/docx_redlines_word/x_y_redline.docx", "tracked")
    ]
    assert {item.src.as_posix() for item in july.items} == {f"{NC}/pdf_redlines_word/x_y_redline.pdf"}


def test_plan_reports_a_pdf_whose_docx_is_gone(tree: Path) -> None:
    (tree / "grok_run" / "fixtures_500" / f"{A}.docx").unlink()
    plan = word_corpus.plan(tree, word_corpus.docset("sources_500"))
    assert plan.orphans == (f"pdf_word/{A}.pdf",)


def test_plan_refuses_two_current_references_for_one_stem(tree: Path) -> None:
    _put(tree / "grok_run" / "fixtures_500_pdf" / f"{B}.pdf", "a second current reference")
    with pytest.raises(word_corpus.CorpusError, match="two current references"):
        word_corpus.plan(tree, word_corpus.docset("sources_500"))


def test_plan_refuses_names_it_cannot_place(tree: Path) -> None:
    _put(tree / "grok_run" / "fixtures_500_pdf" / f"{A}.draft.pdf", "a tag nobody declared")
    with pytest.raises(word_corpus.CorpusError, match="unexpected name"):
        word_corpus.plan(tree, word_corpus.docset("sources_500"))
    _put(tree / "grok_run" / "500_pdf_part_a_original" / f"{D}.pdf", "same stem as part b")
    with pytest.raises(word_corpus.CorpusError, match="two current references"):
        word_corpus.plan(tree, word_corpus.docset("en_pairs_500"))
    _docx(tree / "grok_run" / "compared_a_100_vs_b_10_docx" / "nopair.docx", "no __vs__ in the name")
    with pytest.raises(word_corpus.CorpusError, match="not a <base>__vs__<next>"):
        word_corpus.plan(tree, word_corpus.docset("redlines_a100_b10"))


def test_plan_without_a_blacklist_excludes_nothing(tree: Path) -> None:
    (tree / "grok_run" / "word_blacklist" / "blacklist.tsv").unlink()
    plan = word_corpus.plan(tree, word_corpus.docset("redlines_a100_b10"))
    assert plan.excluded == {}
    assert plan.keys == (f"{A}__vs__{B}", f"{G}__vs__{B}")


def test_plan_refuses_a_missing_origin(tree: Path) -> None:
    with pytest.raises(word_corpus.CorpusError, match="500_pdf_part_b_run2"):
        word_corpus.plan(tree / "nowhere", word_corpus.docset("en_pairs_500"))
    # a redline docset also needs its sources docset's docx (the blacklist is narrowed to them)
    missing = word_corpus.missing_origins(tree / "nowhere", word_corpus.docset("redlines_en_500"))
    assert "grok_run/500_docx_part_a_original" in missing


def test_copy_file_clones_on_apfs_and_copies_elsewhere(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    src = _put(tmp_path / "src.bin", "bytes")
    monkeypatch.setattr(word_corpus, "_clone_enabled", lambda: True)
    monkeypatch.setattr(word_corpus, "CLONE_COMMAND", ("false",))  # clone refused: plain copy
    word_corpus.copy_file(src, tmp_path / "out" / "a.bin")
    assert (tmp_path / "out" / "a.bin").read_text() == "bytes"
    monkeypatch.setattr(word_corpus, "CLONE_COMMAND", ("cp",))  # clone accepted
    word_corpus.copy_file(src, tmp_path / "out" / "b.bin")
    assert (tmp_path / "out" / "b.bin").read_text() == "bytes"
    assert not (tmp_path / "out" / "b.bin").samefile(src)


def test_plan_oracles_reports_docx_without_a_render_and_renders_without_a_docx(tree: Path) -> None:
    _docx(tree / "corpus" / "word_based" / "docx_redlines_word" / "m_n_redline.docx", "docx m_n")
    _put(tree / "grok_run" / "wordpdf_redline_oracles" / "word_based" / "z_z_redline.pdf", "word pdf z_z")
    # two capture variants of one pair, each rendered: two files, one scorer key
    _docx(tree / "corpus" / "word_based" / "docx_redlines_word" / "x_y_word_redline.docx", "docx x_y word variant")
    _put(tree / "grok_run" / "wordpdf_redline_oracles" / "word_based" / "x_y_word_redline.pdf", "word pdf x_y variant")
    plan = word_corpus.plan(tree, word_corpus.docset("oracles_wordpdf"))
    assert plan.absent == ("word_based/m_n_redline",)
    assert plan.orphans == ("word_based/pdf_redline_word/z_z_redline.pdf",)
    assert "z_z" not in plan.keys
    assert plan.corpora["word_based"] == {
        "docx_dir": "corpus/word_based/docx_redlines_word",
        "n_files": 2,
        "n_keys": 1,
        "docset_id": docset_mod.docset_id(("x_y",)),
    }
    assert [(d.key, d.stem) for d in plan.documents if d.corpus == "word_based"] == [
        ("x_y", "x_y_redline"),
        ("x_y", "x_y_word_redline"),
    ]
    assert {item.dst for item in plan.items} >= {
        "word_based/pdf_redline_word/x_y_redline.pdf",
        "word_based/pdf_redline_word/x_y_word_redline.pdf",
    }


# --- building ------------------------------------------------------------------


def test_build_copies_and_leaves_the_origins_alone(tree: Path) -> None:
    before = _snapshot(tree)
    dest = tree / "corpus" / "word"
    report = word_corpus.build(tree, dest)
    after = _snapshot(tree)
    assert {k: v for k, v in after.items() if not k.startswith("corpus/word/")} == before
    assert report.copied > 0 and report.skipped == 0 and report.overwritten == 0
    assert (dest / "sources_500" / "pdf_word" / f"{B}.pdf").read_text() == f"word pdf {B} new build"
    assert (dest / "sources_500" / "pdf_word_prior" / f"{B}.pdf").read_text() == f"word pdf {B} old build"
    assert not (dest / "sources_500" / "docx" / f"{C}.docx").exists()
    assert (dest / "redlines_en_500" / "docx_redline" / f"{C}__vs__{D}.docx").read_bytes() == (
        tree / "grok_run" / "500_extra_docx_redlines" / f"{C}__vs__{D}.docx"
    ).read_bytes()
    assert (dest / "oracles_wordpdf_nocomments" / "word_based" / "pdf_redline_word" / "x_y_redline.pdf").is_file()
    manifest = json.loads((dest / word_corpus.MANIFEST_NAME).read_text())
    assert f"sources_500/pdf_word/{A}.pdf" in manifest["files"]
    assert manifest["n_files"] == report.copied + report.written
    assert (dest / "README.md").is_file()


def test_build_writes_provenance_tables_and_the_index(tree: Path) -> None:
    dest = tree / "corpus" / "word"
    word_corpus.build(tree, dest)
    prov = json.loads((dest / "sources_500" / word_corpus.PROVENANCE_NAME).read_text())
    assert prov["license"] == "ODC-By-1.0"
    assert prov["dataset"] == "superdoc-dev/docx-corpus"
    assert prov["producer"] == word_corpus.WORD_PRODUCER
    assert prov["origins"]["pdf_word"] == ["grok_run/fixtures_500_pdf"]
    assert prov["counts"] == {"docx": 3, "pdf_word": 3, "pdf_word_prior": 1}
    assert prov["absent"] == [C]
    assert prov["superseded"] == [B]
    assert prov["docset_id"] == docset_mod.docset_id((A, B, G))
    assert prov["n_keys"] == 3
    markup = {"comments": 1, "none": 1, "tracked": 1}
    assert prov["states"] == {"tracked_changes": 1, "comments": 1, "pdf_markup": markup}
    rows = _rows(dest / "sources_500" / word_corpus.DOCUMENTS_NAME)
    assert [r["key"] for r in rows] == [A, B, G]
    assert rows[1] == {
        "key": B,
        "docx": f"docx/{B}.docx",
        "pdf_word": f"pdf_word/{B}.pdf",
        "pdf_word_prior": f"pdf_word_prior/{B}.pdf",
        "pdf_word_origin": "grok_run/fixtures_500_pdf",
        "tracked_changes": "false",
        "comments": "true",
        "pdf_markup": "comments",
    }
    en = json.loads((dest / "en_pairs_500" / word_corpus.PROVENANCE_NAME).read_text())
    assert en["filled"] == [F]
    assert en["origins"]["pdf_word"] == [
        "grok_run/500_pdf_part_a_original",
        "grok_run/500_pdf_part_b_original",
        "grok_run/500_pdf_part_a_run2",
        "grok_run/500_pdf_part_b_run2",
    ]
    pairs = _rows(dest / "redlines_a100_b10" / word_corpus.PAIRS_NAME)
    assert pairs == [
        {
            "pair_stem": f"{A}__vs__{B}",
            "base": A,
            "next": B,
            "docx_redline": f"docx_redline/{A}__vs__{B}.docx",
            "pdf_redline_word": f"pdf_redline_word/{A}__vs__{B}.pdf",
            "tracked_changes": "true",
            "comments": "false",
            "pdf_markup": "tracked",
        }
    ]
    prov_r = json.loads((dest / "redlines_a100_b10" / word_corpus.PROVENANCE_NAME).read_text())
    assert prov_r["sources_docset"] == "sources_500"
    assert prov_r["excluded"] == {"word_blacklist": [G], "word_blacklist_pairs": [f"{G}__vs__{B}"]}
    oracles = _rows(dest / "oracles_wordpdf" / word_corpus.ORACLES_NAME)
    # rows follow the docset's sources: word_based, word_based_randomized, word_redlines_superdoc
    assert [(r["corpus"], r["key"], r["pdf_markup"]) for r in oracles] == [
        ("word_based", "x_y", "tracked_comments"),
        ("word_based_randomized", "file_1_file_2", "tracked"),
        ("word_redlines_superdoc", "p_q", "tracked"),
    ]
    # the corpus-wide index: one row per document of every docset, state included
    index = _rows(dest / word_corpus.INDEX_NAME)
    assert list(index[0]) == [
        "docset",
        "family",
        "key",
        "stem",
        "docx",
        "pdf",
        "tracked_changes",
        "comments",
        "pdf_markup",
    ]
    by = {(r["docset"], r["stem"]): r for r in index}
    assert by[("sources_500", A)]["pdf"] == f"sources_500/pdf_word/{A}.pdf"
    assert by[("oracles_wordpdf", "x_y_redline")]["pdf_markup"] == "tracked_comments"
    assert by[("oracles_wordpdf_nocomments", "x_y_redline")]["pdf_markup"] == "tracked"
    assert by[("redlines_a100_b10", f"{A}__vs__{B}")]["docx"] == f"redlines_a100_b10/docx_redline/{A}__vs__{B}.docx"
    assert len(index) == 3 + 3 + 1 + 1 + 3 + 1


def test_build_is_idempotent_and_refuses_to_overwrite_a_changed_file(tree: Path) -> None:
    dest = tree / "corpus" / "word"
    word_corpus.build(tree, dest)
    again = word_corpus.build(tree, dest)
    assert again.copied == 0 and again.skipped > 0
    target = dest / "sources_500" / "pdf_word" / f"{A}.pdf"
    target.write_text("edited by hand")
    with pytest.raises(word_corpus.CorpusError, match="differs"):
        word_corpus.build(tree, dest)
    forced = word_corpus.build(tree, dest, force=True)
    assert forced.overwritten == 1
    assert target.read_text() == f"word pdf {A}"


def test_build_only_and_dry_run(tree: Path) -> None:
    dest = tree / "corpus" / "word"
    dry = word_corpus.build(tree, dest, only=("sources_500",), dry_run=True)
    assert dry.copied > 0 and not dest.exists()
    report = word_corpus.build(tree, dest, only=("sources_500",))
    assert report.docsets == ("sources_500",)
    assert (dest / "sources_500").is_dir() and not (dest / "en_pairs_500").exists()
    with pytest.raises(word_corpus.CorpusError, match="unknown docset"):
        word_corpus.build(tree, dest, only=("nope",))


def test_check_reports_drift(tree: Path) -> None:
    dest = tree / "corpus" / "word"
    word_corpus.build(tree, dest)
    assert word_corpus.check(dest).ok
    (dest / "sources_500" / "pdf_word" / f"{A}.pdf").write_text("drifted")
    report = word_corpus.check(dest)
    assert report.mismatched == (f"sources_500/pdf_word/{A}.pdf",)
    with pytest.raises(word_corpus.CorpusError, match="no MANIFEST"):
        word_corpus.check(tree / "elsewhere")


def test_corpus_entries_point_at_pairs_and_source_docx() -> None:
    entries = word_corpus.corpus_entries()
    by_name = {e.name: e for e in entries}
    assert by_name["word_redlines_en_500"].manifest == "corpus/word/redlines_en_500/pairs.csv"
    assert by_name["word_redlines_en_500"].source_dir == "corpus/word/en_pairs_500/docx"
    assert by_name["word_redlines_a100_b10"].source_dir == "corpus/word/sources_500/docx"
    assert "word_sources_500" not in by_name


def test_summary_lists_every_docset_with_its_counts(tree: Path) -> None:
    dest = tree / "corpus" / "word"
    word_corpus.build(tree, dest)
    rows = word_corpus.summary(dest)
    assert [r["name"] for r in rows] == [d.name for d in word_corpus.DOCSETS]
    assert rows[0]["n_keys"] == 3 and rows[0]["family"] == "render"
    assert rows[0]["tracked_changes"] == 1 and rows[0]["comments"] == 1
    assert word_corpus.summary(tree / "elsewhere") == []


# --- CLI -----------------------------------------------------------------------


def test_cli_build_check_list(tree: Path) -> None:
    runner = CliRunner()
    dest = tree / "corpus" / "word"
    res = runner.invoke(app, ["corpus", "build", "--root", str(tree), "--dest", str(dest)])
    assert res.exit_code == 0, res.output
    assert "copied" in res.output
    assert "left out" in res.output
    res = runner.invoke(app, ["corpus", "check", "--dest", str(dest)])
    assert res.exit_code == 0, res.output
    res = runner.invoke(app, ["corpus", "list", "--dest", str(dest)])
    assert res.exit_code == 0, res.output
    assert "redlines_en_500" in res.output and "oracles_wordpdf_nocomments" in res.output
    (dest / "sources_500" / "pdf_word" / f"{A}.pdf").write_text("drifted")
    res = runner.invoke(app, ["corpus", "check", "--dest", str(dest)])
    assert res.exit_code == 1
    res = runner.invoke(app, ["corpus", "build", "--root", str(tree), "--dest", str(dest)])
    assert res.exit_code == 1 and "differs" in res.output
    res = runner.invoke(app, ["corpus", "build", "--root", str(tree / "nowhere"), "--dest", str(dest)])
    assert res.exit_code == 1

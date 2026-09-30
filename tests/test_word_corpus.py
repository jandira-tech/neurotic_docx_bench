"""The Word corpus (PR 12): ``corpus/word/<state>/docx|pdf|pdf_prior`` for what Word produced.

The fake tree below mirrors the shape of ``grok_run/``, the corpus folders and the
``_fixtures`` folder the sets draw from. docx files are real zips (the plan reads
their XML for the document state); PDFs carry a producer string (the plan reads it
to refuse what Word did not render); every file has its own bytes unless a test
wants two origins to hold the same document.
"""

from __future__ import annotations

import csv
import json
import zipfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from neurotic_docx_bench import hub, word_corpus
from neurotic_docx_bench.cli import app
from neurotic_docx_bench.word_corpus import DocxState

A = "a" * 8
B = "b" * 8
C = "c" * 8
D = "d" * 8
E = "e" * 8
F = "f" * 8
G = "g" * 8
H = "h" * 8
NC = "grok_run/no_comments_pdf_was_generated_by_word"
WB = "grok_run/word_based"
SD = "grok_run/word_redlines_superdoc"
FIX = word_corpus.FIXTURES_PREFIX
QUARTZ = rb"macOS Version 26.6.2 \(Build 25G83\) Quartz PDFContext"
LIBREOFFICE_HEX = b"FEFF004C0069006200720065004F00660066006900630065"  # "LibreOffice" in UTF-16BE


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


def _pdf(path: Path, text: str, *, producer: str = "quartz") -> Path:
    """A PDF-shaped file whose Info dictionary sits at the tail, as Word and LibreOffice write it.

    ``quartz``: what Word for Mac writes (a literal string with escaped parentheses);
    ``creator``: the older Word export (``/Creator(Microsoft Word)``, no ``/Producer``);
    ``libreoffice``: a UTF-16 hex string; anything else is written as a literal producer.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if producer == "quartz":
        info = b"<</Creator (Word)/Producer (" + QUARTZ + b")>>"
    elif producer == "creator":
        info = b"<</Creator(Microsoft Word)>>"
    elif producer == "libreoffice":
        info = b"<</Producer<" + LIBREOFFICE_HEX + b">>>"
    else:
        info = b"<</Producer (" + producer.encode() + b")>>"
    body = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\n" + text.encode() + b"\n"
    path.write_bytes(body + b"2 0 obj" + info + b"endobj\ntrailer<</Info 2 0 R>>\n%%EOF\n")
    return path


def _mapping(path: Path, pairs: list[tuple[str, str, str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["pair_stem", "base", "next", "origin", "docx_source_base", "docx_source_next", "missing"])
        for stem, base, nxt in pairs:
            w.writerow([stem, base, nxt, "both", f"{base}.docx", f"{nxt}.docx", ""])
    return path


def make_tree(root: Path) -> Path:
    """A miniature of the material the sets draw from."""
    g = root / "grok_run"
    # sources_500: docx + tagged Word PDFs; B re-rendered by a later build; C has no PDF at all
    _docx(g / "fixtures_500" / f"{A}.docx", f"docx {A}", tracked=True)
    _docx(g / "fixtures_500" / f"{B}.docx", f"docx {B}", comments=True)
    _docx(g / "fixtures_500" / f"{C}.docx", f"docx {C}")
    _docx(g / "fixtures_500" / f"{G}.docx", f"docx {G}")
    _docx(g / "fixtures_500" / "~$lock.docx", "a Word lock file")
    _put(g / "fixtures_500" / "LICENSE-ODC-BY-1.0.txt", "ODC-By 1.0")
    _put(g / "fixtures_500" / "NOTICE", "notice")
    _put(g / "fixtures_500" / "manifest.jsonl", "{}\n")
    _put(g / "fixtures_500" / "split_a_100_b_10.json", "{}")
    _put(g / "MANIFEST.json", "{}")
    _pdf(g / "fixtures_500_pdf" / f"{A}.pdf", f"pdf {A}")
    _pdf(g / "fixtures_500_pdf" / f"{B}.w26092233.pdf", f"pdf {B} rebuilt")
    _pdf(g / "fixtures_500_pdf" / f"{B}.outdated.pdf", f"pdf {B} first")
    _pdf(g / "fixtures_500_pdf" / f"{G}.pdf", f"pdf {G}")
    _pdf(g / "fixtures_500_pdf" / "orphan.pdf", "a render whose docx is gone")
    _put(g / "fixtures_500_pdf" / "EXTRA_REFERENCES.md", "extra")
    # en_pairs_500: D and E in part a (E is Word-invalid), F and H in part b; H's first-pass PDF is
    # missing and the second pass fills it; F's second-pass render is redundant and stays behind
    _docx(g / "500_docx_part_a_original" / f"{D}.docx", f"docx {D}")
    _docx(g / "500_docx_part_a_original" / f"{E}.docx", f"docx {E}")
    _docx(g / "500_docx_part_a_word_invalid" / f"{E}.docx", f"docx {E}")
    _docx(g / "500_docx_part_b_original" / f"{F}.docx", f"docx {F}")
    _docx(g / "500_docx_part_b_original" / f"{H}.docx", f"docx {H}")
    _pdf(g / "500_pdf_part_a_original" / f"{D}.pdf", f"pdf {D}")
    _pdf(g / "500_pdf_part_b_original" / f"{F}.pdf", f"pdf {F}")
    _pdf(g / "500_pdf_part_a_run2" / f"{D}.pdf", f"pdf {D} run2")
    _pdf(g / "500_pdf_part_b_run2" / f"{F}.pdf", f"pdf {F} run2")
    _pdf(g / "500_pdf_part_b_run2" / f"{H}.pdf", f"pdf {H} run2")
    _put(g / "500_en_pairs.tsv", f"{D}\t{F}\n{F}\t{H}\n")
    _put(g / "500_en_sources.jsonl", "{}\n")
    # redlines_a100_b10: A vs B rendered; A vs C names a document without a Word PDF; G vs B has no PDF
    _docx(g / "compared_a_100_vs_b_10_docx" / f"{A}__vs__{B}.docx", "compare A B", tracked=True)
    _docx(g / "compared_a_100_vs_b_10_docx" / f"{A}__vs__{C}.docx", "compare A C", tracked=True)
    _docx(g / "compared_a_100_vs_b_10_docx" / f"{G}__vs__{B}.docx", "compare G B", tracked=True)
    _pdf(g / "compared_a_100_vs_b_10_pdf" / f"{A}__vs__{B}.pdf", "pdf compare A B")
    _pdf(g / "compared_a_100_vs_b_10_pdf" / f"{A}__vs__{C}.pdf", "pdf compare A C")
    _put(g / "compared_a_100_vs_b_10_pdf" / "NOTE", "ten pairs are absent")
    # redlines_en_500: D vs F rendered; F vs H touches the blacklisted H; D vs H was rejected
    _docx(g / "500_extra_docx_redlines" / f"{D}__vs__{F}.docx", "compare D F", tracked=True, comments=True)
    _docx(g / "500_extra_docx_redlines" / f"{F}__vs__{H}.docx", "compare F H", tracked=True)
    _docx(g / "500_extra_docx_redlines" / f"{D}__vs__{H}.docx", "compare D H", tracked=True)
    _pdf(g / "500_extra_pdf_redlines" / f"{D}__vs__{F}.pdf", "pdf compare D F")
    _pdf(g / "500_extra_pdf_redlines" / f"{F}__vs__{H}.pdf", "pdf compare F H")
    _pdf(g / "500_extra_pdf_redlines" / f"{D}__vs__{H}.pdf", "pdf compare D H")
    _docx(g / "500_extra_redlines_rejected" / "500_extra_docx_redlines" / f"{D}__vs__{H}.docx", "compare D H")
    _put(g / "word_blacklist" / "blacklist.tsv", f"{H}\tWord hangs/crashes\n")
    # word_based: x, y, z with the pairs x_y (tracked + comments) and y_z (a `_word_redline` name);
    # the September Word renders live under grok_run/wordpdf_redline_oracles
    _docx(root / WB / "docx_source" / "x.docx", "docx x")
    _docx(root / WB / "docx_source" / "y.docx", "docx y")
    _docx(root / WB / "docx_source" / "z.docx", "docx z")
    _mapping(root / WB / "centralized_mapping.csv", [("x_y", "x", "y"), ("y_z", "y", "z")])
    _docx(root / WB / "docx_redlines_word" / "x_y_redline.docx", "redline x y", tracked=True, comments=True)
    _docx(root / WB / "docx_redlines_word" / "y_z_word_redline.docx", "redline y z", tracked=True)
    _pdf(g / "wordpdf_redline_oracles" / "word_based" / "x_y_redline.pdf", "pdf redline x y")
    _pdf(g / "wordpdf_redline_oracles" / "word_based" / "y_z_word_redline.pdf", "pdf redline y z")
    # the sealed holdout lists, in the legacy <base>_<next> key space
    _put(root / WB / "holdout.txt", "# sealed\nx_y\nfile_1_file_2\nnot_a_pair\n")
    _put(root / SD / "holdout.txt", "p_q\n")
    # Word's accept-all of x_y, saved by Word (no Word PDF of it)
    _docx(root / WB / "word_working_roundtrip" / "x_y_word_redline_accepted.docx", "x y accepted", comments=True)
    _pdf(g / "wr0929" / "word_based_accepted_word_pdf" / "x_y_word_redline_accepted.pdf", "pdf x y accepted")
    # word_based_randomized and word_redlines_superdoc: one pair each
    _docx(root / WB / "docx_source_randomized" / "file_1.docx", "docx file_1")
    _docx(root / WB / "docx_source_randomized" / "file_2.docx", "docx file_2")
    _put(root / WB / "docx_source_randomized" / "name_map.csv", "a,b\n")
    _mapping(root / WB / "centralized_mapping_randomized.csv", [("file_1_file_2", "file_1", "file_2")])
    _docx(root / WB / "docx_redlines_randomized" / "file_1_file_2_redline.docx", "redline 1 2", tracked=True)
    _put(root / WB / "docx_redlines_randomized" / "batch_retry_log.csv", "a,b\n")
    _pdf(g / "wordpdf_redline_oracles" / "word_based_randomized" / "file_1_file_2_redline.pdf", "pdf redline 1 2")
    _docx(root / SD / "docx_source" / "p.docx", "docx p")
    _docx(root / SD / "docx_source" / "q.docx", "docx q")
    _mapping(root / SD / "centralized_mapping.csv", [("p_q", "p", "q")])
    _docx(root / SD / "docx_redlines_word" / "p_q_redline.docx", "redline p q", tracked=True)
    _pdf(g / "wordpdf_redline_oracles" / "word_redlines_superdoc" / "p_q_redline.pdf", "pdf redline p q")
    # the September compare run: fresh compares of the same pairs (x_y differs from the old docx;
    # y_z is named `_redline` where the old one was `_word_redline`), Word PDFs beside them
    for name in ("word_based", "word_based_randomized", "word_redlines_superdoc"):
        _put(g / "wr0926" / name / "map.tsv", "p0001\tx_y\n")
        _put(g / "wr0926" / name / "identity.log", "ok\n")
    _docx(g / "wr0926" / "word_based" / "docx" / "x_y_redline.docx", "redline x y 0926", tracked=True, comments=True)
    _docx(g / "wr0926" / "word_based" / "docx" / "y_z_redline.docx", "redline y z 0926", tracked=True)
    _pdf(g / "wr0926" / "word_based" / "pdf" / "x_y_redline.pdf", "pdf redline x y 0926")
    _docx(
        g / "wr0926" / "word_based_randomized" / "docx" / "file_1_file_2_redline.docx", "redline 1 2 0926", tracked=True
    )
    _pdf(g / "wr0926" / "word_based_randomized" / "pdf" / "file_1_file_2_redline.pdf", "pdf redline 1 2 0926")
    _docx(g / "wr0926" / "word_redlines_superdoc" / "docx" / "p_q_redline.docx", "redline p q 0926", tracked=True)
    _pdf(g / "wr0926" / "word_redlines_superdoc" / "pdf" / "p_q_redline.pdf", "pdf redline p q 0926")
    # nocomments: the same x and y docx (same bytes) with July Word PDFs, and the x_y compare with
    # its comments stripped (other bytes, so another document); z has no July PDF
    for name in ("x", "y", "z"):
        (root / NC / "docx_source").mkdir(parents=True, exist_ok=True)
        same = (root / WB / "docx_source" / f"{name}.docx").read_bytes()
        (root / NC / "docx_source" / f"{name}.docx").write_bytes(same)
    _pdf(root / NC / "pdf_source" / "x.pdf", "pdf x july")
    _pdf(root / NC / "pdf_source" / "y.pdf", "pdf y july")
    _mapping(root / NC / "centralized_mapping.csv", [("x_y", "x", "y"), ("y_z", "y", "z")])
    _docx(root / NC / "docx_redlines_word" / "x_y_redline.docx", "redline x y nocomments", tracked=True)
    _pdf(root / NC / "pdf_redlines_word" / "x_y_redline.pdf", "pdf redline x y nocomments")
    _docx(root / NC / "docx_source_randomized" / "file_1.docx", "docx file_1 nocomments")
    _pdf(root / NC / "pdf_source_randomized" / "file_1.pdf", "pdf file_1 nocomments")
    _mapping(root / NC / "centralized_mapping_randomized.csv", [("file_1_file_2", "file_1", "file_2")])
    _docx(root / NC / "docx_redlines_randomized" / "file_1_file_2_redline.docx", "redline 1 2 nc", tracked=True)
    _pdf(root / NC / "pdf_redlines_randomized" / "file_1_file_2_redline.pdf", "pdf redline 1 2 nc")
    # pdf_fill_0928: z (word_based, registered without a Word PDF) rendered now; G and B with the
    # renders they already had; the G vs B compare (no PDF until now) through the set's own mapping
    pf = g / "wr0928" / "pdf_fill"
    (pf / "documents_docx").mkdir(parents=True)
    (pf / "documents_pdf").mkdir(parents=True)
    (pf / "documents_docx" / "z_doc.docx").write_bytes((root / WB / "docx_source" / "z.docx").read_bytes())
    _pdf(pf / "documents_pdf" / "z_doc.pdf", "pdf z filled")
    for name, doc, render in (("g_doc", G, f"{G}.pdf"), ("b_doc", B, f"{B}.w26092233.pdf")):
        (pf / "documents_docx" / f"{name}.docx").write_bytes((g / "fixtures_500" / f"{doc}.docx").read_bytes())
        (pf / "documents_pdf" / f"{name}.pdf").write_bytes((g / "fixtures_500_pdf" / render).read_bytes())
    (pf / "word_refused").mkdir(parents=True)
    (pf / "comparisons_docx").mkdir(parents=True)
    (pf / "comparisons_docx" / "g_b_cmp.docx").write_bytes(
        (g / "compared_a_100_vs_b_10_docx" / f"{G}__vs__{B}.docx").read_bytes()
    )
    _pdf(pf / "comparisons_pdf" / "g_b_cmp.pdf", "pdf compare G B filled")
    _mapping(pf / "mapping.csv", [("g_b_cmp", "g_doc", "b_doc")])
    # accepted_tracking_0928: a compare with its changes accepted, and its Word PDF
    at = g / "wr0928" / "accepted_tracking"
    _docx(at / "docx" / "cmp0000001_accepted_tracking.docx", "compare A B accepted")
    _pdf(at / "pdf" / "cmp0000001_accepted_tracking.pdf", "pdf compare A B accepted")
    _put(at / "selection.csv", "key,id\n")
    # rejected_tracking_0928: the same with the changes rejected
    rt = g / "wr0928" / "rejected_tracking"
    _docx(rt / "docx" / "cmp0000002_rejected_tracking.docx", "compare B A rejected")
    _pdf(rt / "pdf" / "cmp0000002_rejected_tracking.pdf", "pdf compare B A rejected")
    _put(rt / "selection.csv", "key,id\n")
    # comment_balloons_0929: synthetic comment A/B documents with their Word PDFs, in two folder
    # pairs, a README, and a Word-invalid variant kept aside
    cb = g / "comment_balloons_0929"
    _docx(cb / "docx" / "R5_00_one_para.docx", "comment balloon one para", comments=True)
    _pdf(cb / "pdf" / "R5_00_one_para.pdf", "pdf comment balloon one para")
    _docx(cb / "ab_docx" / "AB4_0_base_control.docx", "comment balloon ab control", comments=True)
    _pdf(cb / "ab_pdf" / "AB4_0_base_control.pdf", "pdf comment balloon ab control")
    _docx(cb / "word_invalid" / "R3_keep_4_dangling_ref.docx", "comment balloon dangling", comments=True)
    _put(cb / "README.md", "# comment_balloons_0929\n")
    return root


def make_fixtures(root: Path, tree: Path) -> Path:
    """A miniature of jubarte-first/_fixtures: originals with spaces and dots in their names (one of
    them the repo's own x.docx), Word compares of them without a Word PDF, and LibreOffice renders."""
    (root / "original_fixtures").mkdir(parents=True)
    (root / "original_fixtures" / "x.docx").write_bytes((tree / WB / "docx_source" / "x.docx").read_bytes())
    _docx(root / "original_fixtures" / "Sample Document.docx", "docx sample document")
    _docx(root / "original_fixtures" / "1-5-line-spacing.id-paraid-overflow.docx", "docx line spacing")
    _pdf(root / "original_fixtures" / "Sample Document.pdf", "lo render", producer="libreoffice")
    _docx(root / "word_redlined_fixtures" / "x_y_word_redline.docx", "redline x y fixtures", tracked=True)
    _docx(root / "word_redlined_fixtures" / "Sample-Document_x_word_redline.docx", "redline sample x", tracked=True)
    _pdf(root / "word_redlined_fixtures" / "pdf" / "x_y_word_redline.pdf", "lo render", producer="libreoffice")
    return root


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    return make_tree(tmp_path / "repo")


@pytest.fixture
def fixtures(tmp_path: Path, tree: Path) -> Path:
    return make_fixtures(tmp_path / "_fixtures", tree)


def _snapshot(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def _doc(plan_: word_corpus.Plan, name: str) -> word_corpus.Document:
    found = [d for d in plan_.documents if name in d.names]
    assert len(found) == 1, (name, found)
    return found[0]


def _cmp(plan_: word_corpus.Plan, name: str, in_set: str | None = None) -> word_corpus.Comparison:
    found = [c for c in plan_.comparisons if name in c.names and (in_set is None or in_set in c.sets)]
    assert len(found) == 1, (name, found)
    return found[0]


def _id(path: Path) -> str:
    return hub.sha256_file(path)[: word_corpus.ID_LEN]


# --- naming, states and producers ------------------------------------------------


def test_docsets_are_well_formed() -> None:
    names = [ds.name for ds in word_corpus.DOCSETS]
    assert len(names) == len(set(names))
    for ds in word_corpus.DOCSETS:
        assert ds.documents or ds.comparisons, ds.name
        if ds.comparisons:
            assert ds.sources in names, ds.name
            assert ds.mapping or ds.pair_split, ds.name
        if ds.fixtures:
            groups = (ds.documents, ds.comparisons)
            for folder in (f for group in groups if group for f in group.docx):
                assert folder.startswith(word_corpus.FIXTURES_PREFIX), (ds.name, folder)
    def group(name: str, kind: str) -> word_corpus.Group:
        found = getattr(word_corpus.docset(name), kind)
        assert isinstance(found, word_corpus.Group), (name, kind)
        return found

    assert group("sources_500", "documents").require_pdf
    assert not group("word_based", "documents").require_pdf
    assert group("word_based", "comparisons").require_pdf
    assert not group("fixtures_originals", "documents").require_pdf
    with pytest.raises(word_corpus.CorpusError, match="unknown docset"):
        word_corpus.docset("nope")
    assert set(word_corpus.STATES) == {
        "clean",
        "with_comments_tracking",
        "with_comments_clean",
        "tracking_without_comments",
    }


def test_docx_state_and_state_folder(tmp_path: Path) -> None:
    assert word_corpus.docx_state(_docx(tmp_path / "a.docx", "a")) == DocxState(False, False)
    assert word_corpus.docx_state(_docx(tmp_path / "b.docx", "b", tracked=True)) == DocxState(True, False)
    assert word_corpus.docx_state(_docx(tmp_path / "c.docx", "c", comments=True)) == DocxState(False, True)
    assert word_corpus.docx_state(_docx(tmp_path / "d.docx", "d", tracked=True, comments=True)) == DocxState(True, True)
    assert word_corpus.state_name(DocxState(False, False)) == "clean"
    assert word_corpus.state_name(DocxState(True, False)) == "tracking_without_comments"
    assert word_corpus.state_name(DocxState(False, True)) == "with_comments_clean"
    assert word_corpus.state_name(DocxState(True, True)) == "with_comments_tracking"
    # an empty comments part is not a comment
    with zipfile.ZipFile(tmp_path / "e.docx", "w") as zf:
        zf.writestr("word/document.xml", "<w:document/>")
        zf.writestr("word/comments.xml", '<w:comments xmlns:w="w"/>')
    assert word_corpus.docx_state(tmp_path / "e.docx") == DocxState(False, False)
    (tmp_path / "f.docx").write_text("not a zip")
    with pytest.raises(word_corpus.CorpusError, match="not a docx"):
        word_corpus.docx_state(tmp_path / "f.docx")


def test_ids_slugs_and_stems(tmp_path: Path) -> None:
    path = _docx(tmp_path / "a.docx", "a")
    assert word_corpus.file_id(path) == hub.sha256_file(path)[:10]
    assert word_corpus.ID_LEN == 10 and word_corpus.STEM_MAX == 48
    assert word_corpus.slug("Sample Document") == "sample_document"
    assert word_corpus.slug("1-5-line-spacing.id-paraid-overflow") == "1-5-line-spacing_id-paraid-overflow"
    assert word_corpus.slug("Redline_CiceroDo_v_plate(30") == "redline_cicerodo_v_plate_30"
    assert word_corpus.slug("x" * 60) == "x" * 48
    assert word_corpus.slug("_" + "y" * 50) == "y" * 47
    assert word_corpus.document_stem("0123456789", "Sample Document") == "0123456789_sample_document"
    assert (
        word_corpus.comparison_stem("0123456789_a", "abcdef0123_b", "fedcba9876")
        == "0123456789_a__vs__abcdef0123_b_redline_fedcba9876"
    )


def test_pdf_meta_reads_word_and_refuses_other_producers(tmp_path: Path) -> None:
    quartz = word_corpus.pdf_meta(_pdf(tmp_path / "q.pdf", "q"))
    assert quartz.producer == "macOS Version 26.6.2 (Build 25G83) Quartz PDFContext"
    assert quartz.creator == "Word"
    assert word_corpus.is_word_pdf(quartz)
    creator = word_corpus.pdf_meta(_pdf(tmp_path / "c.pdf", "c", producer="creator"))
    assert (creator.producer, creator.creator) == ("", "Microsoft Word")
    assert word_corpus.is_word_pdf(creator)
    lo = word_corpus.pdf_meta(_pdf(tmp_path / "l.pdf", "l", producer="libreoffice"))
    assert lo.producer == "LibreOffice"
    assert not word_corpus.is_word_pdf(lo)
    assert not word_corpus.is_word_pdf(word_corpus.pdf_meta(_pdf(tmp_path / "j.pdf", "j", producer="jubarte 0.4")))
    assert not word_corpus.is_word_pdf(word_corpus.pdf_meta(_pdf(tmp_path / "d.pdf", "d", producer="docxside-pdf")))
    (tmp_path / "n.pdf").write_bytes(b"%PDF-1.4\nno info at all\n")
    none = word_corpus.pdf_meta(tmp_path / "n.pdf")
    assert (none.producer, none.creator) == ("", "") and not word_corpus.is_word_pdf(none)
    # the Info dictionary can sit far from the head: only the tail is read for it
    big = tmp_path / "big.pdf"
    big.write_bytes(b"%PDF-1.4\n" + b"x" * 300_000 + b"<</Creator(Microsoft Word)>>\n%%EOF\n")
    assert word_corpus.is_word_pdf(word_corpus.pdf_meta(big))


def test_pdf_meta_finds_an_info_dictionary_a_long_xref_table_pushed_out_of_the_tail(tmp_path: Path) -> None:
    """A 107-page Quartz render keeps its Info object before a 1195-entry xref table: the
    dictionary sits neither in the head nor in the tail window, and the Word PDF read as
    nobody's. With nothing found in the window the whole file is read."""
    info = b"<</Producer(macOS Version 26.6.2 \\(Build 25G83\\) Quartz PDFContext)>>\n"
    xref = b"xref\n" + b"0000000000 00000 n \n" * 20_000 + b"trailer\n%%EOF\n"
    path = tmp_path / "long_xref.pdf"
    path.write_bytes(b"%PDF-1.3\n" + b"s" * 50_000 + info + xref)
    meta = word_corpus.pdf_meta(path)
    assert meta.producer == "macOS Version 26.6.2 (Build 25G83) Quartz PDFContext"
    assert word_corpus.is_word_pdf(meta)


# --- planning ------------------------------------------------------------------


def test_plan_places_documents_by_state_and_names_them_by_id(tree: Path) -> None:
    plan_ = word_corpus.plan(tree, only=["sources_500"])
    a = _doc(plan_, A)
    assert a.id == _id(tree / "grok_run" / "fixtures_500" / f"{A}.docx")
    assert a.stem == f"{a.id}_{A}"
    assert a.state == "tracking_without_comments"
    assert a.docx == f"tracking_without_comments/docx/{a.stem}.docx"
    assert a.pdf == f"tracking_without_comments/pdf/{a.stem}.pdf"
    assert a.pdf_prior == ""
    assert a.sets == ("sources_500",)
    assert a.producer == "macOS Version 26.6.2 (Build 25G83) Quartz PDFContext"
    assert _doc(plan_, B).state == "with_comments_clean"
    assert _doc(plan_, G).state == "clean"
    assert plan_.sets["sources_500"].documents == (a.id, _doc(plan_, B).id, _doc(plan_, G).id)
    assert "~$lock" not in {n for d in plan_.documents for n in d.names}


def test_plan_tagged_pdfs_keep_the_prior_render(tree: Path) -> None:
    plan_ = word_corpus.plan(tree, only=["sources_500"])
    b = _doc(plan_, B)
    assert b.pdf_src == f"grok_run/fixtures_500_pdf/{B}.w26092233.pdf"
    assert b.pdf_prior_src == f"grok_run/fixtures_500_pdf/{B}.outdated.pdf"
    assert b.pdf_prior == f"with_comments_clean/pdf_prior/{b.stem}.pdf"
    assert plan_.sets["sources_500"].superseded == (B,)
    assert plan_.sets["sources_500"].orphans == ("grok_run/fixtures_500_pdf/orphan.pdf",)


def test_plan_require_pdf_leaves_out_what_word_did_not_render(tree: Path) -> None:
    plan_ = word_corpus.plan(tree, only=["sources_500", "redlines_a100_b10"])
    assert C not in {n for d in plan_.documents for n in d.names}
    assert plan_.sets["sources_500"].absent == (C,)
    report = plan_.sets["redlines_a100_b10"]
    assert report.absent == (f"{G}__vs__{B}",)
    assert report.unresolved == {f"{A}__vs__{C}": f"next {C} is not a document of sources_500"}
    assert [c.names for c in plan_.comparisons] == [(f"{A}__vs__{B}",)]


def test_plan_fallback_fills_gaps_only(tree: Path) -> None:
    plan_ = word_corpus.plan(tree, only=["en_pairs_500"])
    f, h = _doc(plan_, F), _doc(plan_, H)
    assert f.pdf_src == f"grok_run/500_pdf_part_b_original/{F}.pdf" and f.pdf_prior == ""
    assert h.pdf_src == f"grok_run/500_pdf_part_b_run2/{H}.pdf"
    assert plan_.sets["en_pairs_500"].filled == (H,)


def test_plan_applies_exclusion_folders_and_the_blacklist(tree: Path) -> None:
    plan_ = word_corpus.plan(tree, only=["en_pairs_500", "redlines_en_500"])
    names = {n for d in plan_.documents for n in d.names}
    assert E not in names and H in names
    assert plan_.sets["en_pairs_500"].excluded == {"500_docx_part_a_word_invalid": (E,)}
    report = plan_.sets["redlines_en_500"]
    assert report.excluded == {
        "word_blacklist": (f"{D}__vs__{H}", f"{F}__vs__{H}"),
        "500_extra_redlines_rejected": (f"{D}__vs__{H}",),
    }
    assert [c.names for c in plan_.comparisons] == [(f"{D}__vs__{F}",)]


def test_plan_word_invalid_list_removes_documents_and_their_compares_from_every_set(tree: Path) -> None:
    """A docx Word will not open cleanly is out of the corpus by its id, whatever it is called in a
    set, and every compare built on it goes with it."""
    x_id = _id(tree / WB / "docx_source" / "x.docx")
    ab_id = _id(tree / "grok_run" / "compared_a_100_vs_b_10_docx" / f"{A}__vs__{B}.docx")
    _put(tree / word_corpus.WORD_INVALID, f"{x_id}\trecover-contents prompt\n{ab_id}\trepair prompt\n")
    plan_ = word_corpus.plan(tree, only=["sources_500", "redlines_a100_b10", "word_based", "nocomments"])
    assert "x" not in {n for d in plan_.documents for n in d.names}
    assert {c.id for c in plan_.comparisons}.isdisjoint({ab_id})
    assert not [c for c in plan_.comparisons if "x_y_redline" in c.names]
    label = word_corpus.WORD_INVALID_LABEL
    assert plan_.sets["word_based"].excluded == {label: ("x", "x_y_redline")}
    assert plan_.sets["nocomments"].excluded == {label: ("x", "x_y_redline")}
    assert plan_.sets["redlines_a100_b10"].excluded == {label: (f"{A}__vs__{B}",)}
    assert _doc(plan_, "y").id  # the other side of the pair stays
    assert word_corpus.WORD_INVALID in word_corpus.origins()


def test_plan_without_a_blacklist_excludes_nothing(tree: Path) -> None:
    (tree / "grok_run" / "word_blacklist" / "blacklist.tsv").unlink()
    plan_ = word_corpus.plan(tree, only=["en_pairs_500", "redlines_en_500"])
    assert plan_.sets["redlines_en_500"].excluded == {"500_extra_redlines_rejected": (f"{D}__vs__{H}",)}


def test_plan_comparisons_carry_base_next_and_the_redline_id(tree: Path) -> None:
    plan_ = word_corpus.plan(tree, only=["sources_500", "redlines_a100_b10", "word_based"])
    ab = _cmp(plan_, f"{A}__vs__{B}")
    a, b = _doc(plan_, A), _doc(plan_, B)
    assert (ab.base_id, ab.next_id) == (a.id, b.id)
    assert ab.id == _id(tree / "grok_run" / "compared_a_100_vs_b_10_docx" / f"{A}__vs__{B}.docx")
    assert ab.stem == f"{a.stem}__vs__{b.stem}_redline_{ab.id}"
    assert ab.state == "tracking_without_comments"
    assert ab.docx == f"tracking_without_comments/docx/{ab.stem}.docx"
    assert ab.pdf == f"tracking_without_comments/pdf/{ab.stem}.pdf"
    # mapping-based names: `x_y_redline` and `y_z_word_redline` both resolve through pair_stem
    xy = _cmp(plan_, "x_y_redline")
    x, y, z = _doc(plan_, "x"), _doc(plan_, "y"), _doc(plan_, "z")
    assert (xy.base_id, xy.next_id, xy.state) == (x.id, y.id, "with_comments_tracking")
    assert xy.pdf_src == "grok_run/wordpdf_redline_oracles/word_based/x_y_redline.pdf"
    yz = _cmp(plan_, "y_z_word_redline")
    assert (yz.base_id, yz.next_id) == (y.id, z.id)
    assert x.pdf == "" and x.docx == f"clean/docx/{x.stem}.docx"
    assert plan_.sets["word_based"].comparisons == (xy.id, yz.id)


def test_plan_resolves_mapping_keys_that_keep_double_underscores(tree: Path) -> None:
    # the superdoc mapping keeps `__` in its pair_stem column, a compare name folds it to `_`
    sd = tree / SD
    # and mixed case; a key whose next document is itself named `..._redline` keeps that tail
    for name in ("s__p_1", "s__q_2", "Big_R", "y_redline"):
        _docx(sd / "docx_source" / f"{name}.docx", f"docx {name}")
    pairs = [("p_q", "p", "q"), ("s__p_1_s__q_2", "s__p_1", "s__q_2"), ("Big_R_y_redline", "Big_R", "y_redline")]
    _mapping(sd / "centralized_mapping.csv", pairs)
    oracles = tree / "grok_run" / "wordpdf_redline_oracles" / "word_redlines_superdoc"
    for cmp_name in ("s__p_1_s__q_2_redline", "Big_R_y_redline_redline"):
        _docx(sd / "docx_redlines_word" / f"{cmp_name}.docx", f"redline {cmp_name}", tracked=True)
        _pdf(oracles / f"{cmp_name}.pdf", f"pdf {cmp_name}")
    plan_ = word_corpus.plan(tree, only=["word_redlines_superdoc"])
    assert plan_.sets["word_redlines_superdoc"].unresolved == {}
    pq = _cmp(plan_, "s__p_1_s__q_2_redline")
    assert (pq.base_id, pq.next_id) == (_doc(plan_, "s__p_1").id, _doc(plan_, "s__q_2").id)
    ry = _cmp(plan_, "Big_R_y_redline_redline")
    assert (ry.base_id, ry.next_id) == (_doc(plan_, "Big_R").id, _doc(plan_, "y_redline").id)


def test_plan_wr0926_sets_are_new_documents_of_the_same_pairs(tree: Path) -> None:
    plan_ = word_corpus.plan(tree, only=["word_based", "word_based_0926"])
    old = _cmp(plan_, "x_y_redline", in_set="word_based")
    assert old.sets == ("word_based",)  # the two x_y_redline names are different bytes
    new = [c for c in plan_.comparisons if "word_based_0926" in c.sets]
    assert len(new) == 1
    xy = new[0]
    assert xy.names == ("x_y_redline",) and xy.sets == ("word_based_0926",)
    assert xy.id != old.id and (xy.base_id, xy.next_id) == (old.base_id, old.next_id)
    assert xy.pdf_src == "grok_run/wr0926/word_based/pdf/x_y_redline.pdf"
    assert plan_.sets["word_based_0926"].absent == ("y_z_redline",)  # Word did not render it


def test_plan_dedupes_identical_docx_across_sets_and_records_every_name(tree: Path, fixtures: Path) -> None:
    plan_ = word_corpus.plan(tree, fixtures=fixtures)
    x = _doc(plan_, "x")
    assert x.sets == ("word_based", "nocomments", "fixtures_originals")
    assert x.names == ("x",)
    assert x.pdf_src == f"{NC}/pdf_source/x.pdf"  # the only Word render of x
    sample = _doc(plan_, "Sample Document")
    assert sample.stem == f"{sample.id}_sample_document" and sample.pdf == ""
    assert sample.sets == ("fixtures_originals",)
    spacing = _doc(plan_, "1-5-line-spacing.id-paraid-overflow")
    assert spacing.stem == f"{spacing.id}_1-5-line-spacing_id-paraid-overflow"
    assert plan_.sets["fixtures_originals"].documents == (spacing.id, sample.id, x.id)
    assert plan_.sets["fixtures_originals"].refused == {}  # the LibreOffice PDF is not an origin of that set
    # a compare of names the mapping does not know is recorded, not guessed
    assert plan_.sets["fixtures_word_compares"].unresolved == {
        "Sample-Document_x_word_redline": "pair sample_document_x is not in grok_run/word_based/centralized_mapping.csv"
    }
    xy = _cmp(plan_, "x_y_word_redline")
    assert xy.sets == ("fixtures_word_compares",) and xy.pdf == ""
    renamed = {r.original: r for r in plan_.renames}
    assert renamed[f"{FIX}/original_fixtures/Sample Document.docx"].new == sample.docx
    assert renamed[f"{NC}/docx_source/x.docx"].new == x.docx and renamed[f"{NC}/docx_source/x.docx"].id == x.id



def test_plan_without_a_fixtures_root_skips_the_fixtures_sets(tree: Path) -> None:
    plan_ = word_corpus.plan(tree)
    assert "fixtures_originals" not in plan_.sets and "fixtures_word_compares" not in plan_.sets
    assert plan_.skipped == ("fixtures_originals", "fixtures_word_compares")
    with pytest.raises(word_corpus.CorpusError, match="fixtures root"):
        word_corpus.plan(tree, only=["fixtures_originals"])


def test_plan_refuses_an_id_collision(tree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(word_corpus, "ID_LEN", 0)
    with pytest.raises(word_corpus.CorpusError, match="collision"):
        word_corpus.plan(tree, only=["sources_500"])


def test_plan_refuses_a_second_prior_render(tree: Path) -> None:
    # B (already current + outdated in sources_500) reappears in en_pairs_500 with a third render
    (tree / "grok_run" / "500_docx_part_a_original" / f"{B}.docx").write_bytes(
        (tree / "grok_run" / "fixtures_500" / f"{B}.docx").read_bytes()
    )
    _pdf(tree / "grok_run" / "500_pdf_part_a_original" / f"{B}.pdf", f"pdf {B} third")
    with pytest.raises(word_corpus.CorpusError, match="second prior"):
        word_corpus.plan(tree, only=["sources_500", "en_pairs_500"])


def test_plan_keeps_one_pdf_when_two_sets_carry_the_same_render(tree: Path) -> None:
    (tree / "grok_run" / "500_docx_part_a_original" / f"{A}.docx").write_bytes(
        (tree / "grok_run" / "fixtures_500" / f"{A}.docx").read_bytes()
    )
    (tree / "grok_run" / "500_pdf_part_a_original" / f"{A}.pdf").write_bytes(
        (tree / "grok_run" / "fixtures_500_pdf" / f"{A}.pdf").read_bytes()
    )
    plan_ = word_corpus.plan(tree, only=["sources_500", "en_pairs_500"])
    a = _doc(plan_, A)
    assert a.sets == ("sources_500", "en_pairs_500") and a.pdf_prior == ""


def test_plan_prior_render_from_a_later_set(tree: Path) -> None:
    (tree / "grok_run" / "500_docx_part_a_original" / f"{A}.docx").write_bytes(
        (tree / "grok_run" / "fixtures_500" / f"{A}.docx").read_bytes()
    )
    _pdf(tree / "grok_run" / "500_pdf_part_a_original" / f"{A}.pdf", f"pdf {A} other run")
    plan_ = word_corpus.plan(tree, only=["sources_500", "en_pairs_500"])
    a = _doc(plan_, A)
    assert a.pdf_src == f"grok_run/fixtures_500_pdf/{A}.pdf"
    assert a.pdf_prior_src == f"grok_run/500_pdf_part_a_original/{A}.pdf"
    assert plan_.sets["en_pairs_500"].superseded == (A,)


def test_plan_refuses_pdfs_word_did_not_produce(tree: Path) -> None:
    _pdf(tree / NC / "pdf_source" / "x.pdf", "lo render of x", producer="libreoffice")
    _pdf(tree / NC / "pdf_redlines_word" / "x_y_redline.pdf", "tool render", producer="jubarte 0.4")
    plan_ = word_corpus.plan(tree, only=["word_based", "nocomments"])
    assert _doc(plan_, "x").pdf == ""
    assert plan_.sets["nocomments"].refused == {
        f"{NC}/pdf_source/x.pdf": "LibreOffice",
        f"{NC}/pdf_redlines_word/x_y_redline.pdf": "jubarte 0.4",
    }
    assert plan_.sets["nocomments"].absent == ("x", "z", "x_y_redline")


def test_plan_refuses_a_missing_origin(tree: Path) -> None:
    (tree / "grok_run" / "fixtures_500_pdf" / f"{A}.pdf").unlink()
    for p in (tree / "grok_run" / "fixtures_500_pdf").iterdir():
        p.unlink()
    (tree / "grok_run" / "fixtures_500_pdf").rmdir()
    with pytest.raises(word_corpus.CorpusError, match="missing origin"):
        word_corpus.plan(tree, only=["sources_500"])


def test_plan_refuses_a_tagged_name_it_cannot_place(tree: Path) -> None:
    _pdf(tree / "grok_run" / "fixtures_500_pdf" / f"{A}.weird.pdf", "?")
    with pytest.raises(word_corpus.CorpusError, match="unexpected name"):
        word_corpus.plan(tree, only=["sources_500"])
    (tree / "grok_run" / "fixtures_500_pdf" / f"{A}.weird.pdf").unlink()
    _pdf(tree / "grok_run" / "fixtures_500_pdf" / f"{A}.w1.pdf", "?")
    with pytest.raises(word_corpus.CorpusError, match="two current"):
        word_corpus.plan(tree, only=["sources_500"])


def test_copy_file_clones_on_apfs_and_copies_elsewhere(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    src = _put(tmp_path / "src.txt", "bytes")
    monkeypatch.setattr(word_corpus, "_clone_enabled", lambda: False)
    word_corpus.copy_file(src, tmp_path / "a" / "dst.txt")
    assert (tmp_path / "a" / "dst.txt").read_text() == "bytes"
    monkeypatch.setattr(word_corpus, "_clone_enabled", lambda: True)
    monkeypatch.setattr(word_corpus, "CLONE_COMMAND", ("false",))  # the clone fails: fall back to a copy
    word_corpus.copy_file(src, tmp_path / "b" / "dst.txt")
    assert (tmp_path / "b" / "dst.txt").read_text() == "bytes"
    monkeypatch.setattr(word_corpus, "CLONE_COMMAND", ("cp",))
    word_corpus.copy_file(src, tmp_path / "c" / "dst.txt")
    assert (tmp_path / "c" / "dst.txt").read_text() == "bytes"


# --- building ------------------------------------------------------------------


def test_build_copies_and_leaves_the_origins_alone(tree: Path, fixtures: Path) -> None:
    before = _snapshot(tree) | {f"{FIX}/{k}": v for k, v in _snapshot(fixtures).items()}
    dest = tree / "corpus" / "word"
    report = word_corpus.build(tree, dest, fixtures=fixtures)
    after = _snapshot(tree) | {f"{FIX}/{k}": v for k, v in _snapshot(fixtures).items()}
    assert {k: v for k, v in after.items() if not k.startswith("corpus/word/")} == before
    plan_ = word_corpus.plan(tree, fixtures=fixtures)
    for entry in (*plan_.documents, *plan_.comparisons):
        if not entry.docx_src.startswith(FIX):
            assert (dest / entry.docx).read_bytes() == (tree / entry.docx_src).read_bytes()
        if entry.pdf:
            assert (dest / entry.pdf).exists()
        if entry.pdf_prior:
            assert (dest / entry.pdf_prior).exists()
    a = _doc(plan_, A)
    assert (dest / a.docx).read_bytes() == (tree / "grok_run" / "fixtures_500" / f"{A}.docx").read_bytes()
    sample = _doc(plan_, "Sample Document")
    assert (dest / sample.docx).read_bytes() == (fixtures / "original_fixtures" / "Sample Document.docx").read_bytes()
    assert report.copied == len(plan_.documents) + len(plan_.comparisons) + sum(
        bool(e.pdf) + bool(e.pdf_prior) for e in (*plan_.documents, *plan_.comparisons)
    ) + len(plan_.notes)
    assert report.skipped == 0 and report.overwritten == 0
    assert "copied" in report.describe()
    expected = {*word_corpus.STATES, "notices", "pools", "documents.csv", "comparisons.csv"}
    assert {p.name for p in dest.iterdir()} >= expected
    assert {p.name for p in (dest / "clean").iterdir()} == {"docx", "pdf"}
    assert {p.name for p in (dest / "with_comments_clean").iterdir()} == {"docx", "pdf", "pdf_prior"}


def test_build_writes_tables_notices_pools_and_provenance(tree: Path, fixtures: Path) -> None:
    dest = tree / "corpus" / "word"
    word_corpus.build(tree, dest, fixtures=fixtures)
    plan_ = word_corpus.plan(tree, fixtures=fixtures)
    docs = {r["id"]: r for r in _rows(dest / "documents.csv")}
    assert list(docs) == [d.id for d in plan_.documents]
    x = _doc(plan_, "x")
    assert docs[x.id] == {
        "id": x.id,
        "stem": x.stem,
        "state": "clean",
        "docx": x.docx,
        "pdf": x.pdf,
        "pdf_prior": "",
        "sets": "word_based;nocomments;fixtures_originals",
        "names": "x",
        "sha256": hub.sha256_file(tree / WB / "docx_source" / "x.docx"),
        "producer": "macOS Version 26.6.2 (Build 25G83) Quartz PDFContext",
    }
    cmps = {r["id"]: r for r in _rows(dest / "comparisons.csv")}
    ab = _cmp(plan_, f"{A}__vs__{B}")
    xy = _cmp(plan_, "x_y_redline", in_set="word_based")
    assert cmps[ab.id] == {
        "id": ab.id,
        "key": ab.stem,
        "base_id": ab.base_id,
        "next_id": ab.next_id,
        "state": "tracking_without_comments",
        "docx": ab.docx,
        "pdf": ab.pdf,
        "pdf_prior": "",
        "sets": "redlines_a100_b10",
        "names": f"{A}__vs__{B}",
        "sha256": hub.sha256_file(tree / "grok_run" / "compared_a_100_vs_b_10_docx" / f"{A}__vs__{B}.docx"),
        "producer": "macOS Version 26.6.2 (Build 25G83) Quartz PDFContext",
    }
    # notices: the origins' own files, the license and the rename record
    notices = {p.name for p in (dest / "notices").iterdir()}
    assert notices >= {
        "LICENSE-ODC-BY-1.0.txt",
        "NOTICE",
        "MANIFEST.json",
        "manifest.jsonl",
        "split_a_100_b_10.json",
        "EXTRA_REFERENCES.md",
        "NOTE",
        "blacklist.tsv",
        "500_en_pairs.tsv",
        "500_en_sources.jsonl",
        "wr0926_word_based_map.tsv",
        "wr0926_word_based_identity.log",
        "RENAMED.csv",
        "README.md",
    }
    renamed = {r["original"]: r for r in _rows(dest / "notices" / "RENAMED.csv")}
    assert list(renamed[f"grok_run/fixtures_500/{A}.docx"]) == ["original", "new", "id", "sha256", "set"]
    assert renamed[f"grok_run/fixtures_500/{A}.docx"]["new"] == _doc(plan_, A).docx
    assert renamed[f"grok_run/fixtures_500_pdf/{B}.outdated.pdf"]["new"] == _doc(plan_, B).pdf_prior
    assert renamed[f"{FIX}/original_fixtures/Sample Document.docx"]["set"] == "fixtures_originals"
    # pools: base and next as corpus stems the generators can open under --source-dir corpus/word
    pairs = _rows(dest / "pools" / "redlines_a100_b10_pairs.csv")
    a, b = _doc(plan_, A), _doc(plan_, B)
    assert pairs == [
        {
            "key": ab.stem,
            "base": a.docx.removesuffix(".docx"),
            "next": b.docx.removesuffix(".docx"),
            "base_name": A,
            "next_name": B,
            "docx": ab.docx,
            "pdf": ab.pdf,
            "state": "tracking_without_comments",
        }
    ]
    renders = _rows(dest / "pools" / "sources_500_renders.csv")
    assert [r["key"] for r in renders] == [a.stem, b.stem, _doc(plan_, G).stem]
    assert renders[0] == {"key": a.stem, "kind": "document", "docx": a.docx, "pdf": a.pdf, "state": a.state}
    assert not (dest / "pools" / "sources_500_pairs.csv").exists()
    assert not (dest / "pools" / "fixtures_originals_renders.csv").exists()  # nothing there has a Word PDF
    wb = _rows(dest / "pools" / "word_based_pairs.csv")
    assert [r["key"] for r in wb] == [xy.stem, _cmp(plan_, "y_z_word_redline").stem]
    assert wb[0]["base"] == x.docx.removesuffix(".docx") and wb[0]["base_name"] == "x"
    # provenance and manifest
    prov = json.loads((dest / "PROVENANCE.json").read_text())
    assert prov["id_scheme"] == "sha256[:10] of the docx bytes"
    assert prov["license"] == "ODC-By-1.0" and prov["dataset"] == "superdoc-dev/docx-corpus"
    assert set(prov["sets"]) == set(plan_.sets)
    s500 = prov["sets"]["sources_500"]
    assert s500["absent"] == [C] and s500["superseded"] == [B] and s500["n_documents"] == 3
    assert s500["docset_id"] == word_corpus.docset_id_for(plan_, "sources_500")
    assert prov["counts"] == {
        "documents": len(plan_.documents),
        "comparisons": len(plan_.comparisons),
        "pdf": sum(bool(e.pdf) for e in (*plan_.documents, *plan_.comparisons)),
        "pdf_prior": sum(bool(e.pdf_prior) for e in (*plan_.documents, *plan_.comparisons)),
    }
    assert prov["skipped"] == []
    manifest = json.loads((dest / hub.MANIFEST_NAME).read_text())
    assert {x.docx, "documents.csv", "PROVENANCE.json"} <= set(manifest["files"])
    assert "The Word corpus" in (dest / "README.md").read_text()


def test_build_is_idempotent_and_refuses_to_overwrite_a_changed_file(tree: Path) -> None:
    dest = tree / "corpus" / "word"
    first = word_corpus.build(tree, dest)
    again = word_corpus.build(tree, dest)
    assert again.copied == 0 and again.skipped == first.copied and again.overwritten == 0
    plan_ = word_corpus.plan(tree)
    a = _doc(plan_, A)
    (dest / a.pdf).write_text("edited by hand")
    with pytest.raises(word_corpus.CorpusError, match="differs"):
        word_corpus.build(tree, dest)
    forced = word_corpus.build(tree, dest, force=True)
    assert forced.overwritten == 1
    assert (dest / a.pdf).read_bytes() == (tree / "grok_run" / "fixtures_500_pdf" / f"{A}.pdf").read_bytes()


def test_build_only_and_dry_run(tree: Path) -> None:
    dest = tree / "corpus" / "word"
    report = word_corpus.build(tree, dest, only=["sources_500"], dry_run=True)
    assert report.sets == ("sources_500",) and report.copied == 3 + 3 + 1 + 6 and not dest.exists()
    report = word_corpus.build(tree, dest, only=["sources_500"])
    assert set(json.loads((dest / "PROVENANCE.json").read_text())["sets"]) == {"sources_500"}
    assert not (dest / "comparisons.csv").exists() or _rows(dest / "comparisons.csv") == []
    with pytest.raises(word_corpus.CorpusError, match="unknown docset"):
        word_corpus.build(tree, dest, only=["nope"])
    with pytest.raises(word_corpus.CorpusError, match="sources_500"):
        word_corpus.build(tree, dest, only=["redlines_a100_b10"])  # a comparison set needs its sources


def test_check_reports_drift(tree: Path) -> None:
    dest = tree / "corpus" / "word"
    with pytest.raises(word_corpus.CorpusError, match="no MANIFEST"):
        word_corpus.check(dest)
    word_corpus.build(tree, dest)
    assert word_corpus.check(dest).ok
    a = _doc(word_corpus.plan(tree), A)
    (dest / a.pdf).write_text("drifted")
    assert not word_corpus.check(dest).ok


def test_plan_pdf_fill_gives_documents_and_compares_the_word_pdf_they_lacked(tree: Path) -> None:
    plan = word_corpus.plan(tree)
    z = _doc(plan, "z")
    assert z.pdf_src == "grok_run/wr0928/pdf_fill/documents_pdf/z_doc.pdf"
    assert z.stem.endswith("_z") and "z_doc" in z.names and "pdf_fill_0928" in z.sets
    gdoc, bdoc = _doc(plan, G), _doc(plan, B)
    assert gdoc.pdf_src == f"grok_run/fixtures_500_pdf/{G}.pdf"
    assert bdoc.pdf_src == f"grok_run/fixtures_500_pdf/{B}.w26092233.pdf"
    assert not gdoc.pdf_prior_src and plan.sets["pdf_fill_0928"].superseded == ()
    (gb,) = [e for e in plan.comparisons if e.pdf_src.endswith("g_b_cmp.pdf")]
    assert (gb.base_id, gb.next_id) == (gdoc.id, bdoc.id)
    assert gb.stem.startswith(f"{gdoc.stem}__vs__{bdoc.stem}")
    (accepted,) = [d for d in plan.documents if "accepted_tracking_0928" in d.sets]
    assert accepted.stem.endswith("_cmp0000001_accepted_tracking") and accepted.pdf_src
    (rejected,) = [d for d in plan.documents if "rejected_tracking_0928" in d.sets]
    assert rejected.stem.endswith("_cmp0000002_rejected_tracking") and rejected.pdf_src
    balloons = {d.stem.split("_", 1)[1]: d for d in plan.documents if "comment_balloons_0929" in d.sets}
    assert set(balloons) == {"r5_00_one_para", "ab4_0_base_control"}
    assert balloons["r5_00_one_para"].pdf_src == "grok_run/comment_balloons_0929/pdf/R5_00_one_para.pdf"
    assert balloons["ab4_0_base_control"].pdf_src == "grok_run/comment_balloons_0929/ab_pdf/AB4_0_base_control.pdf"
    assert balloons["r5_00_one_para"].state == "with_comments_clean"


def test_summary_and_corpus_entries(tree: Path) -> None:
    dest = tree / "corpus" / "word"
    assert word_corpus.summary(dest) == []
    word_corpus.build(tree, dest)
    rows = {r["name"]: r for r in word_corpus.summary(dest)}
    assert rows["sources_500"]["documents"] == 3 and rows["sources_500"]["comparisons"] == 0
    assert rows["sources_500"]["absent"] == 1 and rows["sources_500"]["superseded"] == 1
    assert rows["redlines_a100_b10"]["comparisons"] == 1 and rows["redlines_a100_b10"]["unresolved"] == 1
    assert rows["redlines_en_500"]["excluded"] == 3
    assert rows["nocomments"]["refused"] == 0
    entries = {e.name: e for e in word_corpus.corpus_entries(dest)}
    assert set(entries) == {
        "word_redlines_a100_b10",
        "word_redlines_en_500",
        "word_word_based",
        "word_word_based_randomized",
        "word_word_redlines_superdoc",
        "word_word_based_0926",
        "word_word_based_randomized_0926",
        "word_word_redlines_superdoc_0926",
        "word_nocomments",
        "word_nocomments_randomized",
        "word_pdf_fill_0928",
    }
    e = entries["word_redlines_a100_b10"]
    assert e.manifest == (dest / "pools" / "redlines_a100_b10_pairs.csv").as_posix()
    assert e.source_dir == dest.as_posix()


def test_cli_build_check_list(tree: Path, fixtures: Path) -> None:
    runner = CliRunner()
    dest = tree / "corpus" / "word"
    res = runner.invoke(app, ["corpus", "build", "--root", str(tree), "--dest", str(dest), "--fixtures", str(fixtures)])
    assert res.exit_code == 0, res.output
    assert "copied" in res.output and "left out" in res.output and "fixtures_originals" in res.output
    res = runner.invoke(app, ["corpus", "check", "--dest", str(dest)])
    assert res.exit_code == 0, res.output
    res = runner.invoke(app, ["corpus", "list", "--dest", str(dest)])
    assert res.exit_code == 0, res.output
    assert "redlines_en_500" in res.output and "word_based_0926" in res.output
    a = _doc(word_corpus.plan(tree), A)
    (dest / a.pdf).write_text("drifted")
    res = runner.invoke(app, ["corpus", "check", "--dest", str(dest)])
    assert res.exit_code == 1
    res = runner.invoke(app, ["corpus", "build", "--root", str(tree), "--dest", str(dest)])
    assert res.exit_code == 1 and "differs" in res.output
    res = runner.invoke(app, ["corpus", "build", "--root", str(tree / "nowhere"), "--dest", str(dest)])
    assert res.exit_code == 1
    res = runner.invoke(app, ["corpus", "list", "--dest", str(tree / "nowhere")])
    assert res.exit_code == 1


# --- the less-trodden paths -------------------------------------------------------


def test_origins_lists_every_origin_once() -> None:
    origins = word_corpus.origins()
    assert len(origins) == len(set(origins)) and "" not in origins
    assert "grok_run/fixtures_500" in origins
    assert "grok_run/500_pdf_part_a_run2" in origins  # a fallback folder is an origin too
    assert f"{WB}/centralized_mapping.csv" in origins
    assert "grok_run/word_blacklist/blacklist.tsv" in origins
    assert "grok_run/fixtures_500/NOTICE" in origins
    assert f"{FIX}/original_fixtures" in origins


def test_pdf_meta_reads_a_hex_string_without_a_byte_order_mark(tmp_path: Path) -> None:
    path = tmp_path / "h.pdf"
    path.write_bytes(b"%PDF-1.4\n2 0 obj<</Producer<4A75 6261 727465>/Creator<FEFF0057006F00720064>>>endobj\n%%EOF\n")
    meta = word_corpus.pdf_meta(path)
    assert (meta.producer, meta.creator) == ("Jubarte", "Word")
    assert not word_corpus.is_word_pdf(meta)


def test_plan_refuses_a_missing_mapping(tree: Path) -> None:
    (tree / WB / "centralized_mapping.csv").unlink()
    with pytest.raises(word_corpus.CorpusError, match="missing mapping"):
        word_corpus.plan(tree, only=["word_based"])


def test_plan_reports_a_compare_whose_name_is_not_a_pair(tree: Path) -> None:
    g = tree / "grok_run"
    _docx(g / "compared_a_100_vs_b_10_docx" / "nopair.docx", "compare of nothing", tracked=True)
    _pdf(g / "compared_a_100_vs_b_10_pdf" / "nopair.pdf", "pdf compare of nothing")
    _docx(g / "compared_a_100_vs_b_10_docx" / f"__vs__{B}.docx", "compare with no base", tracked=True)
    _pdf(g / "compared_a_100_vs_b_10_pdf" / f"__vs__{B}.pdf", "pdf compare with no base")
    plan_ = word_corpus.plan(tree, only=["sources_500", "redlines_a100_b10"])
    report = plan_.sets["redlines_a100_b10"]
    assert report.unresolved["nopair"] == "not a <base>__vs__<next> name"
    assert report.unresolved[f"__vs__{B}"] == "not a <base>__vs__<next> name"
    assert report.comparisons == (_cmp(plan_, f"{A}__vs__{B}").id,)


def test_plan_refuses_the_same_bytes_as_a_document_and_a_comparison(tree: Path) -> None:
    (tree / WB / "docx_redlines_word" / "x_y_redline.docx").write_bytes(
        (tree / WB / "docx_source" / "x.docx").read_bytes()
    )
    with pytest.raises(word_corpus.CorpusError, match="same bytes but not the same kind"):
        word_corpus.plan(tree, only=["word_based"])


def test_plan_refuses_a_prior_render_word_did_not_produce(tree: Path) -> None:
    _pdf(tree / "grok_run" / "fixtures_500_pdf" / f"{B}.outdated.pdf", f"lo render of {B}", producer="libreoffice")
    plan_ = word_corpus.plan(tree, only=["sources_500"])
    b = _doc(plan_, B)
    assert b.pdf_src == f"grok_run/fixtures_500_pdf/{B}.w26092233.pdf" and b.pdf_prior == ""
    report = plan_.sets["sources_500"]
    assert report.refused == {f"grok_run/fixtures_500_pdf/{B}.outdated.pdf": "LibreOffice"}
    assert report.superseded == () and b.id in report.documents


def test_plan_notes_sharing_a_destination(tree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from dataclasses import replace

    def with_note(origin: str, dest: str) -> None:
        sets = tuple(
            replace(ds, notes=(word_corpus.Note(origin, dest),)) if ds.name == "redlines_a100_b10" else ds
            for ds in word_corpus.DOCSETS
        )
        monkeypatch.setattr(word_corpus, "DOCSETS", sets)

    # two origins, one destination, other bytes: refused
    with_note("grok_run/compared_a_100_vs_b_10_pdf/NOTE", "NOTICE")
    with pytest.raises(word_corpus.CorpusError, match="two notes want notices/NOTICE"):
        word_corpus.plan(tree, only=["sources_500", "redlines_a100_b10"])
    # the same bytes under another origin: the first origin is kept, nothing is refused
    _put(tree / "grok_run" / "compared_a_100_vs_b_10_pdf" / "NOTICE-copy", "notice")
    with_note("grok_run/compared_a_100_vs_b_10_pdf/NOTICE-copy", "NOTICE")
    plan_ = word_corpus.plan(tree, only=["sources_500", "redlines_a100_b10"])
    notices = [n for n in plan_.notes if n.dst == "notices/NOTICE"]
    assert [n.src for n in notices] == ["grok_run/fixtures_500/NOTICE"]


def test_build_removes_stale_pools(tree: Path, fixtures: Path) -> None:
    dest = tree / "corpus" / "word"
    word_corpus.build(tree, dest, fixtures=fixtures)
    pools = dest / word_corpus.POOLS_DIR
    assert not (pools / "sources_500_pairs.csv").exists()  # a documents-only set has no pairs
    assert not (pools / "fixtures_originals_renders.csv").exists()  # nothing of it was rendered
    stale = [_put(pools / name, "stale\n") for name in ("sources_500_pairs.csv", "fixtures_originals_renders.csv")]
    assert not word_corpus.check(dest).ok
    word_corpus.build(tree, dest, fixtures=fixtures)
    assert not any(p.exists() for p in stale)
    assert word_corpus.check(dest).ok


def test_planner_resolves_and_caches(tree: Path) -> None:
    planner = word_corpus._Planner(tree, None)
    assert planner.resolve(f"{WB}/docx_source/x.docx") == tree / WB / "docx_source" / "x.docx"
    with pytest.raises(word_corpus.CorpusError, match="needs a fixtures root"):
        planner.resolve(f"{FIX}/original_fixtures")
    rel = f"{WB}/docx_source/x.docx"
    assert planner.sha(rel) == planner.sha(rel) == hub.sha256_file(tree / WB / "docx_source" / "x.docx")
    with_root = word_corpus._Planner(tree, tree / "fx")
    assert with_root.resolve(f"{FIX}/original_fixtures") == tree / "fx" / "original_fixtures"
    assert word_corpus.pair_stem("x_y") == "x_y"  # no redline suffix to drop


def test_plan_records_every_name_of_the_same_bytes(tree: Path) -> None:
    (tree / WB / "docx_source" / "x_copy.docx").write_bytes((tree / WB / "docx_source" / "x.docx").read_bytes())
    plan_ = word_corpus.plan(tree, only=["word_based"])
    x = _doc(plan_, "x")
    assert x.names == ("x", "x_copy") and x.sets == ("word_based",)
    assert [d for d in plan_.documents if "x_copy" in d.names] == [x]
    assert plan_.sets["word_based"].documents.count(x.id) == 1


def test_plan_a_third_render_of_the_same_bytes_in_an_untagged_set_is_redundant(tree: Path) -> None:
    """nocomments holds strict01 under four names, each rendered by Word on its own: the first
    render is current, the next prior, the rest redundant (reported, not copied). Only a tagged
    set, whose names say which render is which, still refuses a second prior."""
    same = (tree / WB / "docx_source" / "x.docx").read_bytes()
    for name in ("x_again", "x_third"):
        (tree / NC / "docx_source" / f"{name}.docx").write_bytes(same)
        _pdf(tree / NC / "pdf_source" / f"{name}.pdf", f"pdf {name} july")
    plan = word_corpus.plan(tree)
    x = _doc(plan, "x")
    assert x.pdf_src == f"{NC}/pdf_source/x.pdf"
    assert x.pdf_prior_src == f"{NC}/pdf_source/x_again.pdf"
    report = plan.sets["nocomments"]
    assert report.superseded == ("x_again",) and report.redundant == ("x_third",)
    assert f"{NC}/pdf_source/x_third.pdf" not in {r.original for r in plan.renames}


def test_plan_word_accepted_documents_carry_their_word_pdf(tree: Path) -> None:
    plan_ = word_corpus.plan(tree, only=["word_based_accepted_word"])
    acc = _doc(plan_, "x_y_word_redline_accepted")
    assert acc.sets == ("word_based_accepted_word",)
    assert acc.state == "with_comments_clean"
    assert acc.pdf_src == "grok_run/wr0929/word_based_accepted_word_pdf/x_y_word_redline_accepted.pdf"
    assert plan_.sets["word_based_accepted_word"].documents == (acc.id,)


def test_build_writes_the_holdout_as_word_keys(tree: Path) -> None:
    dest = tree / "corpus" / "word"
    sets = ["word_based", "word_based_randomized", "word_redlines_superdoc", "word_based_0926"]
    report = word_corpus.build(tree, dest, only=sets)
    stems = {n: _cmp(report.plan, n, in_set=s).stem for n, s in (
        ("x_y_redline", "word_based"), ("file_1_file_2_redline", "word_based_randomized"),
        ("p_q_redline", "word_redlines_superdoc"),
    )}
    lines = (dest / "pools" / "holdout.txt").read_text().splitlines()
    assert sorted(line for line in lines if not line.startswith("#")) == sorted(stems.values())
    prov = json.loads((dest / "PROVENANCE.json").read_text())
    assert prov["holdout"]["missing"] == {f"{WB}/holdout.txt": ["not_a_pair"]}
    assert prov["holdout"]["n"] == 3

"""Tests for ``neurotic_docx_bench.tryout`` (the ``bench try`` helper).

Every test runs against a synthetic repository root under ``tmp_path``: a small Word
corpus laid out like ``corpus/no_comments_pdf_was_generated_by_word``, the two holdout
files, and a fake tool (a Python script that copies its input) so nothing here needs
jubarte, Word or soffice.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections.abc import Collection, Sequence
from pathlib import Path

import fitz
import pytest
from typer.testing import CliRunner

from neurotic_docx_bench import cli, tryout

PAGE_A = "Video provides a powerful way to help you prove your point. " * 12
PAGE_B = "Lorem ipsum dolor sit amet, consectetuer adipiscing elit. " * 12

CORPUS = tryout.CORPUS


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _make_pdf(path: Path, page_texts: list[str]) -> Path:
    doc = fitz.open()
    for text in page_texts:
        page = doc.new_page()
        rect = fitz.Rect(72, 72, page.rect.width - 72, page.rect.height - 72)
        page.insert_textbox(rect, text, fontsize=12)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(path))
    doc.close()
    return path


def _write(path: Path, data: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def make_corpus(
    root: Path, pairs: list[tuple[str, str]], *, holdout: Sequence[str] = (), word_variant: Collection[str] = ()
) -> None:
    """Lay out a Word corpus with one row per (base, next) pair.

    Pair stems are ``f"{base}_{next}"``. Redline and accepted files use the
    ``<pair>_redline`` name unless the pair is in ``word_variant``, which gets
    ``<pair>_word_redline`` as well (the preferred one).
    """
    corpus = root / CORPUS
    rows = []
    for base, nxt in pairs:
        stem = f"{base}_{nxt}"
        rows.append({"pair_stem": stem, "base": base, "next": nxt, "origin": "redline_only"})
        for doc in (base, nxt):
            _write(corpus / "docx_source" / f"{doc}.docx", f"docx {doc}".encode())
            _make_pdf(corpus / "pdf_source" / f"{doc}.pdf", [PAGE_A if doc == base else PAGE_B])
        _write(corpus / "docx_redlines_word" / f"{stem}_redline.docx", f"redline {stem}".encode())
        _make_pdf(corpus / "pdf_redlines_word" / f"{stem}_redline.pdf", [PAGE_B])
        _write(corpus / "docx_accepted_word" / f"{stem}_redline.docx", f"accepted {stem}".encode())
        _make_pdf(corpus / "pdf_accepted_word" / f"{stem}_redline.pdf", [PAGE_B])
        if stem in word_variant:
            _write(corpus / "docx_redlines_word" / f"{stem}_word_redline.docx", f"word redline {stem}".encode())
            _make_pdf(corpus / "pdf_redlines_word" / f"{stem}_word_redline.pdf", [PAGE_A, PAGE_B])
    corpus.mkdir(parents=True, exist_ok=True)
    with (corpus / "centralized_mapping.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["pair_stem", "base", "next", "origin"])
        writer.writeheader()
        writer.writerows(rows)
    combined, word_based = tryout.HOLDOUTS
    (root / word_based).parent.mkdir(parents=True, exist_ok=True)
    (root / combined).write_text("# comment\n\n" + "\n".join(holdout[:1]) + "\n")
    (root / word_based).write_text("\n".join(holdout[1:]) + "\n")


PAIRS = [(f"doc{i:02d}", f"doc{i + 1:02d}") for i in range(0, 12, 2)]  # 6 pairs


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    make_corpus(root, PAIRS, holdout=["doc00_doc01", "doc02_doc03"], word_variant={"doc04_doc05"})
    return root


@pytest.fixture
def fake_tool(tmp_path: Path) -> Path:
    """A tool that copies its last input to ``{out}``; exits 3 when the input is named ``fail``."""
    script = tmp_path / "fake_tool.py"
    script.write_text(
        "import shutil, sys\n"
        "args = sys.argv[1:]\n"
        "out = args[args.index('-o') + 1]\n"
        "inputs = [a for a in args if a not in ('-o', out)]\n"
        "if any('fail' in a for a in inputs):\n"
        "    sys.stderr.write('boom\\n'); sys.exit(3)\n"
        "if any('silent' in a for a in inputs):\n"
        "    sys.exit(0)\n"
        "shutil.copyfile(inputs[-1], out)\n"
    )
    return script


def _template(script: Path, *placeholders: str) -> str:
    return " ".join([sys.executable, str(script), *placeholders, "-o", "{out}"])


# --- set building -------------------------------------------------------------


def test_eligible_pairs_excludes_holdouts_and_prefers_word_variant(repo: Path) -> None:
    pairs = tryout.eligible_pairs(repo)
    assert [p.pair_stem for p in pairs] == ["doc04_doc05", "doc06_doc07", "doc08_doc09", "doc10_doc11"]
    word = pairs[0]
    assert word.files["pdf_redline_word"] == CORPUS / "pdf_redlines_word" / "doc04_doc05_word_redline.pdf"
    assert word.files["docx_redline_word"] == CORPUS / "docx_redlines_word" / "doc04_doc05_word_redline.docx"
    assert pairs[1].files["pdf_redline_word"] == CORPUS / "pdf_redlines_word" / "doc06_doc07_redline.pdf"
    assert pairs[1].files["pdf_accepted_word"] == CORPUS / "pdf_accepted_word" / "doc06_doc07_redline.pdf"


def test_eligible_pairs_skips_a_pair_with_a_missing_file(repo: Path) -> None:
    (repo / CORPUS / "pdf_accepted_word" / "doc08_doc09_redline.pdf").unlink()
    assert [p.pair_stem for p in tryout.eligible_pairs(repo)] == ["doc04_doc05", "doc06_doc07", "doc10_doc11"]


def test_build_set_is_deterministic_and_records_sha256(repo: Path) -> None:
    first = tryout.build_set(repo, size=3, seed=7)
    second = tryout.build_set(repo, size=3, seed=7)
    assert [f.pair_stem for f in first] == [f.pair_stem for f in second]
    assert len(first) == 3
    assert [f.pair_stem for f in first] == sorted(f.pair_stem for f in first)
    for fixture in first:
        for column in tryout.FILE_COLUMNS:
            assert fixture.sha256[column] == _sha(repo / fixture.files[column])
    assert [f.pair_stem for f in tryout.build_set(repo, size=3, seed=8)] != [f.pair_stem for f in first]


def test_build_set_refuses_a_pool_smaller_than_the_size(repo: Path) -> None:
    with pytest.raises(tryout.TryoutError, match="4 eligible"):
        tryout.build_set(repo, size=5, seed=1)


def test_write_then_load_set_round_trips(repo: Path) -> None:
    fixtures = tryout.build_set(repo, size=3, seed=7)
    path = tryout.write_set(repo, fixtures)
    assert path == repo / tryout.TRYOUT_DIR / tryout.SET_NAME
    with path.open(newline="") as fh:
        header = next(csv.reader(fh))
    assert header == list(tryout.SET_COLUMNS)
    loaded = tryout.load_set(repo)
    assert loaded.sha256 == _sha(path)
    assert [f.pair_stem for f in loaded.fixtures] == [f.pair_stem for f in fixtures]
    assert loaded.fixtures[0].files == fixtures[0].files
    assert loaded.fixtures[0].sha256 == fixtures[0].sha256
    assert tryout.verify_set(loaded) == []


def test_verify_set_names_a_changed_file(repo: Path) -> None:
    tryout.write_set(repo, tryout.build_set(repo, size=3, seed=7))
    loaded = tryout.load_set(repo)
    target = repo / loaded.fixtures[1].files["docx_next"]
    target.write_bytes(b"tampered")
    assert tryout.verify_set(loaded) == [loaded.fixtures[1].files["docx_next"].as_posix()]


def test_load_set_refuses_an_old_layout(repo: Path) -> None:
    path = repo / tryout.TRYOUT_DIR / tryout.SET_NAME
    path.parent.mkdir(parents=True)
    path.write_text("pair_stem,base,next\na_b,a,b\n")
    with pytest.raises(tryout.TryoutError, match="docx_redline_word"):
        tryout.load_set(repo)


def test_load_set_refuses_a_missing_csv(repo: Path) -> None:
    with pytest.raises(tryout.TryoutError, match="tryout_100.csv"):
        tryout.load_set(repo)


# --- picking ------------------------------------------------------------------


@pytest.fixture
def tryout_set(repo: Path) -> tryout.TryoutSet:
    tryout.write_set(repo, tryout.build_set(repo, size=3, seed=7))
    return tryout.load_set(repo)


def test_pick_by_stem_is_exact(tryout_set: tryout.TryoutSet) -> None:
    stem = tryout_set.fixtures[2].pair_stem
    picked = tryout.pick(tryout_set, stem=stem)
    assert picked.fixture.pair_stem == stem
    assert picked.seed is None


def test_pick_unknown_stem_names_the_closest(tryout_set: tryout.TryoutSet) -> None:
    stem = tryout_set.fixtures[0].pair_stem
    with pytest.raises(tryout.TryoutError, match=stem):
        tryout.pick(tryout_set, stem=stem[:-1] + "X")


def test_pick_with_a_seed_is_stable(tryout_set: tryout.TryoutSet) -> None:
    a = tryout.pick(tryout_set, seed=5)
    b = tryout.pick(tryout_set, seed=5)
    assert a.fixture.pair_stem == b.fixture.pair_stem
    assert a.seed == 5


def test_pick_without_a_seed_reports_the_seed_it_used(tryout_set: tryout.TryoutSet) -> None:
    picked = tryout.pick(tryout_set)
    assert picked.seed is not None
    again = tryout.pick(tryout_set, seed=picked.seed)
    assert again.fixture.pair_stem == picked.fixture.pair_stem


# --- running a tool -----------------------------------------------------------


def test_run_tool_substitutes_placeholders_for_redline(
    tryout_set: tryout.TryoutSet, fake_tool: Path, tmp_path: Path
) -> None:
    fixture = tryout_set.fixtures[0]
    run = tryout.run_tool(
        _template(fake_tool, "{base}", "{next}"), fixture, "redline", tmp_path / "out", root=tryout_set.root, ext="docx"
    )
    assert run.output == tmp_path / "out" / f"{fixture.pair_stem}_redline.docx"
    assert run.output.read_bytes() == (tryout_set.root / fixture.files["docx_next"]).read_bytes()
    assert run.seconds >= 0
    assert str(tryout_set.root / fixture.files["docx_base"]) in run.command
    assert str(tryout_set.root / fixture.files["docx_next"]) in run.command


def test_run_tool_substitutes_input_for_convert(tryout_set: tryout.TryoutSet, fake_tool: Path, tmp_path: Path) -> None:
    fixture = tryout_set.fixtures[0]
    run = tryout.run_tool(
        _template(fake_tool, "{input}"), fixture, "convert", tmp_path / "out", root=tryout_set.root, ext="pdf"
    )
    assert run.output == tmp_path / "out" / f"{fixture.base}_convert.pdf"
    assert run.output.read_bytes() == (tryout_set.root / fixture.files["docx_base"]).read_bytes()


def test_run_tool_refuses_a_template_without_out(tryout_set: tryout.TryoutSet, tmp_path: Path) -> None:
    with pytest.raises(tryout.TryoutError, match=r"\{out\}"):
        tryout.run_tool("mytool {base} {next}", tryout_set.fixtures[0], "redline", tmp_path, root=tryout_set.root)


def test_run_tool_refuses_a_template_without_the_task_inputs(tryout_set: tryout.TryoutSet, tmp_path: Path) -> None:
    with pytest.raises(tryout.TryoutError, match=r"\{next\}"):
        tryout.run_tool("mytool {base} -o {out}", tryout_set.fixtures[0], "redline", tmp_path, root=tryout_set.root)
    with pytest.raises(tryout.TryoutError, match=r"\{input\}"):
        tryout.run_tool("mytool {base} -o {out}", tryout_set.fixtures[0], "convert", tmp_path, root=tryout_set.root)


def test_run_tool_reports_a_non_zero_exit_with_stderr(
    tryout_set: tryout.TryoutSet, fake_tool: Path, tmp_path: Path
) -> None:
    fixture = tryout_set.fixtures[0]
    (tryout_set.root / fixture.files["docx_base"]).rename(
        tryout_set.root / fixture.files["docx_base"].parent / "fail.docx"
    )
    broken = tryout.Fixture(
        pair_stem=fixture.pair_stem,
        base=fixture.base,
        next=fixture.next,
        files={**fixture.files, "docx_base": fixture.files["docx_base"].parent / "fail.docx"},
        sha256=fixture.sha256,
    )
    with pytest.raises(tryout.TryoutError, match="exit 3.*boom"):
        tryout.run_tool(
            _template(fake_tool, "{base}", "{next}"), broken, "redline", tmp_path / "out", root=tryout_set.root
        )


def test_run_tool_reports_a_missing_output(tryout_set: tryout.TryoutSet, fake_tool: Path, tmp_path: Path) -> None:
    fixture = tryout_set.fixtures[0]
    silent = tryout.Fixture(
        pair_stem=fixture.pair_stem,
        base="silent",
        next=fixture.next,
        files={
            **fixture.files,
            "docx_base": _write(tryout_set.root / CORPUS / "docx_source" / "silent.docx", b"x").relative_to(
                tryout_set.root
            ),
        },
        sha256=fixture.sha256,
    )
    with pytest.raises(tryout.TryoutError, match="did not write"):
        tryout.run_tool(
            _template(fake_tool, "{base}", "{next}"), silent, "redline", tmp_path / "out", root=tryout_set.root
        )


def test_run_tool_refuses_an_unknown_task(tryout_set: tryout.TryoutSet, tmp_path: Path) -> None:
    with pytest.raises(tryout.TryoutError, match="accept"):
        tryout.run_tool("x {input} -o {out}", tryout_set.fixtures[0], "accept", tmp_path, root=tryout_set.root)


# --- rendering ----------------------------------------------------------------


def test_render_passthrough_returns_the_pdf(tmp_path: Path) -> None:
    pdf = _make_pdf(tmp_path / "tool" / "x.pdf", [PAGE_A])
    rendered = tryout.render(pdf, "passthrough", tmp_path / "work")
    assert rendered.pdf == pdf
    assert rendered.renderer_id == "passthrough"


def test_render_passthrough_refuses_a_docx(tmp_path: Path) -> None:
    docx = _write(tmp_path / "tool" / "x.docx", b"docx")
    with pytest.raises(tryout.TryoutError, match="passthrough"):
        tryout.render(docx, "passthrough", tmp_path / "work")


class _FakeRenderer:
    name = "fake"

    def __init__(self) -> None:
        self.calls: list[tuple[Path, Path]] = []

    def to_pdfs(
        self, source_dir: Path, work_dir: Path, *, force: bool = False, jobs: int = 12, timeout: float = 1200.0
    ):
        from neurotic_docx_bench.render.base import RenderReport, RenderResult

        self.calls.append((source_dir, work_dir))
        results = []
        for docx in sorted(source_dir.glob("*.docx")):
            pdf = _make_pdf(work_dir / f"{docx.stem}.pdf", [PAGE_A])
            results.append(RenderResult(source=docx, pdf=pdf, ok=True))
        return RenderReport(pdf_dir=work_dir, results=results)


def test_render_with_an_injected_renderer_returns_its_pdf(tmp_path: Path) -> None:
    docx = _write(tmp_path / "tool" / "x.docx", b"docx")
    fake = _FakeRenderer()
    rendered = tryout.render(docx, "soffice", tmp_path / "work", renderer=fake, renderer_id="soffice-test")
    assert rendered.pdf == tmp_path / "work" / "x.pdf"
    assert rendered.renderer_id == "soffice-test"
    assert fake.calls == [(tmp_path / "tool", tmp_path / "work")]


def test_render_reports_a_renderer_that_produced_nothing(tmp_path: Path) -> None:
    docx = _write(tmp_path / "tool" / "x.docx", b"docx")

    class Empty(_FakeRenderer):
        def to_pdfs(self, source_dir, work_dir, **kw):
            from neurotic_docx_bench.render.base import RenderReport, RenderResult

            return RenderReport(pdf_dir=work_dir, results=[RenderResult(source=docx, pdf=None, ok=False, error="no")])

    with pytest.raises(tryout.TryoutError, match="no"):
        tryout.render(docx, "soffice", tmp_path / "work", renderer=Empty(), renderer_id="x")


def test_render_refuses_an_unknown_backend(tmp_path: Path) -> None:
    docx = _write(tmp_path / "tool" / "x.docx", b"docx")
    with pytest.raises(tryout.TryoutError, match="quartz"):
        tryout.render(docx, "quartz", tmp_path / "work")


# --- scoring and comparing ----------------------------------------------------


def _jubarte_outputs(tryout_set: tryout.TryoutSet) -> None:
    """Precomputed jubarte outputs for every fixture of the set: a copy of the oracle
    for redline (scores 100), a different page for convert."""
    for fixture in tryout_set.fixtures:
        red = tryout.jubarte_output(tryout_set, fixture, "redline")
        red.parent.mkdir(parents=True, exist_ok=True)
        red.write_bytes((tryout_set.root / fixture.files["pdf_redline_word"]).read_bytes())
        _make_pdf(tryout.jubarte_output(tryout_set, fixture, "convert"), [PAGE_B])


def test_jubarte_output_paths(tryout_set: tryout.TryoutSet) -> None:
    fixture = tryout_set.fixtures[0]
    jubarte = tryout_set.root / tryout.TRYOUT_DIR / "jubarte"
    assert (
        tryout.jubarte_output(tryout_set, fixture, "redline")
        == jubarte / "redline" / f"{fixture.pair_stem}_jubarte_redline.pdf"
    )
    assert tryout.jubarte_output(tryout_set, fixture, "convert") == jubarte / "convert" / f"{fixture.base}_jubarte.pdf"


def test_score_against_identity_is_100_and_blank_is_lower(tmp_path: Path) -> None:
    oracle = _make_pdf(tmp_path / "oracle.pdf", [PAGE_A])
    same = _make_pdf(tmp_path / "same.pdf", [PAGE_A])
    blank = _make_pdf(tmp_path / "blank.pdf", [""])
    full = tryout.score_against(oracle, same, tmp_path / "w1", dpi=72, key="same")
    low = tryout.score_against(oracle, blank, tmp_path / "w2", dpi=72, key="blank")
    assert full["overall"] == pytest.approx(100.0)
    assert low["overall"] < full["overall"]
    assert full["page_count_oracle"] == 1 and full["page_count_candidate"] == 1
    assert full["page_count_mismatch"] is False
    assert [Path(p).is_file() for p in full["pages"]["oracle"]] == [True]
    assert [Path(p).is_file() for p in full["pages"]["candidate"]] == [True]
    assert full["score_v2"] is None


def test_score_against_with_a_base_pdf_adds_change_region_scores(tmp_path: Path) -> None:
    oracle = _make_pdf(tmp_path / "oracle.pdf", [PAGE_B])
    base = _make_pdf(tmp_path / "base.pdf", [PAGE_A])
    cand = _make_pdf(tmp_path / "cand.pdf", [PAGE_B])
    result = tryout.score_against(oracle, cand, tmp_path / "w", dpi=72, key="k", base_pdf=base)
    assert result["null_score"] is not None and result["null_score"] < 100.0
    assert result["skill_score"] is not None
    assert result["score_v2"] is not None


def test_compare_scores_the_tool_and_jubarte_against_the_same_oracle(
    tryout_set: tryout.TryoutSet, tmp_path: Path
) -> None:
    _jubarte_outputs(tryout_set)
    # a one-page oracle (PAGE_B) over a one-page base (PAGE_A): the change mask is not empty
    fixture = next(f for f in tryout_set.fixtures if not f.files["pdf_redline_word"].name.endswith("_word_redline.pdf"))
    candidate = _make_pdf(tmp_path / "tool" / "x.pdf", [PAGE_A])  # differs from the redline oracle (PAGE_B)
    report = tryout.compare(
        tryout_set, fixture, "redline", candidate, tmp_path / "work", dpi=72, renderer_id="passthrough"
    )
    assert report.fixture is fixture
    assert report.task == "redline"
    assert report.oracle == fixture.files["pdf_redline_word"]
    assert report.against["overall"] == pytest.approx(100.0)
    assert report.tool["overall"] < 100.0
    assert report.delta == pytest.approx(report.tool["overall"] - report.against["overall"])
    assert report.tool["score_v2"] is not None  # redline gets the change-region score (base PDF known)
    assert report.sha256["candidate"] == _sha(candidate)
    assert report.sha256["oracle"] == fixture.sha256["pdf_redline_word"]
    assert report.sha256["against"] == _sha(tryout.jubarte_output(tryout_set, fixture, "redline"))
    assert report.renderer_id == "passthrough"
    assert report.scorer_fingerprint
    assert report.dpi == 72
    as_dict = report.to_dict()
    json.dumps(as_dict)  # serializable
    assert as_dict["fixture"]["pair_stem"] == fixture.pair_stem
    assert set(as_dict) >= {
        "task",
        "oracle",
        "tool",
        "against",
        "delta",
        "sha256",
        "renderer_id",
        "scorer_fingerprint",
        "dpi",
        "timings",
    }


def test_compare_convert_uses_the_base_word_pdf_as_oracle(tryout_set: tryout.TryoutSet, tmp_path: Path) -> None:
    _jubarte_outputs(tryout_set)
    fixture = tryout_set.fixtures[0]
    candidate = tmp_path / "tool" / "x.pdf"
    candidate.parent.mkdir()
    candidate.write_bytes((tryout_set.root / fixture.files["pdf_base_word"]).read_bytes())
    report = tryout.compare(
        tryout_set, fixture, "convert", candidate, tmp_path / "work", dpi=72, renderer_id="passthrough"
    )
    assert report.oracle == fixture.files["pdf_base_word"]
    assert report.tool["overall"] == pytest.approx(100.0)
    assert report.tool["score_v2"] is None
    assert report.against["overall"] < 100.0


def test_compare_refuses_a_missing_jubarte_output(tryout_set: tryout.TryoutSet, tmp_path: Path) -> None:
    fixture = tryout_set.fixtures[0]
    candidate = _make_pdf(tmp_path / "tool" / "x.pdf", [PAGE_A])
    with pytest.raises(tryout.TryoutError, match="jubarte"):
        tryout.compare(tryout_set, fixture, "redline", candidate, tmp_path / "work", dpi=72, renderer_id="passthrough")


def test_compare_against_another_pdf(tryout_set: tryout.TryoutSet, tmp_path: Path) -> None:
    fixture = tryout_set.fixtures[0]
    candidate = _make_pdf(tmp_path / "tool" / "x.pdf", [PAGE_A])
    other = _make_pdf(tmp_path / "other" / "y.pdf", [PAGE_B])
    report = tryout.compare(
        tryout_set,
        fixture,
        "redline",
        candidate,
        tmp_path / "work",
        dpi=72,
        renderer_id="passthrough",
        against_pdf=other,
    )
    assert report.sha256["against"] == _sha(other)
    assert report.against_label == str(other)


# --- fetching from the hub ----------------------------------------------------


class _FakeFiles:
    """``hf_hub_download`` over an in-memory repo; records what was asked for."""

    def __init__(self, files: dict[str, bytes]) -> None:
        self.files = files
        self.calls: list[tuple[str, str | None]] = []

    def hf_hub_download(
        self,
        repo_id: str,
        filename: str,
        *,
        repo_type: str,
        revision: str | None = None,
        local_dir: str | Path | None = None,
    ) -> str:
        self.calls.append((filename, revision))
        if filename not in self.files:
            raise FileNotFoundError(filename)
        assert repo_type == "dataset"
        assert local_dir is not None
        dest = Path(local_dir) / filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(self.files[filename])
        return str(dest)


def _hub_files(tryout_set: tryout.TryoutSet) -> dict[str, bytes]:
    """The tryout set as the fixtures dataset holds it: paths relative to ``corpus/``."""
    _jubarte_outputs(tryout_set)
    root = tryout_set.root
    files: dict[str, bytes] = {}
    for path in (root / "corpus").rglob("*"):
        if path.is_file():
            files[path.relative_to(root / "corpus").as_posix()] = path.read_bytes()
    manifest = {
        "outputs": {
            tryout.jubarte_output(tryout_set, f, task).relative_to(root).as_posix(): {
                "sha256": _sha(tryout.jubarte_output(tryout_set, f, task))
            }
            for f in tryout_set.fixtures
            for task in tryout.TASKS
        }
    }
    files["tryout/jubarte/MANIFEST.json"] = json.dumps(manifest).encode()
    return files


def test_fetch_downloads_one_fixture_and_verifies_it(tryout_set: tryout.TryoutSet, tmp_path: Path) -> None:
    api = _FakeFiles(_hub_files(tryout_set))
    stem = tryout_set.fixtures[1].pair_stem
    dest = tmp_path / "dl"
    fetched, fixture = tryout.fetch("owner/repo", "v1", stem, dest, api=api)
    assert fixture.pair_stem == stem
    assert fetched.root == dest
    assert (dest / fixture.files["docx_base"]).is_file()
    assert tryout.jubarte_output(fetched, fixture, "redline").is_file()
    assert tryout.jubarte_output(fetched, fixture, "convert").is_file()
    requested = {name for name, _ in api.calls}
    assert "tryout/tryout_100.csv" in requested and "tryout/jubarte/MANIFEST.json" in requested
    other = tryout_set.fixtures[0]
    assert other.files["docx_base"].relative_to("corpus").as_posix() not in requested  # one fixture, not the set
    assert {rev for _, rev in api.calls} == {"v1"}


def test_fetch_refuses_a_file_whose_sha256_differs(tryout_set: tryout.TryoutSet, tmp_path: Path) -> None:
    files = _hub_files(tryout_set)
    fixture = tryout_set.fixtures[1]
    files[fixture.files["pdf_redline_word"].relative_to("corpus").as_posix()] = b"corrupt"
    with pytest.raises(tryout.TryoutError, match="sha256"):
        tryout.fetch("owner/repo", None, fixture.pair_stem, tmp_path / "dl", api=_FakeFiles(files))


def test_fetch_refuses_a_jubarte_output_whose_sha256_differs(tryout_set: tryout.TryoutSet, tmp_path: Path) -> None:
    files = _hub_files(tryout_set)
    fixture = tryout_set.fixtures[1]
    files[tryout.jubarte_output(tryout_set, fixture, "redline").relative_to(tryout_set.root / "corpus").as_posix()] = (
        b"corrupt"
    )
    with pytest.raises(tryout.TryoutError, match="MANIFEST"):
        tryout.fetch("owner/repo", None, fixture.pair_stem, tmp_path / "dl", api=_FakeFiles(files))


def test_fetch_unknown_stem_names_the_closest(tryout_set: tryout.TryoutSet, tmp_path: Path) -> None:
    api = _FakeFiles(_hub_files(tryout_set))
    stem = tryout_set.fixtures[1].pair_stem
    with pytest.raises(tryout.TryoutError, match=stem):
        tryout.fetch("owner/repo", None, stem + "Z", tmp_path / "dl", api=api)


# --- JUBARTE_BIN --------------------------------------------------------------


def test_resolve_tool_binary_honours_jubarte_bin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from neurotic_docx_bench import docx_to_pdf

    binary = tmp_path / "jubarte"
    binary.write_bytes(b"")
    monkeypatch.setenv("JUBARTE_BIN", str(binary))
    assert docx_to_pdf.resolve_tool_binary("jubarte") == binary
    assert docx_to_pdf.resolve_tool_binary("jubarte", tmp_path / "explicit") == tmp_path / "explicit"
    monkeypatch.setenv("JUBARTE_BIN", str(tmp_path / "missing"))
    with pytest.raises(FileNotFoundError, match="JUBARTE_BIN"):
        docx_to_pdf.resolve_tool_binary("jubarte")


# --- CLI ----------------------------------------------------------------------


def _invoke(*args: str):
    return CliRunner().invoke(cli.app, ["try", *args])


def test_cli_list_prints_every_stem(tryout_set: tryout.TryoutSet) -> None:
    result = _invoke("list", "--root", str(tryout_set.root))
    assert result.exit_code == 0, result.output
    for fixture in tryout_set.fixtures:
        assert fixture.pair_stem in result.output


def test_cli_run_fixture_with_passthrough_tool_writes_json_and_nothing_under_results(
    tryout_set: tryout.TryoutSet, fake_tool: Path, tmp_path: Path
) -> None:
    _jubarte_outputs(tryout_set)
    fixture = tryout_set.fixtures[0]
    # the fake tool copies {next}; for a redline that is docx_next, so give it a PDF task instead:
    # convert copies {input} = docx_base; point the template at the Word base PDF to get a real PDF out
    template = " ".join(
        [
            sys.executable,
            str(fake_tool),
            "{input}",
            str(tryout_set.root / fixture.files["pdf_base_word"]),  # copied: the last input
            "-o",
            "{out}",
        ]
    )
    result = _invoke(
        "run",
        "--root",
        str(tryout_set.root),
        "--fixture",
        fixture.pair_stem,
        "--task",
        "convert",
        "--tool",
        template,
        "--out",
        str(tmp_path / "out"),
        "--json",
        str(tmp_path / "report.json"),
        "--dpi",
        "72",
    )
    assert result.exit_code == 0, result.output
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["fixture"]["pair_stem"] == fixture.pair_stem
    assert report["task"] == "convert"
    assert report["renderer_id"] == "passthrough"
    assert report["against_label"] == "jubarte"
    assert "delta" in report
    assert not (tryout_set.root / "results").exists()
    assert fixture.pair_stem in result.output


def test_cli_run_random_with_seed_is_stable(tryout_set: tryout.TryoutSet, fake_tool: Path, tmp_path: Path) -> None:
    _jubarte_outputs(tryout_set)
    picked = tryout.pick(tryout_set, seed=3).fixture
    template = " ".join(
        [
            sys.executable,
            str(fake_tool),
            "{base}",
            "{next}",
            str(tryout_set.root / picked.files["pdf_redline_word"]),  # copied: the last input
            "-o",
            "{out}",
        ]
    )
    result = _invoke(
        "run",
        "--root",
        str(tryout_set.root),
        "--random",
        "--seed",
        "3",
        "--task",
        "redline",
        "--tool",
        template,
        "--out",
        str(tmp_path / "out"),
        "--json",
        str(tmp_path / "r.json"),
        "--dpi",
        "72",
    )
    assert result.exit_code == 0, result.output
    report = json.loads((tmp_path / "r.json").read_text())
    assert report["fixture"]["pair_stem"] == picked.pair_stem
    assert report["seed"] == 3
    assert report["tool"]["overall"] == pytest.approx(100.0)


def test_cli_run_requires_a_selection_and_a_tool(tryout_set: tryout.TryoutSet) -> None:
    result = _invoke("run", "--root", str(tryout_set.root), "--tool", "x -o {out}")
    assert result.exit_code != 0
    assert "--random" in result.output and "--fixture" in result.output
    result = _invoke("run", "--root", str(tryout_set.root), "--random")
    assert result.exit_code != 0
    assert "--tool" in result.output


def test_cli_run_reports_a_tool_failure(tryout_set: tryout.TryoutSet, fake_tool: Path, tmp_path: Path) -> None:
    _jubarte_outputs(tryout_set)
    result = _invoke(
        "run",
        "--root",
        str(tryout_set.root),
        "--fixture",
        tryout_set.fixtures[0].pair_stem,
        "--task",
        "convert",
        "--tool",
        f"{sys.executable} {fake_tool} fail {{input}} -o {{out}}",
        "--out",
        str(tmp_path / "out"),
        "--dpi",
        "72",
    )
    assert result.exit_code == 1
    assert "exit 3" in result.output and "boom" in result.output


def test_cli_build_set_writes_the_csv_and_refuses_to_overwrite(repo: Path) -> None:
    result = _invoke("build-set", "--root", str(repo), "--size", "3", "--seed", "7")
    assert result.exit_code == 0, result.output
    assert (repo / tryout.TRYOUT_DIR / tryout.SET_NAME).is_file()
    assert "3 pairs" in result.output
    again = _invoke("build-set", "--root", str(repo), "--size", "3", "--seed", "7")
    assert again.exit_code == 2
    assert "--force" in again.output
    forced = _invoke("build-set", "--root", str(repo), "--size", "3", "--seed", "7", "--force")
    assert forced.exit_code == 0, forced.output


def test_cli_build_set_reports_a_pool_too_small(repo: Path) -> None:
    result = _invoke("build-set", "--root", str(repo), "--size", "9")
    assert result.exit_code == 1
    assert "4 eligible" in result.output


def test_cli_fetch_uses_the_default_api(
    tryout_set: tryout.TryoutSet, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from neurotic_docx_bench import hub

    api = _FakeFiles(_hub_files(tryout_set))
    monkeypatch.setattr(hub, "default_api", lambda: api)
    stem = tryout_set.fixtures[2].pair_stem
    result = _invoke("fetch", stem, "--dest", str(tmp_path / "dl"), "--repo", "owner/repo", "--revision", "v2")
    assert result.exit_code == 0, result.output
    assert (tmp_path / "dl" / tryout_set.fixtures[2].files["pdf_redline_word"]).is_file()
    assert {rev for _, rev in api.calls} == {"v2"}
    listed = _invoke("list", "--root", str(tmp_path / "dl"))
    assert listed.exit_code == 0 and stem in listed.output


def test_cli_fetch_reports_a_bad_stem(
    tryout_set: tryout.TryoutSet, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from neurotic_docx_bench import hub

    monkeypatch.setattr(hub, "default_api", lambda: _FakeFiles(_hub_files(tryout_set)))
    result = _invoke("fetch", "nope", "--dest", str(tmp_path / "dl"), "--repo", "owner/repo")
    assert result.exit_code == 1
    assert "closest" in result.output


def test_cli_run_against_a_template_and_a_pdf(tryout_set: tryout.TryoutSet, fake_tool: Path, tmp_path: Path) -> None:
    fixture = tryout_set.fixtures[0]
    oracle = tryout_set.root / fixture.files["pdf_redline_word"]
    template = " ".join([sys.executable, str(fake_tool), "{base}", "{next}", str(oracle), "-o", "{out}"])
    common = [
        "run",
        "--root",
        str(tryout_set.root),
        "--fixture",
        fixture.pair_stem,
        "--tool",
        template,
        "--out",
        str(tmp_path / "out"),
        "--dpi",
        "72",
    ]
    result = _invoke(*common, "--against", template, "--json", str(tmp_path / "a.json"))
    assert result.exit_code == 0, result.output
    report = json.loads((tmp_path / "a.json").read_text())
    assert report["against_label"] == template
    assert report["delta"] == pytest.approx(0.0)
    assert "against_s" in report["timings"] and "tool_s" in report["timings"]
    result = _invoke(*common, "--against", str(oracle), "--json", str(tmp_path / "b.json"))
    assert result.exit_code == 0, result.output
    assert json.loads((tmp_path / "b.json").read_text())["against_label"] == str(oracle)
    result = _invoke(*common, "--against", str(tmp_path / "missing.pdf"))
    assert result.exit_code == 1 and "neither" in result.output


def test_cli_run_rejects_bad_task_and_renderer(tryout_set: tryout.TryoutSet) -> None:
    common = ["run", "--root", str(tryout_set.root), "--random", "--tool", "x {base} {next} -o {out}"]
    assert _invoke(*common, "--task", "accept").exit_code == 2
    assert _invoke(*common, "--renderer", "quartz").exit_code == 2


def test_cli_run_passthrough_refuses_a_docx_output(
    tryout_set: tryout.TryoutSet, fake_tool: Path, tmp_path: Path
) -> None:
    _jubarte_outputs(tryout_set)
    # a tool that writes a .docx cannot be scored through passthrough: the library guard refuses it
    fixture = tryout_set.fixtures[0]
    run = tryout.run_tool(
        _template(fake_tool, "{base}", "{next}"), fixture, "redline", tmp_path / "o", root=tryout_set.root, ext="docx"
    )
    with pytest.raises(tryout.TryoutError, match="passthrough"):
        tryout.render(run.output, "passthrough", tmp_path / "w")


# --- edges ------------------------------------------------------------------------


def test_read_holdout_of_a_missing_file_is_empty(tmp_path: Path) -> None:
    assert tryout.read_holdout(tmp_path / "nope.txt") == set()


def test_eligible_pairs_needs_the_mapping(tmp_path: Path) -> None:
    with pytest.raises(tryout.TryoutError, match="centralized_mapping.csv"):
        tryout.eligible_pairs(tmp_path)


def test_pick_refuses_an_empty_set(tryout_set: tryout.TryoutSet) -> None:
    empty = tryout.TryoutSet(root=tryout_set.root, csv_path=tryout_set.csv_path, sha256="0", fixtures=())
    with pytest.raises(tryout.TryoutError, match="no fixtures"):
        tryout.pick(empty, seed=1)


def test_run_tool_reports_a_missing_binary(tryout_set: tryout.TryoutSet, tmp_path: Path) -> None:
    fixture = tryout_set.fixtures[0]
    with pytest.raises(tryout.TryoutError, match="not found"):
        tryout.run_tool("/no/such/tool {base} {next} -o {out}", fixture, "redline", tmp_path, root=tryout_set.root)


def test_run_tool_reports_a_timeout(tryout_set: tryout.TryoutSet, tmp_path: Path) -> None:
    fixture = tryout_set.fixtures[0]
    template = f"{sys.executable} -c import\\ time;time.sleep(5) {{base}} {{next}} -o {{out}}"
    with pytest.raises(tryout.TryoutError, match="timed out"):
        tryout.run_tool(template, fixture, "redline", tmp_path, root=tryout_set.root, timeout=0.2)


def test_unknown_task_is_refused_everywhere(tryout_set: tryout.TryoutSet, tmp_path: Path) -> None:
    fixture = tryout_set.fixtures[0]
    with pytest.raises(tryout.TryoutError, match="accept"):
        tryout.jubarte_output(tryout_set, fixture, "accept")
    with pytest.raises(tryout.TryoutError, match="accept"):
        tryout.compare(tryout_set, fixture, "accept", tmp_path / "x.pdf", tmp_path / "w", renderer_id="passthrough")


def test_render_rejects_an_unknown_backend_even_with_a_renderer(tmp_path: Path) -> None:
    from neurotic_docx_bench.render.passthrough import PassthroughRenderer

    pdf = _make_pdf(tmp_path / "a.pdf", [PAGE_A])
    with pytest.raises(tryout.TryoutError, match="quartz"):
        tryout.render(pdf, "quartz", tmp_path / "w", renderer=PassthroughRenderer())


def test_fetch_reports_a_file_the_hub_lacks(tryout_set: tryout.TryoutSet, tmp_path: Path) -> None:
    files = _hub_files(tryout_set)
    fixture = tryout_set.fixtures[1]
    del files[fixture.files["docx_base"].relative_to("corpus").as_posix()]
    with pytest.raises(tryout.TryoutError, match="has no"):
        tryout.fetch("owner/repo", None, fixture.pair_stem, tmp_path / "dl", api=_FakeFiles(files))


def test_fetch_reports_a_jubarte_output_missing_from_the_manifest(tryout_set: tryout.TryoutSet, tmp_path: Path) -> None:
    files = _hub_files(tryout_set)
    files["tryout/jubarte/MANIFEST.json"] = json.dumps({"outputs": {}}).encode()
    fixture = tryout_set.fixtures[1]
    with pytest.raises(tryout.TryoutError, match="MANIFEST.json does not list"):
        tryout.fetch("owner/repo", None, fixture.pair_stem, tmp_path / "dl", api=_FakeFiles(files))

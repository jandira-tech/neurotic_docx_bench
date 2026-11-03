"""The speed release — ledger.speed.emit and the results/release/speed.json half of
the release-views flow (Plan 3b, #119).

Spec: docs/plans/2026-11-02-plan3b-cases-speed.md; survey:
docs/plans/reviews/plan3b-survey.md §1.2. The contract is the 10,000-input page
(per-pair raw rows aggregated), NOT the results/speed.jsonl leaderboard view.
The release contract is `bench_ops.models` (the bench-ops dependency):
Speed, dumps_compact.

bench-ops is not a venv dependency (#134): it is a PEP 723 inline dependency of
scripts/release_views.py. This module skips under a plain `uv run pytest` and
runs under the overlay that provides it.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

pytest.importorskip(
    "bench_ops",
    reason=(
        "bench-ops is a PEP 723 inline dependency of scripts/release_views.py, not a "
        "venv dependency (#134); run: uv run --with 'bench-ops @ git+https://github.com/"
        "arthrod/bench-ops@35ab2cbeb8bc44d5059878d14176dc90c5b46f5d' pytest -q "
        "tests/test_ledger_cases.py tests/test_ledger_speed.py tests/test_ledger_cases_ref.py"
    ),
)

from neurotic_docx_bench.ledger import build as bd
from neurotic_docx_bench.ledger import speed as speed_emit
from test_ledger_build import repo as _ledger_repo  # noqa: F401  the fake-repo fixture, shared with test_ledger_build

from bench_ops.models import Speed, dumps_compact

REPO = Path(__file__).resolve().parents[1]
T0 = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)

# The five published 10k lanes (results/speed_10k/redlines/SUMMARY.md, 2026-11-02).
TEN_K_TOOLS = ["docxodus", "jubarte-rust", "jubarte-rust-inproc", "jubarte-wasm", "superdoc"]

PAIRS_CSV_HEADER = "key,base,next,category,base_bytes,next_bytes,base_state,next_state\n"


def _stable(speed: Speed) -> str:
    """dumps_compact with the emission clock pinned, so two runs compare."""
    return dumps_compact(speed.model_copy(update={"generated": T0}))


def _row(key: str, category: str, ok: bool, ms: float, **extra: object) -> str:
    return json.dumps({"key": key, "category": category, "ok": ok, "ms": ms, **extra}) + "\n"


def _write_speed_sources(root: Path, *, with_notes: bool = True) -> None:
    """A minimal results/speed_10k in the real input shapes: per-pair JSONL rows
    ({key, category, ok, ms, ...}), pairs_10k.csv, NOTES.md, and no pdf/SUMMARY.md
    (the PDF task is 'Not measured yet.')."""
    base = root / "results" / "speed_10k"
    per_pair = base / "redlines" / "per_pair"
    per_pair.mkdir(parents=True)
    (per_pair / "alpha.jsonl").write_text(
        _row("p1", "grid", True, 10.0, out_bytes=1)
        + _row("p2", "grid", True, 20.0, out_bytes=1)
        + _row("p3", "identity", True, 30.0, out_bytes=1)
        + _row("p4", "word_compare", True, 40.0, out_bytes=1),
        encoding="utf-8",
    )
    (per_pair / "beta.jsonl").write_text(
        _row("p1", "grid", True, 10.0, out_bytes=1)
        + _row("p2", "grid", False, 120000.0, out_bytes=1, timeout=True)
        + _row("p3", "identity", True, 30.0, out_bytes=1)
        + _row("p4", "word_compare", False, 5.0, out_bytes=1),
        encoding="utf-8",
    )
    if with_notes:
        (base / "redlines" / "NOTES.md").write_text(
            "# Redline speed run, notes\n\n## Heading\n\nA paragraph.\n\n- bullet one\n- bullet two\n",
            encoding="utf-8",
        )
    (base / "pairs_10k.csv").write_text(
        PAIRS_CSV_HEADER
        + "p1,a.docx,b.docx,grid,100,100,clean,clean\n"
        + "p2,a.docx,b.docx,grid,200,200,clean,clean\n"
        + "p3,a.docx,b.docx,identity,300,300,clean,clean\n"
        + "p4,a.docx,b.docx,word_compare,400,400,clean,clean\n",
        encoding="utf-8",
    )


# ---- emit(root) -> Speed: the synthetic store ------------------------------------------


def test_emit_synthetic_store_validates_and_carries_the_tables(tmp_path: Path) -> None:
    _write_speed_sources(tmp_path)
    speed = speed_emit.emit(tmp_path)
    assert isinstance(speed, Speed)
    assert speed.version and speed.repo and speed.title and speed.intro
    assert speed.generated.tzinfo is not None  # naive timestamps are rejected
    assert [t.id for t in speed.tasks] == ["pdf", "redlines"]  # sorted by id
    red = next(t for t in speed.tasks if t.id == "redlines")
    # the redline task: one lane per per_pair file, complete coverage
    assert red.available is True
    assert red.planned == 4
    assert [(c.tool, c.completed, c.planned) for c in red.coverage] == [
        ("alpha", 4, 4),
        ("beta", 4, 4),
    ]
    tables = {t.id: t for t in red.tables}
    assert [t.id for t in red.tables] == ["category", "common", "quartile"]  # sorted by id
    assert set(tables) == {"common", "category", "quartile"}
    # common pairs: failures are excluded from the timing statistics
    common = {r.tool: r for r in tables["common"].rows}
    assert set(common) == {"alpha", "beta"}
    a, b = common["alpha"], common["beta"]
    assert (a.bucket, a.n, a.ok, a.failed) == ("4 common", 4, 4, 0)
    assert a.median_ms == pytest.approx(25.0)
    assert a.mean_ms == pytest.approx(25.0)
    assert (b.bucket, b.n, b.ok, b.failed) == ("4 common", 4, 2, 2)
    assert b.median_ms == pytest.approx(20.0)  # ok rows only: [10, 30]
    assert b.mean_ms == pytest.approx(20.0)
    assert b.max_ms == pytest.approx(30.0)
    assert b.ok_total_s == pytest.approx(0.04)
    # by category: the 'all' bucket plus every category present in pairs_10k.csv
    cat = {(r.tool, r.bucket): r for r in tables["category"].rows}
    assert set(cat) == {
        ("alpha", b_) for b_ in ("all", "grid", "identity", "word_compare")
    } | {("beta", b_) for b_ in ("all", "grid", "identity", "word_compare")}
    assert (cat[("alpha", "all")].n, cat[("alpha", "all")].ok) == (4, 4)
    assert (cat[("alpha", "grid")].n, cat[("alpha", "grid")].ok) == (2, 2)
    assert cat[("alpha", "grid")].median_ms == pytest.approx(15.0)
    assert (cat[("beta", "grid")].n, cat[("beta", "grid")].ok, cat[("beta", "grid")].failed) == (2, 1, 1)
    # by base-size quartile: every tool is covered
    quart = {r.tool for r in tables["quartile"].rows}
    assert quart == {"alpha", "beta"}


def test_emit_synthetic_notes_are_plain_text_sections(tmp_path: Path) -> None:
    _write_speed_sources(tmp_path)
    speed = speed_emit.emit(tmp_path)
    red = next(t for t in speed.tasks if t.id == "redlines")
    assert [(n.heading, n.paragraphs, n.bullets) for n in red.notes] == [
        ("Heading", ["A paragraph."], ["bullet one", "bullet two"])
    ]
    # no markup anywhere in the notes; the model relies on the escaping viewer,
    # so emit must never feed it markup in the first place
    for note in red.notes:
        for text in [note.heading, *note.paragraphs, *note.bullets]:
            assert "<" not in text


def test_emit_synthetic_pdf_task_is_not_measured(tmp_path: Path) -> None:
    _write_speed_sources(tmp_path)
    speed = speed_emit.emit(tmp_path)
    pdf = next(t for t in speed.tasks if t.id == "pdf")
    assert pdf.id == "pdf"
    assert pdf.available is False
    assert pdf.tables == []  # nothing to render for an unmeasured task


def test_emit_is_deterministic(tmp_path: Path) -> None:
    _write_speed_sources(tmp_path)
    assert _stable(speed_emit.emit(tmp_path)) == _stable(speed_emit.emit(tmp_path))


# ---- emit(root) on the real 10k store of this checkout ---------------------------------


def _has_10k_store() -> bool:
    base = REPO / "results" / "speed_10k"
    return (base / "pairs_10k.csv").is_file() and (base / "redlines" / "per_pair").is_dir()


def test_emit_reproduces_the_published_10k_page() -> None:
    """The values SUMMARY.md publishes today: five complete lanes, the three
    tables' shapes, the timeout and quartile cuts, and the pinned jubarte-rust
    and docxodus rows (counts exact, timings to the page's one decimal)."""
    if not _has_10k_store():
        pytest.skip("no results/speed_10k store in this checkout")
    speed = speed_emit.emit(REPO)
    assert isinstance(speed, Speed)
    red = next(t for t in speed.tasks if t.id == "redlines")
    assert red.available is True
    assert red.timeout_ms == 120000
    assert red.quartile_cuts_bytes == [10601, 19102, 56197]
    # the five published lanes are all present and complete; a rerun lane still in
    # progress (docxodus-csharp-inproc today) may show its real partial coverage
    lanes = {c.tool: c for c in red.coverage}
    assert set(TEN_K_TOOLS) <= set(lanes)
    for tool in TEN_K_TOOLS:
        assert (lanes[tool].completed, lanes[tool].planned) == (10000, 10000)
    for c in red.coverage:
        assert c.completed <= c.planned
    tables = {t.id: t for t in red.tables}
    assert set(tables) == {"common", "category", "quartile"}
    assert len(tables["common"].rows) == 5
    assert len(tables["category"].rows) == 25  # 5 tools x (all + 4 categories)
    assert len(tables["quartile"].rows) == 20  # 5 tools x Q1..Q4
    common = {r.tool: r for r in tables["common"].rows}
    jr, dx, sd = common["jubarte-rust"], common["docxodus"], common["superdoc"]
    assert (jr.n, jr.ok, jr.failed) == (10000, 10000, 0)
    assert jr.median_ms == pytest.approx(45.0, abs=0.1)
    assert jr.mean_ms == pytest.approx(83.0, abs=0.1)
    assert jr.p95_ms == pytest.approx(246.8, abs=0.1)
    assert (dx.n, dx.ok, dx.failed) == (10000, 9933, 67)
    assert (sd.n, sd.ok, sd.failed) == (10000, 798, 9202)
    # every table row stays consistent: n = ok + failed
    for table in red.tables:
        for r in table.rows:
            assert r.n == r.ok + r.failed, f"{table.id}/{r.tool}/{r.bucket}"


def test_emit_real_notes_are_the_notesc_sections_in_plain_text() -> None:
    if not _has_10k_store():
        pytest.skip("no results/speed_10k store in this checkout")
    speed = speed_emit.emit(REPO)
    red = next(t for t in speed.tasks if t.id == "redlines")
    headings = [n.heading for n in red.notes]
    assert "Run of 2026-09-29 (00:45 to 09:23 EDT)" in headings
    assert "Load" in headings
    for note in red.notes:
        for text in [note.heading, *note.paragraphs, *note.bullets]:
            assert "<" not in text  # plain text only; the viewer escapes, emit never feeds markup
    # `backtick` code spans stay plain text in the contract (the viewer renders
    # them as <code> after escaping)
    assert any(
        "`" in text for note in red.notes for text in (*note.paragraphs, *note.bullets)
    )
    # the pdf task stays "Not measured yet." while results/speed_10k/pdf/ is absent
    pdf = next(t for t in speed.tasks if t.id == "pdf")
    assert pdf.available is False


def test_emit_real_is_deterministic() -> None:
    if not _has_10k_store():
        pytest.skip("no results/speed_10k store in this checkout")
    assert _stable(speed_emit.emit(REPO)) == _stable(speed_emit.emit(REPO))


# ---- the release-views flow writes results/release/speed.json and --check covers it ----


@pytest.fixture
def repo_with_release_sources(_ledger_repo: Path) -> Path:  # noqa: F811  fixture parameter
    """The test_ledger_build fake repo plus this module's synthetic speed_10k."""
    _write_speed_sources(_ledger_repo)
    return _ledger_repo


def test_release_views_write_speed_json(repo_with_release_sources: Path) -> None:
    """ledger.build.run_release_views — the shared body scripts/release_views.py
    runs — writes speed.json since `bench report` stopped writing it (#134); no
    case sources on this repo (speed only), so --allow-no-cases."""
    said: list[str] = []
    assert (
        bd.run_release_views(
            repo_with_release_sources, allow_no_cases=True, echo=said.append
        )
        == 0
    )
    speed_path = repo_with_release_sources / "results" / "release" / "speed.json"
    assert speed_path.is_file(), "the release views must write results/release/speed.json"
    speed = Speed.model_validate_json(speed_path.read_text(encoding="utf-8"))
    assert speed.generated.tzinfo is not None  # naive timestamps are rejected
    assert [t.id for t in speed.tasks] == ["pdf", "redlines"]  # sorted by id
    text = speed_path.read_text(encoding="utf-8")
    assert (
        json.dumps(json.loads(text), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        == text.strip()
    ), "speed.json must be compact JSON with sorted keys"
    # --check passes right after a write, and flags a tampered speed.json
    ok: list[str] = []
    assert bd.run_release_views(repo_with_release_sources, check=True, allow_no_cases=True, echo=ok.append) == 0
    speed_path.write_text('{"tampered":true}\n', encoding="utf-8")
    stale: list[str] = []
    assert bd.run_release_views(repo_with_release_sources, check=True, allow_no_cases=True, echo=stale.append) == 1
    assert "results/release/speed.json" in " ".join(stale)

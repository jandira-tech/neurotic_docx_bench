"""score_v2 + skill score (PR3): change-region fidelity and null-baseline normalization.

The v1 pixel metric hands out ~55-70 points for reproducing unchanged body text (the
do-nothing baseline outscored half the leaderboard). Two parallel, informational
metrics fix the dynamic range without touching the parity-locked scorer:

- ``null_score``: what rendering the BASE unchanged scores against the oracle.
- ``skill_score``: (overall - null) / (100 - null) * 100 — 0 means "no better than
  doing nothing", 100 means oracle-perfect, negative means worse than nothing.
- ``score_v2``: ink-F1 computed ONLY inside the change-region mask (where base and
  oracle renders differ), so unchanged text stops subsidizing the score.
"""

from __future__ import annotations

import json
from pathlib import Path

import pymupdf as fitz
import pytest

from neurotic_docx_bench import pipeline, score_v2

BODY = (
    "This agreement is made between the parties hereto. " * 8
    + "Each party shall perform its obligations in good faith. " * 8
)
INSERTED = "THE TIGER CLAUSE: the licensee shall feed the tiger twice daily without fail."


def _make_pdf(path: Path, paragraphs: list[tuple[str, tuple[float, float, float]]]) -> Path:
    doc = fitz.open()
    page = doc.new_page()
    y = 72.0
    for text, color in paragraphs:
        rect = fitz.Rect(72, y, page.rect.width - 72, y + 220)
        page.insert_textbox(rect, text, fontsize=11, color=color)
        y += 230
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(path))
    doc.close()
    return path


BLACK = (0.0, 0.0, 0.0)
RED = (0.8, 0.0, 0.0)


@pytest.fixture
def trio(tmp_path: Path) -> dict[str, Path]:
    """base = body only; oracle = body + red inserted clause; candidates vary."""
    return {
        "base": _make_pdf(tmp_path / "base.pdf", [(BODY, BLACK)]),
        "oracle": _make_pdf(tmp_path / "oracle.pdf", [(BODY, BLACK), (INSERTED, RED)]),
        "perfect": _make_pdf(tmp_path / "perfect.pdf", [(BODY, BLACK), (INSERTED, RED)]),
        "do_nothing": _make_pdf(tmp_path / "nothing.pdf", [(BODY, BLACK)]),
    }


def test_perfect_candidate_scores_high_on_v2_and_skill(trio, tmp_path):
    result = pipeline.score_pdf_pair(
        trio["oracle"], trio["perfect"], tmp_path / "w1", base_pdf=trio["base"],
    )
    assert result["null_score"] is not None
    assert result["null_score"] < 95.0  # doing nothing must not look near-perfect
    assert result["score_v2"] == pytest.approx(100.0, abs=2.0)
    assert result["skill_score"] == pytest.approx(100.0, abs=2.0)


def test_do_nothing_candidate_scores_near_zero_on_v2_and_skill(trio, tmp_path):
    result = pipeline.score_pdf_pair(
        trio["oracle"], trio["do_nothing"], tmp_path / "w2", base_pdf=trio["base"],
    )
    # The candidate IS the null baseline: skill ~ 0, and the change region contains
    # none of the inserted clause's ink: v2 ~ 0.
    assert result["skill_score"] == pytest.approx(0.0, abs=5.0)
    assert result["score_v2"] < 20.0


def test_v2_fields_none_without_base(trio, tmp_path):
    result = pipeline.score_pdf_pair(trio["oracle"], trio["perfect"], tmp_path / "w3")
    assert result["null_score"] is None
    assert result["skill_score"] is None
    assert result["score_v2"] is None


def test_v2_none_when_base_equals_oracle(trio, tmp_path):
    """No visible change between base and oracle → mask empty → v2 undefined (the
    roundtrip benchmark owns that case)."""
    result = pipeline.score_pdf_pair(
        trio["base"], trio["do_nothing"], tmp_path / "w4", base_pdf=trio["base"],
    )
    assert result["score_v2"] is None


def test_skill_score_formula_and_clamp():
    assert score_v2.skill_score(100.0, 60.0) == pytest.approx(100.0)
    assert score_v2.skill_score(60.0, 60.0) == pytest.approx(0.0)
    assert score_v2.skill_score(80.0, 60.0) == pytest.approx(50.0)
    assert score_v2.skill_score(20.0, 60.0) == pytest.approx(-100.0)  # clamped
    assert score_v2.skill_score(50.0, 99.99999) is None  # degenerate null


def test_resolve_base_pdfs_from_mapping(tmp_path):
    csv = tmp_path / "map.csv"
    csv.write_text(
        "pair_stem,base,next,origin\n"
        "Alpha_Beta,Alpha,Beta,redline_only\n"
        "file_1_file_2,file_1,file_2,randomized_chain\n",
    )
    base_dir = tmp_path / "pdf_source"
    base_dir.mkdir()
    (base_dir / "Alpha.pdf").write_bytes(b"%PDF-1.4\n")
    resolved = score_v2.resolve_base_pdfs([csv], base_dir)
    # Keys are lowercased to match the score key space; missing base PDFs are absent.
    assert resolved == {"alpha_beta": base_dir / "Alpha.pdf"}


def test_null_cache_roundtrip(tmp_path, trio):
    cache_path = tmp_path / "null_baseline.json"
    entry_key = score_v2.null_cache_key(trio["oracle"], trio["base"], 144)
    assert score_v2.load_null_cache(cache_path) == {}
    score_v2.merge_null_cache(cache_path, {entry_key: 61.25})
    assert score_v2.load_null_cache(cache_path) == {entry_key: 61.25}
    # Merge preserves existing entries.
    score_v2.merge_null_cache(cache_path, {"other": 50.0})
    loaded = score_v2.load_null_cache(cache_path)
    assert loaded[entry_key] == 61.25 and loaded["other"] == 50.0
    assert json.loads(cache_path.read_text())  # valid json on disk


def test_score_folders_full_threads_base_map(trio, tmp_path):
    oracle_dir = tmp_path / "oracle"
    cand_dir = tmp_path / "cand"
    oracle_dir.mkdir()
    cand_dir.mkdir()
    import shutil

    shutil.copy(trio["oracle"], oracle_dir / "alpha_beta_redline.pdf")
    shutil.copy(trio["perfect"], cand_dir / "alpha_beta_tool_redline.pdf")
    full = pipeline.score_folders_full(
        oracle_dir,
        cand_dir,
        tmp_path / "w5",
        jobs=1,
        candidate_tool="tool",
        base_map={"alpha_beta": trio["base"]},
    )
    assert full["alpha_beta"]["score_v2"] == pytest.approx(100.0, abs=2.0)
    assert full["alpha_beta"]["skill_score"] is not None


def test_build_results_aggregates_optional_metrics() -> None:
    import uuid
    from datetime import UTC, datetime

    from neurotic_docx_bench.config import BenchConfig
    from neurotic_docx_bench.results_schema import build_results

    per_doc = {
        "a": {"skill_score": 80.0, "score_v2": 90.0},
        "b": {"skill_score": 40.0, "score_v2": None},
        "c": {"skill_score": None, "score_v2": None},
    }
    result = build_results(
        id_run=uuid.uuid7(),
        vendor="acme",
        benchmark="script_redlines",
        scores={"a": 90.0, "b": 70.0, "c": 60.0},
        per_doc=per_doc,
        speed_samples_ms=[],
        environment_config=BenchConfig(source_of_truth=Path("corpus/oracle")),
        timestamp=datetime(2026, 8, 2, tzinfo=UTC),
    )
    assert result.skill_mean == pytest.approx(60.0)
    assert result.skill_median == pytest.approx(60.0)
    assert result.v2_mean == pytest.approx(90.0)
    assert result.v2_median == pytest.approx(90.0)
    line = result.to_json_dict()
    assert line["skill_median"] == pytest.approx(60.0)

    empty = build_results(
        id_run=uuid.uuid7(),
        vendor="acme",
        benchmark="script_redlines",
        scores={"a": 90.0},
        per_doc={"a": {}},
        speed_samples_ms=[],
        environment_config=BenchConfig(source_of_truth=Path("corpus/oracle")),
        timestamp=datetime(2026, 8, 2, tzinfo=UTC),
    )
    assert empty.skill_mean is None and empty.v2_median is None

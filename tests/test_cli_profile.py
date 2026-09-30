"""``bench profile``: per-stage timings on a seeded sample, uncached (plan item 9b)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from typer.testing import CliRunner

from neurotic_docx_bench import cli
from neurotic_docx_bench import content_cache as cc
from neurotic_docx_bench.pipeline import oracle_pair_key

runner = CliRunner()


def test_limited_source_samples_by_seed_instead_of_taking_the_head(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    for i in range(12):
        (src / f"{i:02d}_redline.pdf").write_bytes(b"%PDF")
    head, is_temp = cli._limited_source(src, "*.pdf", 3)
    assert is_temp
    assert sorted(p.name for p in head.iterdir()) == ["00_redline.pdf", "01_redline.pdf", "02_redline.pdf"]
    seeded, is_temp = cli._limited_source(src, "*.pdf", 3, seed=7)
    assert is_temp
    picked = sorted(p.name for p in seeded.iterdir())
    assert len(picked) == 3
    assert picked != ["00_redline.pdf", "01_redline.pdf", "02_redline.pdf"]
    again, _ = cli._limited_source(src, "*.pdf", 3, seed=7)
    assert sorted(p.name for p in again.iterdir()) == picked
    shutil.rmtree(head)
    shutil.rmtree(seeded)
    shutil.rmtree(again)


def test_profile_drives_an_uncached_unrecorded_sample_and_writes_json(tmp_path: Path, monkeypatch) -> None:
    seen: dict[str, object] = {}

    def fake(**kwargs):
        seen["active"] = cc.active()
        seen["kwargs"] = kwargs
        sink = kwargs["timings_sink"]
        sink["jubarte"] = {
            "renderer_id": "soffice-24.2",
            "wall_s": 1.5,
            "benchmarks": {"script_redlines": {"a_b": {"raster_s": 1.0, "score_s": 3.0}}},
        }

    monkeypatch.setattr(cli, "_drive_runs", fake)
    monkeypatch.delenv("BENCH_NO_CACHE", raising=False)
    out = tmp_path / "profile.json"
    result = runner.invoke(
        cli.app,
        ["profile", "--config", str(tmp_path / "bench.yaml"), "--results-dir", str(tmp_path / "results"),
         "--run", "jubarte", "--sample", "4", "--seed", "3", "--dpi", "96", "--json", str(out)],
    )
    assert result.exit_code == 0, result.output
    assert seen["active"] is None, "profiling never reads or writes the content cache"
    kwargs = seen["kwargs"]
    assert kwargs["emit"] is False and kwargs["do_gate"] is False and kwargs["rerun"] is True
    assert kwargs["names"] == ["jubarte"]
    assert kwargs["limit"] == 4 and kwargs["sample_seed"] == 3 and kwargs["dpi"] == 96
    assert kwargs["oracle_check"] is False and kwargs["canary_check"] is False
    report = json.loads(out.read_text())
    assert report["cached"] is False and report["sample"] == 4 and report["seed"] == 3
    assert report["runs"]["jubarte"]["wall_s"] == 1.5
    assert report["runs"]["jubarte"]["benchmarks"]["script_redlines"]["score_s"]["n"] == 1
    assert "score" in result.output and "jubarte: wall 1.50 s" in result.output
    assert "cache off" in result.output


def test_profile_end_to_end_reports_raster_and_score_stages(tmp_path: Path, sample_oracle_pdfs) -> None:
    oracle = tmp_path / "oracle"
    cand = tmp_path / "cand"
    oracle.mkdir()
    cand.mkdir()
    for pdf in sample_oracle_pdfs:
        shutil.copy(pdf, oracle / pdf.name)
        # The oracle side folds the ``_word`` capture variant into the pair key.
        shutil.copy(pdf, cand / f"{oracle_pair_key(pdf.stem)}_prebaked_redline.pdf")
    cfg = tmp_path / "bench.yaml"
    cfg.write_text(
        f"source_of_truth: {oracle}\nruns:\n"
        f"  - {{name: prebaked, render: passthrough, modified: {cand}, unversioned: true, "
        f"vendor: prebaked, jobs: 1}}\n",
    )
    out = tmp_path / "profile.json"
    result = runner.invoke(
        cli.app,
        ["profile", "-c", str(cfg), "--results-dir", str(tmp_path / "results"),
         "--runs-dir", str(tmp_path / "runs"), "--sample", "1", "--json", str(out)],
    )
    assert result.exit_code == 0, result.output
    report = json.loads(out.read_text())
    run = report["runs"]["prebaked"]
    assert run["renderer_id"] == "passthrough"
    assert run["wall_s"] > 0
    stats = run["benchmarks"]["script_redlines"]
    assert stats["raster_s"]["n"] == 1 and stats["score_s"]["n"] == 1
    assert stats["raster_s"]["total_s"] > 0 and stats["score_s"]["total_s"] > 0
    # Nothing recorded: profiling is never a bench result.
    assert not (tmp_path / "results" / "bench.jsonl").exists()
    assert cc.active() is None

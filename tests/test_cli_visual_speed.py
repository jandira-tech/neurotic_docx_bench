"""End-to-end wiring: a visual_* benchmark run emits a JSONL line whose speed
stats come from the renderer's ``duration_ns`` (not the hardcoded empty
``timings={}`` that previously zeroed ``overall_mean_speed``).

The renderer is stubbed (no real Chromium / LibreOffice): it copies the oracle
PDF to the work dir (identity → score 100) and returns a ``RenderResult`` with a
synthetic ``duration_ns``. This exercises the full chain —
``_execute_run`` → ``render_timings_from_report`` → ``BenchmarkOutcome.timings``
→ ``_emit_and_gate_benchmark`` → ``build_results_line`` → appended JSONL — so a
future regression that re-introduces ``timings={}`` on visual outcomes fails here.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from typer.testing import CliRunner

from neurotic_docx_bench import cli
from neurotic_docx_bench.emit import jsonl as jsonl_emit
from neurotic_docx_bench.pipeline import redline_key
from neurotic_docx_bench.render.base import RenderReport, RenderResult

runner = CliRunner()


class _StubRenderer:
    """Copies the oracle PDF to the work dir (identity score) and stamps a
    synthetic ``duration_ns`` so the visual_* speed stats are non-zero.
    """

    name = "stub"

    def __init__(self, oracle_pdf: Path) -> None:
        self._oracle = oracle_pdf

    def to_pdfs(self, source_dir, work_dir, *, force=False, jobs=4, timeout=1200.0):
        out_dir = work_dir / "pdf"
        out_dir.mkdir(parents=True, exist_ok=True)
        results: list[RenderResult] = []
        for docx in sorted(source_dir.glob("*.docx")):
            # Candidate PDF name mirrors the oracle: <key>_redline.pdf (no tool token,
            # because the viewer renders the oracle DOCX itself).
            pdf = out_dir / f"{docx.stem}.pdf"
            shutil.copy(self._oracle, pdf)
            results.append(RenderResult(
                source=docx, pdf=pdf, ok=True, duration_ns=250_000_000,  # 250ms
            ))
        return RenderReport(pdf_dir=out_dir, results=results)


def test_visual_redlines_line_carries_render_speed(tmp_path, sample_oracle_pdfs, monkeypatch):
    oracle_pdf = sample_oracle_pdfs[0]
    key = redline_key(oracle_pdf.stem)  # <base>_<next>

    oracle = tmp_path / "oracle"
    oracle.mkdir()
    shutil.copy(oracle_pdf, oracle / oracle_pdf.name)

    # Candidate DOCX source: one file whose stem maps to the oracle key.
    docx_src = tmp_path / "docx"
    docx_src.mkdir()
    (docx_src / f"{key}_redline.docx").write_bytes(b"PK stub docx")

    stub = _StubRenderer(oracle_pdf)
    monkeypatch.setattr(cli, "_renderer", lambda backend, harness=None: stub)

    cfg = tmp_path / "bench.yaml"
    cfg.write_text(
        f"source_of_truth: {oracle}\n"
        f"visual_oracles:\n  visual_redlines: {oracle}\n"
        "runs:\n"
        f"  - {{name: stub-viewer, render: playwright, docx: {docx_src}, "
        f"vendor: stub, unversioned: true, jobs: 1, "
        f"benchmarks: [visual_redlines], harness: {{url: http://x, file_input: '#f'}}}}\n",
    )
    results = tmp_path / "results"
    r = runner.invoke(
        cli.app,
        ["run", "-c", str(cfg), "--results-dir", str(results), "--runs-dir", str(tmp_path / "runs")],
    )
    assert r.exit_code == 0, r.output

    lines = jsonl_emit.read_lines(results / "bench.jsonl")
    vis = [ln for ln in lines if ln.get("benchmark") == "visual_redlines"]
    assert vis, "no visual_redlines line emitted"
    line = vis[-1]
    # The headline assertion: render speed is non-zero (was 0.0 before the fix).
    assert line["overall_mean_speed"] > 0.0
    assert line["overall_median_speed"] > 0.0
    # And the per-doc timings carry render_s (was missing entirely before).
    assert "render_s" in next(iter(line["timings"].values()))
    # The 250ms synthetic duration → 250.0 ms mean.
    assert line["overall_mean_speed"] == 250.0


def test_visual_redlines_line_zero_speed_when_renderer_untimed(tmp_path, sample_oracle_pdfs, monkeypatch):
    """Guard the regression precisely: if a renderer returns ``duration_ns=None``
    (the old Playwright behaviour), the visual_* line's speed stats are 0.0 —
    confirming the test above passes because of the timing, not by accident.
    """
    oracle_pdf = sample_oracle_pdfs[0]
    key = redline_key(oracle_pdf.stem)
    oracle = tmp_path / "oracle"
    oracle.mkdir()
    shutil.copy(oracle_pdf, oracle / oracle_pdf.name)
    docx_src = tmp_path / "docx"
    docx_src.mkdir()
    (docx_src / f"{key}_redline.docx").write_bytes(b"PK stub docx")

    class _UntimedRenderer(_StubRenderer):
        def to_pdfs(self, source_dir, work_dir, *, force=False, jobs=4, timeout=1200.0):
            report = super().to_pdfs(source_dir, work_dir, force=force, jobs=jobs, timeout=timeout)
            # Strip the timing — simulate the pre-fix Playwright backend.
            untimed = [RenderResult(source=r.source, pdf=r.pdf, ok=r.ok, duration_ns=None)
                       for r in report.results]
            return RenderReport(pdf_dir=report.pdf_dir, results=untimed)

    monkeypatch.setattr(cli, "_renderer", lambda backend, harness=None: _UntimedRenderer(oracle_pdf))

    cfg = tmp_path / "bench.yaml"
    cfg.write_text(
        f"source_of_truth: {oracle}\n"
        f"visual_oracles:\n  visual_redlines: {oracle}\n"
        "runs:\n"
        f"  - {{name: stub-viewer, render: playwright, docx: {docx_src}, "
        f"vendor: stub, unversioned: true, jobs: 1, "
        f"benchmarks: [visual_redlines], harness: {{url: http://x, file_input: '#f'}}}}\n",
    )
    results = tmp_path / "results"
    r = runner.invoke(
        cli.app,
        ["run", "-c", str(cfg), "--results-dir", str(results), "--runs-dir", str(tmp_path / "runs")],
    )
    assert r.exit_code == 0, r.output
    lines = jsonl_emit.read_lines(results / "bench.jsonl")
    line = next(ln for ln in lines if ln.get("benchmark") == "visual_redlines")
    assert line["overall_mean_speed"] == 0.0
    assert line["timings"] == {}

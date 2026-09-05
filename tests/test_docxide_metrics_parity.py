"""Parity guard for the vendored docxide-pdf scorer.

``utils/docxide-metrics/`` is a verbatim lift of the metric code in
sverrejb/docxide-pdf (``tests/common/mod.rs``, ``tests/common/text_boundary.rs``).
This test is what keeps it honest, in two layers:

1. **Always** — score five committed corpus PDF pairs (Word's redline render vs the
   LibreOffice render of the same document, both already in git) with the vendored
   binary and require the frozen numbers in ``tests/reference/docxide_page_metrics.json``,
   which were produced by upstream's own ``page-metrics``. Hermetic: no converter,
   no network, no docxide-pdf checkout.
2. **When upstream is present** — re-run upstream's ``page-metrics`` on the same
   pairs and require the frozen file still matches it, so the reference cannot
   quietly drift away from the project it was lifted from. Point
   ``DOCXIDE_PAGE_METRICS`` at the binary, or leave a docxide-pdf checkout beside
   this repo with ``tools/target/release/page-metrics`` built.

Equality is exact. These are deterministic f64 pipelines over identical PNG bytes;
a tolerance here would hide exactly the drift the test exists to catch.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from neurotic_docx_bench import docxide_metrics as dm

REPO_ROOT = Path(__file__).resolve().parents[1]
REFERENCE = REPO_ROOT / "tests" / "reference" / "docxide_page_metrics.json"
WORD_CORPUS = REPO_ROOT / "corpus" / "no_comments_pdf_was_generated_by_word"
WORD_PDFS = WORD_CORPUS / "pdf_redlines_randomized"
SOFFICE_PDFS = WORD_CORPUS / "except_this_pdf_soffice_redlines_randomized"

# Upstream's own binary, for layer 2. Absent in CI and fresh clones — that is fine.
UPSTREAM_ENV = "DOCXIDE_PAGE_METRICS"
UPSTREAM_DEFAULT = REPO_ROOT.parent / "docxide-pdf" / "tools" / "target" / "release" / "page-metrics"

METRIC_KEYS = ("jaccard", "ssim", "text_boundary", "ref_pages", "pages", "scored_pages", "max_break_drift")


def _expected() -> dict[str, dict]:
    return json.loads(REFERENCE.read_text(encoding="utf-8"))


def _pairs() -> list[tuple[str, Path, Path]]:
    return [
        (stem, WORD_PDFS / f"{stem}.pdf", SOFFICE_PDFS / f"{stem}.pdf")
        for stem in sorted(_expected())
    ]


def _upstream_binary() -> Path | None:
    override = os.environ.get(UPSTREAM_ENV)
    if override:
        path = Path(override)
        return path if path.is_file() else None
    return UPSTREAM_DEFAULT if UPSTREAM_DEFAULT.is_file() else None


requires_mutool = pytest.mark.skipif(
    shutil.which("mutool") is None, reason="mutool (mupdf-tools) not installed",
)


@requires_mutool
def test_vendored_scorer_matches_frozen_upstream_numbers(tmp_path: Path) -> None:
    """The vendored crate reproduces upstream's numbers on committed corpus PDFs."""
    expected = _expected()
    pairs = _pairs()
    for _, oracle, candidate in pairs:
        assert oracle.is_file() and candidate.is_file(), f"corpus PDF missing: {oracle} / {candidate}"

    dm.ensure_scorer()
    jobs = tmp_path / "jobs.json"
    out = tmp_path / "scores.json"
    jobs.write_text(
        json.dumps(
            [
                {"stem": stem, "oracle": str(oracle), "candidate": str(candidate)}
                for stem, oracle, candidate in pairs
            ],
        ),
        encoding="utf-8",
    )
    subprocess.run(
        [str(dm.SCORER_BIN), "--jobs", str(jobs), "--scratch", str(tmp_path / "raster"),
         "--out", str(out), "--workers", "2"],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    actual = {row["stem"]: row for row in json.loads(out.read_text(encoding="utf-8"))}

    assert set(actual) == set(expected)
    for stem, want in expected.items():
        got = actual[stem]
        assert got["converted"] is True, stem
        for key in METRIC_KEYS:
            # Upstream emits null for an unscorable metric; the vendored crate omits
            # the key entirely (serde skip_serializing_if). Both mean "no number".
            assert got.get(key) == want.get(key), f"{stem}.{key}: {got.get(key)} != {want.get(key)}"


@requires_mutool
def test_frozen_reference_still_matches_upstream(tmp_path: Path) -> None:
    """The frozen numbers are still what upstream's own page-metrics produces."""
    upstream = _upstream_binary()
    if upstream is None:
        pytest.skip(
            f"upstream page-metrics not found (set ${UPSTREAM_ENV} or build {UPSTREAM_DEFAULT})",
        )
    expected = _expected()
    for stem, oracle, candidate in _pairs():
        ref_png, cand_png = tmp_path / stem / "ref", tmp_path / stem / "cand"
        ref_png.mkdir(parents=True)
        cand_png.mkdir(parents=True)
        for pdf, dest in ((oracle, ref_png), (candidate, cand_png)):
            subprocess.run(
                ["mutool", "draw", "-F", "png", "-r", dm.d2p_dpi(),
                 "-o", str(dest / "page_%03d.png"), str(pdf)],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        proc = subprocess.run(
            [str(upstream), str(oracle), str(candidate), str(ref_png), str(cand_png)],
            check=True, capture_output=True, text=True,
        )
        got = json.loads(proc.stdout)
        for key in METRIC_KEYS:
            assert got.get(key) == expected[stem].get(key), f"{stem}.{key}"


def test_vendored_sources_carry_upstream_provenance() -> None:
    """Both lifted files must say where they came from and that they are not to be edited."""
    for name in ("metrics.rs", "text_boundary.rs"):
        text = (dm.SCORER_DIR / "src" / name).read_text(encoding="utf-8")
        assert "sverrejb/docxide-pdf" in text, name
        assert "Apache-2.0" in text, name
        assert "do not edit the logic" in text, name


def test_scorer_dpi_is_upstreams() -> None:
    """docxide-pdf rasterizes at 150 DPI; the track's numbers are only comparable at that DPI."""
    assert dm.d2p_dpi() == "150"


def test_itt_zeroes_a_failed_convert() -> None:
    """A document with no candidate PDF scores 0 on all three metrics, not NaN or missing."""
    report = dm._tool_report(
        "toy",
        None,
        ["a", "b"],
        {"a": {"stem": "a", "converted": True, "jaccard": 0.5, "ssim": 0.5,
               "text_boundary": 0.5, "ref_pages": 1, "pages": 1, "scored_pages": 1,
               "max_break_drift": 0}},
        [{"doc": "b", "stage": "generate", "error": "boom", "cmd": ["toy"]}],
    )
    assert report["per_doc"]["b"] == {"jaccard": 0.0, "ssim": 0.0, "text_boundary": 0.0}
    assert report["n_scored"] == 1
    assert report["itt_n"] == 2
    assert report["failures"] == 1
    assert report["metrics"]["jaccard"]["mean"] == 25.0

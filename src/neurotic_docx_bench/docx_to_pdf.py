"""DOCX→PDF evaluation track: soffice oracles vs an independent converter.

Scores candidate PDFs against committed LibreOffice ``pdf_source`` oracles using
the shipped visual pipeline (``score_folders_plain`` / ``match_by_plain_stem``).
Does not wrap soffice as the converter-under-test and does not touch
``score.py`` / ``diff.py`` / ``raster.py``.
"""

from __future__ import annotations

import json
import math
import statistics
import subprocess
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from neurotic_docx_bench import pipeline

REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS = REPO_ROOT / "corpus" / "word_based"
DOCX_SOURCE = CORPUS / "docx_source"
PDF_SOURCE = CORPUS / "pdf_source"
FIXTURE_LIST = CORPUS / "docx_to_pdf_fixtures.txt"

REQUIRED_FEATURES = frozenset(
    {"body_text", "table", "numbering", "image", "header_or_footer"},
)

DEFAULT_CONVERTER = REPO_ROOT.parent / "jubarte-redlines" / "target" / "release" / "jubarte"


@dataclass(frozen=True)
class Fixture:
    """One pinned DOCX plus its soffice oracle PDF, keyed by plain stem."""

    stem: str
    docx: Path
    oracle: Path


def load_fixture_stems(path: Path = FIXTURE_LIST) -> list[str]:
    """Read the pinned 100-stem list (comments and blanks ignored)."""
    stems: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        stems.append(line)
    return stems


def load_fixtures(path: Path = FIXTURE_LIST) -> list[Fixture]:
    """Resolve each pinned stem to its source DOCX and soffice oracle PDF."""
    fixtures: list[Fixture] = []
    for stem in load_fixture_stems(path):
        fixtures.append(
            Fixture(
                stem=stem,
                docx=DOCX_SOURCE / f"{stem}.docx",
                oracle=PDF_SOURCE / f"{stem}.pdf",
            ),
        )
    return fixtures


def docx_features(docx: Path) -> set[str]:
    """Feature tags from package XML (not from the redline coverage map)."""
    tags: set[str] = set()
    with zipfile.ZipFile(docx) as zf:
        names = set(zf.namelist())
        blobs: list[str] = []
        if "word/document.xml" in names:
            blobs.append(zf.read("word/document.xml").decode("utf-8", "replace"))
        for name in names:
            if name.startswith("word/header") and name.endswith(".xml"):
                tags.add("header")
                blobs.append(zf.read(name).decode("utf-8", "replace"))
            elif name.startswith("word/footer") and name.endswith(".xml"):
                tags.add("footer")
                blobs.append(zf.read(name).decode("utf-8", "replace"))
        xml = "\n".join(blobs)
    if "<w:t" in xml or "</w:t>" in xml:
        tags.add("body_text")
    if "<w:tbl" in xml:
        tags.add("table")
    if "<w:numPr" in xml or "<w:ilvl" in xml:
        tags.add("numbering")
    if "<w:drawing" in xml or "<a:blip" in xml or "<w:pict" in xml or "<v:imagedata" in xml:
        tags.add("image")
    if "header" in tags or "footer" in tags:
        tags.add("header_or_footer")
    return tags


def feature_coverage(fixtures: Iterable[Fixture]) -> set[str]:
    """Union of :func:`docx_features` across ``fixtures``."""
    found: set[str] = set()
    for item in fixtures:
        found |= docx_features(item.docx)
    return found


def aggregate(scores: dict[str, float]) -> dict[str, float | int]:
    """Mean / median / min / max / n over finite per-document scores."""
    vals = [v for v in scores.values() if isinstance(v, (int, float)) and math.isfinite(v)]
    if not vals:
        return {"n": 0}
    return {
        "mean": round(statistics.mean(vals), 4),
        "median": round(statistics.median(vals), 4),
        "min": round(min(vals), 4),
        "max": round(max(vals), 4),
        "n": len(vals),
    }


def _overall_map(full: dict[str, pipeline.ScoreResult]) -> dict[str, float]:
    return {key: pipeline.overall_from_result(result) for key, result in full.items()}


def score_folder_pair(
    oracle_dir: Path,
    candidate_dir: Path,
    work_dir: Path,
    *,
    dpi: int = 144,
    jobs: int = 8,
) -> dict[str, pipeline.ScoreResult]:
    """Score two PDF folders with the shipped plain-stem visual path."""
    return pipeline.score_folders_plain(
        oracle_dir, candidate_dir, work_dir, dpi=dpi, jobs=jobs,
    )


def convert_fixture(converter: Path, fixture: Fixture, dest_pdf: Path) -> None:
    """Launch the independent converter for one fixture (not soffice)."""
    dest_pdf.parent.mkdir(parents=True, exist_ok=True)
    cmd = [str(converter), "convert", str(fixture.docx), "-o", str(dest_pdf), "--force"]
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if proc.returncode != 0 or not dest_pdf.is_file() or dest_pdf.stat().st_size == 0:
        err = (proc.stderr or proc.stdout or "").strip() or f"exit {proc.returncode}"
        raise RuntimeError(f"converter failed for {fixture.stem}: {err}")
    header = dest_pdf.read_bytes()[:5]
    if header != b"%PDF-":
        raise RuntimeError(f"converter output for {fixture.stem} is not a PDF ({header!r})")


def convert_fixtures(converter: Path, fixtures: list[Fixture], dest_dir: Path) -> Path:
    """Convert every fixture into ``dest_dir/<stem>.pdf``."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    total = len(fixtures)
    for idx, item in enumerate(fixtures, 1):
        convert_fixture(converter, item, dest_dir / f"{item.stem}.pdf")
        if idx == total or idx % 10 == 0:
            print(f"converted {idx}/{total}", flush=True)
    return dest_dir


def stage_oracles(fixtures: list[Fixture], dest_dir: Path) -> Path:
    """Copy soffice oracles into ``dest_dir`` under their plain stems."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    for item in fixtures:
        target = dest_dir / f"{item.stem}.pdf"
        if target.exists() or target.is_symlink():
            target.unlink()
        try:
            if _same_fs(item.oracle, dest_dir):
                target.hardlink_to(item.oracle)
            else:
                _copy(item.oracle, target)
        except OSError:
            _copy(item.oracle, target)
    return dest_dir


def _same_fs(src: Path, dest_dir: Path) -> bool:
    try:
        return src.stat().st_dev == dest_dir.stat().st_dev
    except OSError:
        return False


def _copy(src: Path, dest: Path) -> None:
    dest.write_bytes(src.read_bytes())


def run_eval(
    converter: Path,
    json_out: Path,
    *,
    jobs: int = 8,
    dpi: int = 144,
    work_dir: Path | None = None,
    limit: int | None = None,
    fixtures: list[Fixture] | None = None,
) -> dict:
    """Convert the pin list, score soffice-vs-self and converter-vs-soffice.

    Returns the report dict and writes it to ``json_out``. Oracle PDFs are reused
    from ``pdf_source`` (not re-rendered).
    """
    items = list(fixtures if fixtures is not None else load_fixtures())
    if limit is not None:
        items = items[:limit]
    if not items:
        raise RuntimeError("no docx-to-pdf fixtures to evaluate")

    root = work_dir if work_dir is not None else json_out.parent / "docx_to_pdf_work"
    oracle_dir = stage_oracles(items, root / "oracle")
    self_dir = stage_oracles(items, root / "soffice_self")
    cand_dir = convert_fixtures(converter, items, root / "candidate")

    print(f"scoring soffice-self ({len(items)} docs)", flush=True)
    self_full = score_folder_pair(oracle_dir, self_dir, root / "score_self", dpi=dpi, jobs=jobs)
    print(f"scoring converter-vs-soffice ({len(items)} docs)", flush=True)
    cand_full = score_folder_pair(oracle_dir, cand_dir, root / "score_cand", dpi=dpi, jobs=jobs)
    self_scores = _overall_map(self_full)
    cand_scores = _overall_map(cand_full)

    report = {
        "track": "docx_to_pdf",
        "generated_at": datetime.now(UTC).isoformat(),
        "converter": str(converter),
        "n": len(items),
        "stems": [item.stem for item in items],
        "soffice_self": {
            "per_doc": self_scores,
            "aggregate": aggregate(self_scores),
        },
        "converter_vs_soffice": {
            "per_doc": cand_scores,
            "aggregate": aggregate(cand_scores),
        },
    }
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report

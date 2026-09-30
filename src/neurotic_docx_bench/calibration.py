"""Calibration candidates for the fidelity tables.

- ``oracle-identity``: Word's own redline DOCX, renamed as if a tool produced it. Through
  the candidate pipeline it must score 100 (the renderer is deterministic: see
  results/noise_floor.json). It anchors the top of every table.
- ``null-baseline``: the base DOCX submitted unchanged. It is the score a tool gets for
  doing nothing, the floor every redline tool must beat.

Both run through the normal ``bench run`` driver as ``docx:`` runs so their lines carry
the same document set, renderer, scorer and hardware stamps as every vendor's.
"""

from __future__ import annotations

import csv
import shutil
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

Kind = Literal["oracle-identity", "null-baseline"]
KINDS: tuple[Kind, ...] = ("oracle-identity", "null-baseline")


class BuildReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: str
    out_dir: Path
    written: int


def _oracle_docx(row: dict[str, str], redline_dirs: Sequence[Path], stem: str) -> Path:
    for column in ("redline_docx_word", "redline_docx"):
        name = (row.get(column) or "").strip()
        if not name or name == "MISSING":
            continue
        for d in redline_dirs:
            p = Path(d) / name
            if p.is_file():
                return p
    raise FileNotFoundError(
        f"no oracle redline DOCX for pair {stem} under {list(redline_dirs)}"
    )


def _base_docx(row: dict[str, str], source_dir: Path, stem: str) -> Path:
    name = (row.get("docx_source_base") or "").strip()
    p = Path(source_dir) / name if name else None
    if p is None or not p.is_file():
        raise FileNotFoundError(
            f"no base DOCX {name!r} for pair {stem} under {source_dir}"
        )
    return p


def build_candidates(
    kind: Kind,
    *,
    manifest: Path,
    source_dir: Path,
    redline_dirs: Sequence[Path],
    out_dir: Path,
) -> BuildReport:
    """Copy one candidate DOCX per manifest pair into ``out_dir`` as
    ``<pair>_<kind>_redline.docx`` (the filename shape the scorer keys on)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    with Path(manifest).open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            stem = (row.get("pair_stem") or "").strip()
            if not stem:
                continue
            src = (
                _oracle_docx(row, redline_dirs, stem)
                if kind == "oracle-identity"
                else _base_docx(row, source_dir, stem)
            )
            shutil.copyfile(src, out_dir / f"{stem}_{kind}_redline.docx")
            written += 1
    return BuildReport(kind=kind, out_dir=out_dir, written=written)


_SHARED_KEYS = (
    "source_of_truth",
    "extra_oracle_dirs",
    "holdout_list",
    "scoring",
    "corpora",
    "visual_oracles",
)


def calibration_config(
    base: dict[str, Any], *, oracle_dir: Path, null_dir: Path
) -> dict[str, Any]:
    """A bench.yaml document with the shared environment of ``base`` and only the two
    calibration runs. Accepted/roundtrip settings are left out on purpose: calibration
    covers script_redlines."""
    doc: dict[str, Any] = {k: base[k] for k in _SHARED_KEYS if k in base}
    doc["runs"] = [
        {
            "name": kind,
            "render": "soffice",
            "docx": str(d),
            "vendor": kind,
            "benchmarks": ["script_redlines"],
            "unversioned": True,
        }
        for kind, d in (("oracle-identity", oracle_dir), ("null-baseline", null_dir))
    ]
    return doc

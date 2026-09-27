"""Document sets: the fixed denominator of every benchmark.

A benchmark's document set is the key set of its ORACLE directory (minus the sealed
holdout for a normal run). Its ``docset_id`` is a 12-hex SHA-256 of the sorted keys,
so two runs are comparable exactly when they share it, whichever oracle PDFs were
re-rendered in between (that is what ``corpus_revision`` tracks, separately).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict

from neurotic_docx_bench import pipeline

if TYPE_CHECKING:
    from neurotic_docx_bench.config import BenchConfig

KeyKind = Literal["redline", "accepted", "plain"]

KEY_KIND: dict[str, KeyKind] = {
    "script_redlines": "redline",
    "accepted_changes": "accepted",
    "roundtrip": "plain",
    "visual_rendering": "plain",
    "visual_redlines": "redline",
    "visual_accepted_changes": "accepted",
}

ROUNDTRIP_CORPUS = Path("corpus/word_based/word_working_roundtrip")
DEFAULT_DOCSETS_PATH = Path("results/docsets.json")
MISSING_OUTPUT_STAGE = "missing_output"
MISSING_OUTPUT_ERROR = "no candidate output for this document"
_SUFFIXES = {".pdf", ".docx"}


class DocSet(BaseModel):
    model_config = ConfigDict(frozen=True)

    benchmark: str
    keys: tuple[str, ...]
    id: str
    holdout_mode: str | None = None

    @property
    def n(self) -> int:
        return len(self.keys)


def keys_in_dir(directory: Path, kind: KeyKind) -> set[str]:
    stems = {p.stem for p in Path(directory).iterdir() if p.suffix.lower() in _SUFFIXES}
    if kind == "redline":
        return {pipeline.oracle_pair_key(s) for s in stems if pipeline.is_redline(s)}
    if kind == "accepted":
        return {pipeline.accepted_key(s) for s in stems}
    # "plain": the same key the roundtrip and visual_rendering matchers use
    # (pipeline._index_plain: lowercased stem, no suffix stripping).
    return {s.lower() for s in stems}


def docset_id(keys: Iterable[str]) -> str:
    joined = "\n".join(sorted(set(keys))).encode("utf-8")
    return hashlib.sha256(joined).hexdigest()[:12]


def benchmark_docset(
    benchmark: str,
    oracle_dirs: Sequence[Path],
    *,
    holdout: set[str],
    holdout_mode: str | None,
) -> DocSet:
    kind = KEY_KIND[benchmark]
    keys: set[str] = set()
    for d in oracle_dirs:
        if Path(d).is_dir():
            keys |= keys_in_dir(Path(d), kind)
    if holdout_mode == "excluded":
        keys -= holdout
    elif holdout_mode == "only":
        keys &= holdout
    ordered = tuple(sorted(keys))
    return DocSet(
        benchmark=benchmark,
        keys=ordered,
        id=docset_id(ordered),
        holdout_mode=holdout_mode,
    )


def oracle_dirs_for(cfg: BenchConfig, benchmark: str) -> list[Path]:
    """Oracle directories that define ``benchmark``'s document set, from a BenchConfig."""
    if benchmark == "script_redlines":
        return [Path(cfg.source_of_truth), *(Path(p) for p in cfg.extra_oracle_dirs)]
    if benchmark == "accepted_changes":
        return [Path(cfg.accepted_ground_truth)] if cfg.accepted_ground_truth else []
    if benchmark == "roundtrip":
        return [ROUNDTRIP_CORPUS]
    visual = cfg.visual_oracles or {}
    return [Path(visual[benchmark])] if benchmark in visual else []


def missing_output_failures(
    keys: Iterable[str],
    scores: Mapping[str, float],
    failures: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Failure records for documents in the set that neither scored nor failed."""
    seen = set(scores) | {str(f.get("doc", "")) for f in failures}
    return [
        {"doc": k, "stage": MISSING_OUTPUT_STAGE, "error": MISSING_OUTPUT_ERROR}
        for k in sorted(set(keys) - seen)
    ]


class Restriction(BaseModel):
    """Scores, per-doc results and failures limited to a document set."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    scores: dict[str, float]
    per_doc: dict[str, object] | None
    failures: list[dict[str, str]]
    dropped_scores: tuple[str, ...]
    dropped_failures: tuple[str, ...]


def restrict_to_docset(
    keys: Iterable[str],
    scores: Mapping[str, float],
    per_doc: Mapping[str, object] | None,
    failures: Sequence[Mapping[str, str]],
) -> Restriction:
    """Keep only documents in the set, then add a missing-output failure for every
    document of the set that neither scored nor failed. After this, the ITT pool is
    exactly the document set: ``len(scores) + n_failed_docs == len(keys)``."""
    keyset = set(keys)
    kept_scores = {k: float(v) for k, v in scores.items() if k in keyset}
    kept_per_doc = (
        {k: v for k, v in per_doc.items() if k in keyset}
        if per_doc is not None
        else None
    )
    kept_failures = [dict(f) for f in failures if str(f.get("doc", "")) in keyset]
    kept_failures.extend(missing_output_failures(keyset, kept_scores, kept_failures))
    return Restriction(
        scores=kept_scores,
        per_doc=kept_per_doc,
        failures=kept_failures,
        dropped_scores=tuple(sorted(k for k in scores if k not in keyset)),
        dropped_failures=tuple(
            sorted(
                {
                    str(f.get("doc", ""))
                    for f in failures
                    if str(f.get("doc", "")) not in keyset
                }
            )
        ),
    )


def write_docsets(
    path: Path, docsets: Sequence[DocSet], *, source_dirs: Mapping[str, list[str]]
) -> None:
    existing = load_docsets(path) if Path(path).is_file() else {}
    now = datetime.now(UTC).isoformat()
    for d in docsets:
        existing[d.id] = {
            "benchmark": d.benchmark,
            "n": d.n,
            "holdout_mode": d.holdout_mode,
            "source_dirs": list(source_dirs.get(d.id, [])),
            "computed_at": now,
        }
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(existing, indent="\t", sort_keys=True) + "\n")


def load_docsets(path: Path) -> dict[str, dict]:
    if not Path(path).is_file():
        return {}
    data = json.loads(Path(path).read_text())
    return {str(k): dict(v) for k, v in data.items()} if isinstance(data, dict) else {}

"""Document sets: the fixed denominator of every benchmark.

A benchmark's document set is the key set of its ORACLE directory (minus the sealed
holdout for a normal run). Its ``docset_id`` is a 12-hex SHA-256 of the sorted keys,
so two runs are comparable exactly when they share it, whichever oracle PDFs were
re-rendered in between (that is what ``corpus_revision`` tracks, separately).

The *gate set* of a benchmark is a fixed 50-document subset of its document set,
allocated across the oracle directories in proportion to their size and picked
inside each directory by a hash of the key, so it is deterministic and does not
favour the alphabetical head of a directory. It has its own docset id and records
which full set it gates (``gate_of``).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Collection, Iterable, Mapping, Sequence
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
GATE_N = 50
GATE_SEED = "gate"
_SUFFIXES = {".pdf", ".docx"}


class DocSet(BaseModel):
    model_config = ConfigDict(frozen=True)

    benchmark: str
    keys: tuple[str, ...]
    id: str
    holdout_mode: str | None = None
    # The full document set this one is the gate of; None for a full set.
    gate_of: str | None = None

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


def benchmark_strata(
    oracle_dirs: Sequence[Path], kind: KeyKind, keys: Iterable[str]
) -> dict[str, list[str]]:
    """The document set's keys grouped by the oracle directory that holds them
    (a key found in several directories counts for the first)."""
    wanted = set(keys)
    strata: dict[str, list[str]] = {}
    seen: set[str] = set()
    for d in oracle_dirs:
        if not Path(d).is_dir():
            continue
        mine = sorted((keys_in_dir(Path(d), kind) & wanted) - seen)
        seen |= set(mine)
        strata[str(d)] = mine
    return strata


def _pick_order(key: str, seed: str) -> str:
    return hashlib.sha256(f"{seed}:{key}".encode()).hexdigest()


def gate_subset(
    strata: Mapping[str, Iterable[str]], *, n: int | None = None, seed: str = GATE_SEED
) -> tuple[str, ...]:
    """``n`` keys (default ``GATE_N``, read at call time) drawn across strata by
    largest-remainder proportional allocation, each stratum contributing its keys
    in hashed order. Every key is returned when there are at most ``n``.
    Deterministic; sorted for stable ids."""
    if n is None:
        n = GATE_N
    pools = {name: sorted(set(ks)) for name, ks in strata.items()}
    total = sum(len(ks) for ks in pools.values())
    if total <= n:
        return tuple(sorted(k for ks in pools.values() for k in ks))
    quota: dict[str, int] = {}
    remainders: list[tuple[float, str]] = []
    for name, ks in pools.items():
        exact = len(ks) * n / total
        quota[name] = int(exact)
        remainders.append((exact - int(exact), name))
    short = n - sum(quota.values())
    for _, name in sorted(remainders, key=lambda t: (-t[0], t[1]))[:short]:
        quota[name] += 1
    chosen: list[str] = []
    for name, ks in pools.items():
        ordered = sorted(ks, key=lambda k: _pick_order(k, seed))
        chosen.extend(ordered[: quota[name]])
    return tuple(sorted(chosen))


def gate_docset(
    full: DocSet, strata: Mapping[str, Iterable[str]], *, n: int | None = None
) -> DocSet:
    """The gate set of ``full``: its own id, ``gate_of`` pointing back."""
    allowed = set(full.keys)
    inside = {name: [k for k in ks if k in allowed] for name, ks in strata.items()}
    keys = gate_subset(inside, n=n)
    return DocSet(
        benchmark=full.benchmark,
        keys=keys,
        id=docset_id(keys),
        holdout_mode=full.holdout_mode,
        gate_of=full.id,
    )


def stem_in_keys(stem: str, keys: Collection[str], tool: str | None = None) -> bool:
    """Whether a candidate file stem names a document in ``keys``: through its
    redline pair key (``<base>_<next>_<tool>_redline``), its accepted-changes key,
    or its plain lowercase stem."""
    return (
        pipeline.redline_key(stem, tool) in keys
        or pipeline.accepted_key(stem) in keys
        or stem.lower() in keys
    )


def gate_docset_id(
    docsets: Mapping[str, Mapping[str, object]], full_id: str
) -> str | None:
    """The recorded gate set of ``full_id``, or None when none was recorded."""
    for gid, entry in sorted(docsets.items()):
        if entry.get("gate_of") == full_id:
            return gid
    return None


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
        entry: dict[str, object] = {
            "benchmark": d.benchmark,
            "n": d.n,
            "holdout_mode": d.holdout_mode,
            "source_dirs": list(
                source_dirs.get(d.id, source_dirs.get(d.gate_of or "", []))
            ),
            "computed_at": now,
        }
        if d.gate_of:
            entry["gate_of"] = d.gate_of
        existing[d.id] = entry
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(existing, indent="\t", sort_keys=True) + "\n")


def load_docsets(path: Path) -> dict[str, dict]:
    if not Path(path).is_file():
        return {}
    data = json.loads(Path(path).read_text())
    return {str(k): dict(v) for k, v in data.items()} if isinstance(data, dict) else {}

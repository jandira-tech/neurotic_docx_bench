"""Oracle checksum manifest (PR4): refuse to score against a drifted oracle.

The committed oracle PDFs are the benchmark's ground truth; an accidental
regeneration with a different LibreOffice build (or a stray copy) silently changes
every score. The manifest pins SHA-256 of every oracle artifact + the mapping CSVs;
``bench run`` verifies it before any work and aborts on drift.

Layout convention: the manifest lives at ``<corpus root>/oracle_manifest.json`` where
the corpus root is ``source_of_truth.parent``. Covered inputs: every ``*.pdf`` in the
oracle dirs (source_of_truth, accepted ground truth, visual oracles — those that are
directories under any root) plus every ``centralized_mapping*.csv`` at the corpus
root. CI regenerates oracles in-image (renderer-agnostic invariant) and therefore
re-writes the manifest right after regeneration — the gate then still protects the
rest of the CI run.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ManifestDrift:
    changed: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    extra: list[str] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return not (self.changed or self.missing or self.extra)

    def summary(self) -> str:
        parts = []
        for label, items in (("changed", self.changed), ("missing", self.missing), ("extra", self.extra)):
            if items:
                shown = ", ".join(items[:5]) + ("…" if len(items) > 5 else "")
                parts.append(f"{len(items)} {label} ({shown})")
        return "; ".join(parts) if parts else "clean"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _covered_files(corpus_root: Path, oracle_dirs: list[Path]) -> list[Path]:
    files: set[Path] = set()
    for d in oracle_dirs:
        if d.is_dir():
            files.update(d.glob("*.pdf"))
    files.update(corpus_root.glob("centralized_mapping*.csv"))
    return sorted(files)


def build_manifest(corpus_root: Path, oracle_dirs: list[Path]) -> dict[str, str]:
    """``{relpath-from-corpus-root: sha256}``, sorted by path."""
    manifest: dict[str, str] = {}
    for f in _covered_files(corpus_root, oracle_dirs):
        try:
            rel = f.relative_to(corpus_root).as_posix()
        except ValueError:
            rel = f.as_posix()
        manifest[rel] = _sha256(f)
    return dict(sorted(manifest.items()))


def write_manifest(path: Path, manifest: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent="\t", sort_keys=True) + "\n")


def load_manifest(path: Path) -> dict[str, str] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else None


def verify_manifest(
    manifest_path: Path, corpus_root: Path, oracle_dirs: list[Path],
) -> ManifestDrift:
    """Compare disk state against the committed manifest.

    ``changed``: hash differs; ``missing``: in manifest, absent on disk; ``extra``:
    on disk (in a covered location), not in the manifest.
    """
    expected = load_manifest(manifest_path) or {}
    actual = build_manifest(corpus_root, oracle_dirs)
    changed = sorted(k for k in expected.keys() & actual.keys() if expected[k] != actual[k])
    missing = sorted(expected.keys() - actual.keys())
    extra = sorted(actual.keys() - expected.keys())
    return ManifestDrift(changed=changed, missing=missing, extra=extra)


def default_manifest_path(source_of_truth: Path) -> Path:
    return source_of_truth.parent / "oracle_manifest.json"


def oracle_dirs_from_config(cfg: object) -> list[Path]:
    """Unique existing oracle directories declared by a BenchConfig."""
    dirs: list[Path] = [cfg.source_of_truth]  # type: ignore[attr-defined]
    accepted = getattr(cfg, "accepted_ground_truth", None)
    if accepted:
        dirs.append(Path(accepted))
    for p in (getattr(cfg, "visual_oracles", None) or {}).values():
        dirs.append(Path(p))
    seen: set[Path] = set()
    out: list[Path] = []
    for d in dirs:
        if d and d.is_dir() and d not in seen:
            seen.add(d)
            out.append(d)
    return out

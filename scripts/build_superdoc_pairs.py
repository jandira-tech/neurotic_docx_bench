#!/usr/bin/env python3
"""Build the superdoc Word-redline subcorpus: 400 deterministic base→next pairs.

Plan reference: ``plans/agent-execution-plan.md`` Chapter 2.2 and the teaching
document ``plans/word-redline-automation.md``.

Pure-function core (``inventory`` → ``build_pairs`` → ``mapping_rows`` /
``provenance_rows``) so the whole pairing spec is testable without Microsoft
Word or the fixture repo; ``main`` is the only part that touches the disk.

Two CSVs come out of this, deliberately:

* ``centralized_mapping.csv`` — the 12-column schema the bench already consumes
  (``scripts/generate-native-redlines.ts`` reads ``base``/``next``; the scorer
  keys oracle PDFs on ``<base>_<next>_redline.pdf``). Same shape as
  ``corpus/word_based/centralized_mapping*.csv`` so no bench code changes.
* ``pair_provenance.csv`` — the map of where each pair came from in the source
  pool, carrying SHA-256 of base, next and (after Word runs) the redline.

Usage::

    uv run python scripts/build_superdoc_pairs.py            # build everything
    uv run python scripts/build_superdoc_pairs.py --dry-run  # manifests only
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import random
import re
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import NamedTuple

# Default source pool: the SuperDoc fixture corpus vendored by docx-validate.
DEFAULT_POOL_ROOT = Path(
    "/Users/arthrod/temp/T/docx-validate/tests/fixtures/external/superdoc",
)
DEFAULT_OUT_ROOT = Path(__file__).resolve().parents[1] / "corpus" / "word_redlines_superdoc"
DEFAULT_INVENTORY_CSV = Path(__file__).resolve().parents[1] / "plans" / "superdoc-source-pool.sha256.csv"

TARGET_PAIRS = 400
PAIR_SEED = 0x5D0C400
HOLDOUT_SEED = 0xD0C5 + 1
HOLDOUT_SIZE = 20

# Buckets that can never be automated: Word blocks on a password dialog forever.
EXCLUDED_BUCKETS = frozenset({"encryption"})

# macOS caps a filename at 255 bytes and the bench appends
# ``_<tool>_redline.docx`` to ``<base>_<next>`` — 60 per side leaves ample room.
MAX_STEM = 60
_HASH_LEN = 8

MAPPING_FIELDS = [
    "pair_stem",
    "base",
    "next",
    "origin",
    "docx_source_base",
    "docx_source_next",
    "redline_docx",
    "redline_docx_word",
    "accepted_docx",
    "pdf_redline",
    "pdf_accepted",
    "missing",
]

PROVENANCE_FIELDS = [
    "pair_id",
    "base_rel",
    "next_rel",
    "base_sha256",
    "next_sha256",
    "redline_docx",
    "redline_sha256",
    "status",
    "error",
]

INVENTORY_FIELDS = ["relative_path", "sha256", "bytes"]


class PoolFile(NamedTuple):
    relative_path: str
    sha256: str
    size: int


class Pair(NamedTuple):
    base: PoolFile
    next: PoolFile
    kind: str  # "chain" (path-sorted neighbours) | "cross" (seeded draw)


# --------------------------------------------------------------------------- #
# naming
# --------------------------------------------------------------------------- #


def bucket_of(relative_path: str) -> str:
    parts = PurePosixPath(relative_path).parts
    return parts[0] if len(parts) > 1 else ""


def flat_stem(relative_path: str) -> str:
    """``<bucket>__<filestem>_<pathhash>`` — a flat, injective, filesystem-safe name.

    The bucket prefix is load-bearing: ``numwords.docx`` and ``basic-list.docx``
    each exist in two buckets, and the bench's source dir is flat.

    The 8-hex path-hash suffix is NOT decoration and is NOT conditional on
    length. Sanitizing ``[^A-Za-z0-9_]`` to ``_`` is lossy, and the pool really
    contains ``sd-1494-table-left-indent.docx`` *and*
    ``sd_1494_table_left_indent.docx`` in the same bucket — without the suffix
    they collapse to one name and one file silently stands in for the other,
    corrupting the ground truth. Hashing the PATH (not the content) keeps the
    6 duplicate-content files distinct too.

    Two invariants fall out of the suffix for free: no stem can end in ``_word``
    or ``_redline`` (``pipeline.oracle_pair_key`` / ``redline_key`` would eat
    them and mis-key the oracle), because the last 8 chars are always hex.
    """
    path = PurePosixPath(relative_path)
    bucket = bucket_of(relative_path)
    raw = f"{bucket}__{path.stem}" if bucket else path.stem
    body = re.sub(r"[^A-Za-z0-9_]", "_", raw)[: MAX_STEM - _HASH_LEN - 1]
    digest = hashlib.sha256(relative_path.encode()).hexdigest()[:_HASH_LEN]
    return f"{body}_{digest}"


def pair_stem(pair: Pair) -> str:
    return f"{flat_stem(pair.base.relative_path)}_{flat_stem(pair.next.relative_path)}"


# --------------------------------------------------------------------------- #
# inventory
# --------------------------------------------------------------------------- #


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inventory(root: Path) -> list[PoolFile]:
    """Every usable ``.docx`` under ``root``, path-sorted and content-hashed.

    Excluded: Word owner/lock stubs (``~$*``, not documents at all) and the
    encrypted bucket (a password dialog would wedge the unattended run).
    """
    files: list[PoolFile] = []
    for path in sorted(root.rglob("*.docx")):
        rel = path.relative_to(root).as_posix()
        if path.name.startswith("~$"):
            continue
        if bucket_of(rel) in EXCLUDED_BUCKETS:
            continue
        files.append(PoolFile(rel, sha256_file(path), path.stat().st_size))
    files.sort(key=lambda p: p.relative_path)
    return files


# --------------------------------------------------------------------------- #
# pairing
# --------------------------------------------------------------------------- #


def drop_unreadable(pool: list[PoolFile], unreadable: set[str]) -> list[PoolFile]:
    """Remove sources Word cannot read, identified by STAGED filename.

    These have to leave the pool entirely rather than just failing their own
    pair: opening one leaves Word silently returning empty documents for every
    later open in the same session, so a single survivor can invalidate a whole
    batch. ``scripts/word_compare_driver.sh --screen`` produces the list.
    """
    if not unreadable:
        return pool
    return [p for p in pool if f"{flat_stem(p.relative_path)}.docx" not in unreadable]


def _feasible_ordered_pairs(pool: list[PoolFile]) -> int:
    """Distinct ordered (base, next) pairs with different paths AND different content."""
    total = 0
    for a in pool:
        for b in pool:
            if a.relative_path != b.relative_path and a.sha256 != b.sha256:
                total += 1
    return total


def build_pairs(
    pool: list[PoolFile],
    target: int = TARGET_PAIRS,
    seed: int = PAIR_SEED,
) -> list[Pair]:
    """Exactly ``target`` deterministic pairs: bucket chains first, then seeded draws.

    Chain pairs come from path-sorted neighbours inside one bucket — related
    fixtures, so the diffs are realistic rather than whole-document rewrites.
    Cross pairs top up to ``target`` from a seeded PRNG.

    Never emitted: a file with itself, two files with equal SHA-256 (Word's
    compare of identical content produces an empty redline), or a repeat of an
    already-emitted ordered pair.
    """
    ordered = sorted(pool, key=lambda p: p.relative_path)
    feasible = _feasible_ordered_pairs(ordered)
    if feasible < target:
        raise ValueError(
            f"cannot reach {target} pairs from {len(ordered)} files: "
            f"only {feasible} distinct ordered pairs with differing content exist",
        )

    pairs: list[Pair] = []
    seen: set[tuple[str, str]] = set()

    def emit(base: PoolFile, nxt: PoolFile, kind: str) -> bool:
        if base.relative_path == nxt.relative_path or base.sha256 == nxt.sha256:
            return False
        key = (base.relative_path, nxt.relative_path)
        if key in seen:
            return False
        seen.add(key)
        pairs.append(Pair(base, nxt, kind))
        return True

    for left, right in zip(ordered, ordered[1:], strict=False):
        if len(pairs) >= target:
            return pairs
        if bucket_of(left.relative_path) != bucket_of(right.relative_path):
            continue
        emit(left, right, "chain")

    rng = random.Random(seed)
    size = len(ordered)
    # Generous cap: the feasibility check above already proves termination is
    # possible, this only stops a pathological pool from spinning forever.
    attempts_left = max(1_000_000, target * 1000)
    while len(pairs) < target:
        attempts_left -= 1
        if attempts_left <= 0:  # pragma: no cover - unreachable given `feasible`
            raise ValueError(f"cannot reach {target} pairs: exhausted draw attempts")
        emit(ordered[rng.randrange(size)], ordered[rng.randrange(size)], "cross")

    return pairs


def build_holdout(pairs: list[Pair], size: int = HOLDOUT_SIZE, seed: int = HOLDOUT_SEED) -> list[str]:
    """Seal ``size`` pair keys as the overfitting detector for this subcorpus."""
    rng = random.Random(seed)
    return sorted(rng.sample([pair_stem(p) for p in pairs], size))


# --------------------------------------------------------------------------- #
# manifest rows
# --------------------------------------------------------------------------- #


def mapping_rows(pairs: list[Pair]) -> list[dict[str, str]]:
    """Rows in the 12-column schema the bench already consumes.

    ``accepted_docx``/``pdf_accepted`` are MISSING for the same reason the
    randomized chain corpus leaves them missing: this subcorpus supplies the
    redline oracle only, not the accepted-changes oracle.
    """
    rows: list[dict[str, str]] = []
    for pair in pairs:
        base = flat_stem(pair.base.relative_path)
        nxt = flat_stem(pair.next.relative_path)
        stem = f"{base}_{nxt}"
        rows.append(
            {
                "pair_stem": stem,
                "base": base,
                "next": nxt,
                "origin": f"superdoc_{pair.kind}",
                "docx_source_base": f"{base}.docx",
                "docx_source_next": f"{nxt}.docx",
                "redline_docx": f"{stem}_redline.docx",
                "redline_docx_word": "",
                "accepted_docx": "MISSING",
                "pdf_redline": f"{stem}_redline.pdf",
                "pdf_accepted": "MISSING",
                "missing": "accepted_docx; pdf_accepted",
            },
        )
    return rows


def provenance_rows(pairs: list[Pair]) -> list[dict[str, str]]:
    """The map: pair → source paths in the pool → three SHA-256s → status."""
    rows: list[dict[str, str]] = []
    for pair in pairs:
        stem = pair_stem(pair)
        rows.append(
            {
                "pair_id": stem,
                "base_rel": pair.base.relative_path,
                "next_rel": pair.next.relative_path,
                "base_sha256": pair.base.sha256,
                "next_sha256": pair.next.sha256,
                "redline_docx": f"{stem}_redline.docx",
                "redline_sha256": "",
                "status": "pending",
                "error": "",
            },
        )
    return rows


# --------------------------------------------------------------------------- #
# disk
# --------------------------------------------------------------------------- #


def _clone(src: Path, dst: Path) -> None:
    """APFS clonefile (O(1), zero bytes copied); plain copy elsewhere."""
    try:
        subprocess.run(["cp", "-c", str(src), str(dst)], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        shutil.copy2(src, dst)


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def stage_sources(pool: list[PoolFile], pool_root: Path, dest: Path, pairs: list[Pair]) -> int:
    """Copy every file actually used by a pair into the flat ``docx_source`` dir."""
    dest.mkdir(parents=True, exist_ok=True)
    used = {p.base.relative_path for p in pairs} | {p.next.relative_path for p in pairs}
    written = 0
    for entry in pool:
        if entry.relative_path not in used:
            continue
        target = dest / f"{flat_stem(entry.relative_path)}.docx"
        if target.exists() and target.stat().st_size == entry.size:
            continue
        _clone(pool_root / entry.relative_path, target)
        written += 1
    return written


def write_compare_manifest(path: Path, pairs: list[Pair], source_dir: Path, redline_dir: Path) -> None:
    """TSV consumed by ``scripts/word_compare_batch.applescript``:
    ``pair_id \\t base_path \\t next_path \\t out_path`` (absolute paths)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for pair in pairs:
        stem = pair_stem(pair)
        base = source_dir / f"{flat_stem(pair.base.relative_path)}.docx"
        nxt = source_dir / f"{flat_stem(pair.next.relative_path)}.docx"
        out = redline_dir / f"{stem}_redline.docx"
        lines.append(f"{stem}\t{base.resolve()}\t{nxt.resolve()}\t{out.resolve()}")
    path.write_text("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool-root", type=Path, default=DEFAULT_POOL_ROOT)
    parser.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    parser.add_argument("--inventory-csv", type=Path, default=DEFAULT_INVENTORY_CSV)
    parser.add_argument("--target", type=int, default=TARGET_PAIRS)
    parser.add_argument("--seed", type=lambda s: int(s, 0), default=PAIR_SEED)
    parser.add_argument("--dry-run", action="store_true", help="write manifests, skip staging")
    parser.add_argument(
        "--exclude-list",
        type=Path,
        default=DEFAULT_OUT_ROOT / "word_unreadable.txt",
        help="staged filenames Word cannot read (from --screen); skipped if absent",
    )
    args = parser.parse_args(argv)

    if not args.pool_root.is_dir():
        print(f"pool root not found: {args.pool_root}", file=sys.stderr)
        return 2

    pool = inventory(args.pool_root)
    unreadable: set[str] = set()
    if args.exclude_list.is_file():
        unreadable = {ln.strip() for ln in args.exclude_list.read_text().splitlines() if ln.strip()}
        pool = drop_unreadable(pool, unreadable)
    pairs = build_pairs(pool, target=args.target, seed=args.seed)

    # Two hard uniqueness gates. The source-stem one is not theoretical: `-` and
    # `_` both sanitize to `_`, so a pool with `a-b.docx` and `a_b.docx` in one
    # bucket would stage one file over the other and silently mis-pair it.
    source_stems = [flat_stem(p.relative_path) for p in pool]
    if len({s.lower() for s in source_stems}) != len(source_stems):
        collisions = {s for s in source_stems if source_stems.count(s) > 1}
        print(f"FATAL: source stems collide: {sorted(collisions)}", file=sys.stderr)
        return 1

    stems = [pair_stem(p) for p in pairs]
    if len({s.lower() for s in stems}) != len(stems):
        print("FATAL: duplicate pair keys (case-insensitive) — scorer would reject", file=sys.stderr)
        return 1

    _write_csv(args.inventory_csv, INVENTORY_FIELDS, [dict(zip(INVENTORY_FIELDS, p, strict=True)) for p in pool])
    _write_csv(args.out_root / "centralized_mapping.csv", MAPPING_FIELDS, mapping_rows(pairs))
    _write_csv(args.out_root / "pair_provenance.csv", PROVENANCE_FIELDS, provenance_rows(pairs))

    holdout = build_holdout(pairs)
    (args.out_root / "holdout.txt").write_text("\n".join(holdout) + "\n")

    source_dir = args.out_root / "docx_source"
    redline_dir = args.out_root / "docx_redlines_word"
    staged = 0
    if not args.dry_run:
        staged = stage_sources(pool, args.pool_root, source_dir, pairs)
        redline_dir.mkdir(parents=True, exist_ok=True)
        (args.out_root / "pdf_redlines_word").mkdir(parents=True, exist_ok=True)
    write_compare_manifest(args.out_root / "compare_manifest.tsv", pairs, source_dir, redline_dir)

    chain = sum(1 for p in pairs if p.kind == "chain")
    print(f"pool:      {len(pool)} usable .docx (encryption + ~$ lock files + {len(unreadable)} Word-unreadable excluded)")
    print(f"pairs:     {len(pairs)}  ({chain} chain / {len(pairs) - chain} cross)")
    print(f"sources:   {len({p.base.relative_path for p in pairs} | {p.next.relative_path for p in pairs})} distinct files, {staged} staged")
    print(f"holdout:   {len(holdout)} sealed keys -> {args.out_root / 'holdout.txt'}")
    print(f"manifests: {args.out_root / 'centralized_mapping.csv'}")
    print(f"           {args.out_root / 'pair_provenance.csv'}")
    print(f"           {args.out_root / 'compare_manifest.tsv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Find byte-identical files under grok_run/ and fold the extra copies into symlinks.

    uv run python scripts/grok_run_dedupe.py                 # report only
    uv run python scripts/grok_run_dedupe.py --apply         # move copies aside, link them

A group is every non-empty regular file with the same sha256 (symlinks, empty files and
``.DS_Store`` are skipped). One copy per group stays: the one inside a corpus origin
(``word_corpus.origins()``) when there is one, else the shallowest path. Every other copy
outside an origin moves to the attic (outside grok_run/, same relative path) and a
relative symlink to the kept copy takes its place, so every path, the fixtures
``MANIFEST.sha256.json`` and ``bench corpus build`` still read the same bytes. Copies
inside an origin are never touched: the corpus build reads same bytes under different
names as aliases and renders, so folding them would change the corpus. Those groups are
reported instead. ``moved.csv`` in the attic records each move.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import shutil
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

SKIP_NAMES = {".DS_Store"}


class DedupeError(RuntimeError):
    pass


@dataclass(frozen=True)
class Move:
    path: str
    keeper: str
    sha256: str
    size: int


@dataclass
class Plan:
    moves: list[Move] = field(default_factory=list)
    protected_groups: list[list[str]] = field(default_factory=list)
    groups: int = 0


def _sha256(path: Path) -> str:
    with open(path, "rb") as fh:
        return hashlib.file_digest(fh, "sha256").hexdigest()


def duplicate_groups(root: Path, jobs: int = 8) -> dict[str, list[str]]:
    """sha256 -> sorted relative paths, for every content held by two or more files."""
    by_size: dict[int, list[Path]] = defaultdict(list)
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            p = Path(dirpath) / name
            if name in SKIP_NAMES or p.is_symlink() or not p.is_file():
                continue
            size = p.stat().st_size
            if size:
                by_size[size].append(p)
    candidates = [p for ps in by_size.values() if len(ps) > 1 for p in ps]
    with ThreadPoolExecutor(jobs) as pool:
        digests = pool.map(_sha256, candidates)
    by_hash: dict[str, list[str]] = defaultdict(list)
    for p, digest in zip(candidates, digests, strict=True):
        by_hash[digest].append(p.relative_to(root).as_posix())
    return {h: sorted(ps) for h, ps in by_hash.items() if len(ps) > 1}


def is_protected(rel: str, protected: tuple[str, ...]) -> bool:
    return any(rel == p or rel.startswith(p.rstrip("/") + "/") for p in protected)


def plan(groups: dict[str, list[str]], protected: tuple[str, ...], root: Path | None = None) -> Plan:
    out = Plan(groups=len(groups))
    for digest, paths in sorted(groups.items(), key=lambda kv: kv[1]):
        guarded = [p for p in paths if is_protected(p, protected)]
        keeper = guarded[0] if guarded else min(paths, key=lambda p: (p.count("/"), p))
        if len(guarded) > 1:
            out.protected_groups.append(paths)
        size = (root / keeper).stat().st_size if root else 0
        for p in paths:
            if p != keeper and p not in guarded:
                out.moves.append(Move(p, keeper, digest, size))
    return out


def apply(plan: Plan, root: Path, attic: Path) -> None:
    clashes = [m.path for m in plan.moves if (attic / m.path).exists()]
    if clashes:
        raise DedupeError(f"{len(clashes)} attic paths already exist, e.g. {clashes[0]}")
    attic.mkdir(parents=True, exist_ok=True)
    ledger = attic / "moved.csv"
    new = not ledger.exists()
    with open(ledger, "a", newline="") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(["path", "keeper", "sha256", "bytes"])
        for m in plan.moves:
            src, dst = root / m.path, attic / m.path
            dst.parent.mkdir(parents=True, exist_ok=True)
            size = src.stat().st_size
            shutil.move(src, dst)
            src.symlink_to(os.path.relpath(root / m.keeper, src.parent))
            w.writerow([m.path, m.keeper, m.sha256, size])


def _corpus_protected(root: Path) -> tuple[str, ...]:
    """Origins under ``root``, relative to it. The jubarte-first fixtures origins
    (``_fixtures/...``) count too: their folder is ``grok_run/_fixtures``."""
    from neurotic_docx_bench.word_corpus import FIXTURES_PREFIX, origins

    prefix = root.name + "/"
    return tuple(
        o.removeprefix(prefix)
        for o in origins()
        if o.startswith(prefix) or o.startswith(FIXTURES_PREFIX + "/")
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=Path("grok_run"))
    ap.add_argument("--attic", type=Path, default=Path("grok_run_attic/dedupe"))
    ap.add_argument("--report", type=Path, default=Path("grok_run_attic/duplicates.csv"))
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--apply", action="store_true", help="move the copies aside and leave symlinks")
    args = ap.parse_args()

    root = args.root.resolve()
    if args.attic.resolve().is_relative_to(root):
        raise SystemExit("the attic must sit outside the scanned root")
    protected = _corpus_protected(root)
    groups = duplicate_groups(root, args.jobs)
    p = plan(groups, protected, root)

    args.report.parent.mkdir(parents=True, exist_ok=True)
    with open(args.report, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["sha256", "bytes", "copies", "action", "path"])
        moving = {m.path for m in p.moves}
        for digest, paths in sorted(groups.items(), key=lambda kv: kv[1]):
            size = (root / paths[0]).stat().st_size
            for path in paths:
                action = "move" if path in moving else ("keep" if not is_protected(path, protected) else "origin")
                w.writerow([digest, size, len(paths), action, path])

    files = sum(len(v) for v in groups.values())
    freed = sum(m.size for m in p.moves)
    print(f"{len(groups)} groups of identical files ({files} files) under {args.root}")
    print(f"{len(p.moves)} copies to fold into symlinks ({freed / 2**30:.2f} GiB)")
    print(f"{len(p.protected_groups)} groups with two or more copies inside corpus origins (left alone)")
    print(f"report: {args.report}")
    if args.apply:
        apply(p, root, args.attic.resolve())
        print(f"moved {len(p.moves)} copies to {args.attic}, ledger {args.attic / 'moved.csv'}")


if __name__ == "__main__":
    main()

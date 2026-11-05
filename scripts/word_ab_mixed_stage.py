#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["typer"]
# ///
"""Stage the 70-good + 30-broken mixed A/B fixture sets, conversion and redline.

One shuffle (seed 20261102): the sampled 100 are shuffled once and that shuffle
IS the processing order — staged names carry a ``NNN_`` prefix because
word_pdf's ``iter_docx`` walks a folder in sorted-name order, so the order the
driver sees is the order drawn here, broken scattered among good.

- 30 broken = every ``crashes_word`` fixture in ``really_broken/manifest.csv``
  (5) + a random 20 of ``repair_prompt`` + a random 5 of ``unconfirmed``.
- 70 good (conversion) = a random sample of the corpus docx.
- Redline set = 70 real corpus pairs (from a pools table whose base and next
  both exist locally) + the same 30 broken fixtures as bases, each paired with
  a real ``next`` document so the compare has work when the base opens.

Both roots get a ``fixtures.json`` recording seed, order, sources, categories.
"""

from __future__ import annotations

import csv
import json
import random
import shutil
from pathlib import Path

import typer

REPO = Path(__file__).resolve().parents[1]
BROKEN_MANIFEST = REPO / "really_broken/manifest.csv"
CORPUS = REPO / "corpus/word"
GOOD_DOCX = CORPUS / "tracking_without_comments/docx"
PAIR_TABLES = ("word_based_pairs.csv", "nocomments_pairs.csv")
AB_ROOT = REPO / "out/ab"
RL_ROOT = REPO / "out/ab_redline"
SEED = 20261102
N_GOOD = 70
N_BROKEN_REPAIR = 20
N_BROKEN_UNCONF = 5

app = typer.Typer()


def broken_rows() -> list[dict[str, str]]:
    with BROKEN_MANIFEST.open(encoding="utf-8") as fh:
        return [
            {"set": r[0], "file": r[1], "category": r[2]}
            for r in csv.reader(fh)
            if r and r[0] == "tool_redline"
        ]


def real_pairs() -> list[tuple[Path, Path, str]]:
    """(base, next, key) for pool pairs whose two docx exist locally."""
    for table in PAIR_TABLES:
        path = CORPUS / "pools" / table
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        pairs = []
        for r in rows:
            base = CORPUS / f"{r['base']}.docx"
            nxt = CORPUS / f"{r['next']}.docx"
            if base.is_file() and nxt.is_file():
                pairs.append((base, nxt, r["key"]))
        if pairs:
            typer.echo(f"pairs from {table}: {len(pairs)} of {len(rows)} rows complete locally")
            return pairs
    raise SystemExit("no pools table with locally complete pairs")


@app.command()
def stage(
    seed: int = SEED,
    root: Path = AB_ROOT,
    rl_root: Path = RL_ROOT,
) -> None:
    rng = random.Random(seed)
    rows = broken_rows()
    by_cat: dict[str, list[dict[str, str]]] = {}
    for r in rows:
        by_cat.setdefault(r["category"], []).append(r)
    for cat, lst in by_cat.items():
        lst.sort(key=lambda r: r["file"])
    broken = (
        by_cat.get("crashes_word", [])[:5]
        + rng.sample(by_cat.get("repair_prompt", []), N_BROKEN_REPAIR)
        + rng.sample(by_cat.get("unconfirmed", []), N_BROKEN_UNCONF)
    )
    missing = [r["file"] for r in broken if not (REPO / "really_broken" / r["file"]).is_file()]
    if missing:
        raise SystemExit(f"broken fixture(s) missing on disk: {missing[:3]}")

    good_names = sorted(
        p.name for p in GOOD_DOCX.glob("*.docx") if not p.name.startswith("~$")
    )
    good = rng.sample(good_names, N_GOOD)

    mixed = [(r["file"], r["category"]) for r in broken] + [(n, "good") for n in good]
    rng.shuffle(mixed)  # the one shuffle: this order is the processing order

    conv = root / "mixed100" / "docx"
    if conv.exists():
        shutil.rmtree(conv)
    conv.mkdir(parents=True)
    conv_order = []
    for i, (name, cat) in enumerate(mixed):
        src = (REPO / "really_broken" / name) if cat != "good" else GOOD_DOCX / name
        staged = conv / f"{i:03d}_{Path(name).name}"  # basename: manifest paths carry folders
        shutil.copy2(src, staged)
        conv_order.append({"order": i, "source": str(src), "category": cat, "staged": staged.name})

    pairs = real_pairs()
    good_pairs = rng.sample(pairs, N_GOOD)
    # A broken pair: the broken fixture as base, a real `next` as its partner,
    # cycling the sampled good pairs so each broken base gets a real revision.
    rl = [
        (REPO / "really_broken" / r["file"], good_pairs[i % N_GOOD][1], r["category"])
        for i, r in enumerate(broken)
    ] + [(b, n, "good_pair") for b, n, _ in good_pairs]
    rng.shuffle(rl)  # the redline set's one shuffle

    a_dir, b_dir = rl_root / "a", rl_root / "b"
    for d in (a_dir, b_dir):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
    rl_order = []
    for i, (base, nxt, cat) in enumerate(rl):
        key = f"p{i:03d}.docx"
        shutil.copy2(base, a_dir / key)
        shutil.copy2(nxt, b_dir / key)
        rl_order.append({"order": i, "key": key, "base": str(base), "next": str(nxt), "category": cat})

    root.mkdir(parents=True, exist_ok=True)
    rl_root.mkdir(parents=True, exist_ok=True)
    (root / "fixtures.json").write_text(
        json.dumps({"seed": seed, "set": "mixed100", "order": conv_order}, indent=1), encoding="utf-8"
    )
    (rl_root / "fixtures.json").write_text(
        json.dumps({"seed": seed, "set": "mixed100_pairs", "order": rl_order}, indent=1), encoding="utf-8"
    )
    cats = {c: sum(1 for _, cc in mixed if cc == c) for c in ("crashes_word", "repair_prompt", "unconfirmed", "good")}
    typer.echo(
        f"staged conversion: {len(conv_order)} under {conv} ({cats}); redline: {len(rl_order)} pairs under {a_dir}/{b_dir}"
    )


if __name__ == "__main__":
    app()

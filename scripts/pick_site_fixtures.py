"""Pick a varied N-document sample of the jubarte DOCX-to-PDF results for the comparison site.

Pool: documents scored by the current jubarte AND converted by every other engine on the site
(docxide-pdf, LibreOffice), so each row can be shown side by side. Strata: corpus state x page
count x jubarte score band. Allocation flattens the distribution (cell weight = size**0.5, with a
floor) so rare kinds of document are well represented instead of drowned by the common ones.

    uv run python scripts/pick_site_fixtures.py --n 800 --seed 20261001 --out results/site_fixtures_800.csv
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import math
import os
import random
from pathlib import Path

PAGE_BINS = [(1, 1), (2, 2), (3, 3), (4, 6), (7, 12), (13, 30), (31, 10**6)]
SCORE_BINS = [(0, 50), (50, 70), (70, 90), (90, 100.01)]


def bin_of(value: float, bins: list[tuple[float, float]]) -> int:
    return next(i for i, (lo, hi) in enumerate(bins) if lo <= value <= hi)


def label(bins: list[tuple[float, float]], i: int) -> str:
    lo, hi = bins[i]
    return f"{lo:g}" if lo == hi else (f"{lo:g}+" if hi >= 10**6 else f"{lo:g}-{hi:g}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", type=Path, default=Path("results/jubarte_0.10.1_docx_to_pdf_work"))
    ap.add_argument("--results", type=Path, default=Path("results"))
    ap.add_argument("--n", type=int, default=800)
    ap.add_argument("--seed", type=int, default=20261001)
    ap.add_argument("--out", type=Path, default=Path("results/site_fixtures_800.csv"))
    ap.add_argument("--exclude", type=Path, action="append", default=[], help="a picked CSV whose stems are left out (repeatable)")
    a = ap.parse_args()

    others = [
        {p[:-4] for p in os.listdir(a.results / d / "candidate")}
        for d in ("docxide_0.17.1_work", "soffice_26.8.0.3_work")
    ]
    pool: dict[str, dict] = {}
    for line in (a.work / "jubarte" / "scores.checkpoint.jsonl").read_text().splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        pool[row["key"]] = {"score": row["result"]["overall_score"], "pages": row["result"]["page_count"]}
    pool = {k: v for k, v in pool.items() if all(k in o for o in others)}
    for path in a.exclude:
        with path.open() as fh:
            for row in csv.DictReader(fh):
                pool.pop(row["stem"], None)

    cells: dict[tuple, list[str]] = collections.defaultdict(list)
    for key, v in pool.items():
        cells[(key.split("__")[0], bin_of(v["pages"], PAGE_BINS), bin_of(v["score"], SCORE_BINS))].append(key)

    # floor of 2 per non-empty cell, the rest by sqrt(size)
    quota = {c: min(len(k), 2) for c, k in cells.items()}
    left = a.n - sum(quota.values())
    weight = {c: math.sqrt(len(k)) for c, k in cells.items()}
    for _ in range(10):
        open_cells = {c: w for c, w in weight.items() if quota[c] < len(cells[c])}
        total = sum(open_cells.values())
        if left <= 0 or not total:
            break
        for c, w in sorted(open_cells.items()):
            add = min(len(cells[c]) - quota[c], int(left * w / total))
            quota[c] += add
        left = a.n - sum(quota.values())
    rng = random.Random(a.seed)
    order = sorted(cells)
    while left > 0:  # remainder, one at a time, to the largest unfilled cells
        c = max((c for c in order if quota[c] < len(cells[c])), key=lambda c: (len(cells[c]) - quota[c], c))
        quota[c] += 1
        left -= 1

    picked = []
    for c in order:
        picked += rng.sample(sorted(cells[c]), quota[c])
    picked.sort()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["stem", "state", "pages", "jubarte_score"])
        for k in picked:
            w.writerow([k, k.split("__")[0], pool[k]["pages"], round(pool[k]["score"], 2)])

    print(f"pool {len(pool)} -> picked {len(picked)} ({a.out})")
    for title, fn, bins in (("state", None, None), ("pages", lambda k: pool[k]["pages"], PAGE_BINS),
                            ("score", lambda k: pool[k]["score"], SCORE_BINS)):
        if fn is None:
            cnt = collections.Counter(k.split("__")[0] for k in picked)
            base = collections.Counter(k.split("__")[0] for k in pool)
            print(f"\n{title:6s} picked / pool")
            for s in sorted(base):
                print(f"  {s:28s} {cnt[s]:4d} / {base[s]:5d}")
        else:
            cnt = collections.Counter(bin_of(fn(k), bins) for k in picked)
            base = collections.Counter(bin_of(fn(k), bins) for k in pool)
            print(f"\n{title:6s} picked / pool")
            for i in range(len(bins)):
                print(f"  {label(bins, i):28s} {cnt[i]:4d} / {base[i]:5d}")


if __name__ == "__main__":
    main()

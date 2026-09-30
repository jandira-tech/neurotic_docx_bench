"""Pick the 100 Word tracking redlines whose accepted copies join the corpus (seed 20260928).

40 from with_comments_tracking, 60 from tracking_without_comments, each stratified by source
set in proportion to the pool and one pair per base document where the set allows. Pairs
touching a document Word refused to open are left out. Writes accept_selection.csv.
"""

import csv
import random
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
SEED = 20260928
QUOTA = {"with_comments_tracking": 40, "tracking_without_comments": 60}
REFUSED = {p.stem[:10] for p in Path("grok_run/wr0928/pdf_fill/word_refused").glob("*.docx")}


def ids(row):
    return {Path(row["base"]).name[:10], Path(row["next"]).name[:10]}


def allocate(counts, total):
    """Largest-remainder split of ``total`` across sets, proportional to ``counts``."""
    n = sum(counts.values())
    raw = {k: total * v / n for k, v in counts.items()}
    out = {k: min(int(x), counts[k]) for k, x in raw.items()}
    for k in sorted(raw, key=lambda k: raw[k] - int(raw[k]), reverse=True):
        if sum(out.values()) >= total:
            break
        if out[k] < counts[k]:
            out[k] += 1
    return out


def pick(rows, k, rng):
    """``k`` rows, one per base first, then the rest at random."""
    rows = rows[:]
    rng.shuffle(rows)
    seen, first, rest = set(), [], []
    for r in rows:
        (rest if r["base"] in seen else first).append(r)
        seen.add(r["base"])
    return (first + rest)[:k]


def main():
    rng = random.Random(SEED)
    rows = [r for r in csv.DictReader(open(HERE / "pool_pairs.csv")) if not ids(r) & REFUSED]
    chosen = []
    for state, quota in QUOTA.items():
        by_set = defaultdict(list)
        for r in rows:
            if r["state"] == state:
                by_set[r["sets"]].append(r)
        alloc = allocate({s: len(v) for s, v in by_set.items()}, quota)
        for s in sorted(by_set):
            chosen += pick(by_set[s], alloc[s], rng)
    with open(HERE / "accept_selection.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(chosen)
    print(len(chosen), "selected;", len(REFUSED), "refused ids excluded")


if __name__ == "__main__":
    main()

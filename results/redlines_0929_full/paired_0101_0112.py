"""Paired comparison of two scored redline lanes on the compares both scored.

    uv run python results/redlines_0929_full/paired_0101_0112.py jubarte-0.10.1 jubarte-0.11.2-full

Both score files must come from the same scorer (bench 0de6361bf changed it on
2026-10-03). Prints the paired deltas overall and per oracle (corpus or fresh), how many
compares moved by more than 2 points each way, a bootstrap 95% interval of the mean
delta, and the 10 largest losses and gains (key, A, B) to read by hand.
"""

from __future__ import annotations

import json
import random
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MOVE = 2.0


def bootstrap(deltas: list[float], rounds: int = 2000, seed: int = 20261004) -> tuple[float, float]:
    rng = random.Random(seed)
    means = sorted(statistics.fmean(rng.choices(deltas, k=len(deltas))) for _ in range(rounds))
    return means[int(0.025 * rounds)], means[int(0.975 * rounds)]


def line(name: str, pairs: list[tuple[str, float, float]]) -> str:
    a = [x for _, x, _ in pairs]
    b = [y for _, _, y in pairs]
    d = [y - x for _, x, y in pairs]
    lo, hi = bootstrap(d)
    return (f'{name:28} n={len(d):5} A {statistics.fmean(a):6.2f} B {statistics.fmean(b):6.2f} '
            f'delta {statistics.fmean(d):+6.2f} [{lo:+.2f},{hi:+.2f}] median {statistics.median(d):+5.2f} '
            f'up {sum(x > MOVE for x in d):4} down {sum(x < -MOVE for x in d):4} '
            f'>=90 {sum(x >= 90 for x in a):4}->{sum(x >= 90 for x in b):4}')


def main() -> None:
    tool_a, tool_b = sys.argv[1], sys.argv[2]
    rows_a = json.loads((HERE / f'scores_{tool_a}.json').read_text())['rows']
    rows_b = json.loads((HERE / f'scores_{tool_b}.json').read_text())['rows']
    pairs: list[tuple[str, float, float]] = []
    by_state: dict[str, list[tuple[str, float, float]]] = {}
    for key in sorted(set(rows_a) & set(rows_b)):
        a, b = rows_a[key].get('overall_score'), rows_b[key].get('overall_score')
        if a is None or b is None:
            continue
        pairs.append((key, a, b))
        by_state.setdefault(rows_b[key].get('oracle') or '?', []).append((key, a, b))
    print(f'{tool_a} (A) vs {tool_b} (B): {len(pairs)} compares scored by both')
    print(line('all', pairs))
    for state, group in sorted(by_state.items()):
        if len(group) > 1:
            print(line(state, group))
    ranked = sorted(pairs, key=lambda p: p[2] - p[1])
    print('largest losses:')
    for key, a, b in ranked[:10]:
        print(f'  {b - a:+7.2f}  {a:6.2f} -> {b:6.2f}  {key}')
    print('largest gains:')
    for key, a, b in ranked[-10:][::-1]:
        print(f'  {b - a:+7.2f}  {a:6.2f} -> {b:6.2f}  {key}')


if __name__ == '__main__':
    main()

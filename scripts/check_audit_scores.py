#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Check the Word-driver audit's scorecard against itself.

Three classes of drift have already happened in this document by hand, so they
are checked mechanically now:

1. a row's Σ not matching the seven criteria beside it;
2. the table not being sorted by Σ, which is how it claims to be ordered;
3. a per-criterion detail table (§6 C4, §7 C5, §8 C6, §9 C7) carrying a score
   that disagrees with the same script's cell in the scorecard. That one bit
   twice: §8's C6 row for `word-convert.sh` sat at 0.85 for two revisions while
   the scorecard said 0.80.

Usage: check_audit_scores.py <audit.md> [<audit.md> ...]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

CRITERIA = ("C1", "C2", "C3", "C4", "C5", "C6", "C7")
SCORECARD = re.compile(
    r"^\| `([^`]+)` \| (ndb|jf|jr) \| " + r"([\d.]+) \| " * 7 + r"\*\*([\d.]+)\*\* \| (\S+) \|$"
)
DETAIL = re.compile(r"^\| `([^`]+)` \| ([01]\.\d{2}) \| ")
# Which criterion each detail section scores, keyed by its heading number.
SECTION_CRITERION = {"6": "C4", "7": "C5", "8": "C6", "9": "C7"}


def check(path: Path) -> list[str]:
    problems: list[str] = []
    lines = path.read_text(encoding="utf-8").splitlines()

    scores: dict[str, dict[str, float]] = {}
    totals: list[tuple[str, float]] = []
    for line in lines:
        if m := SCORECARD.match(line):
            name = m.group(1)
            comps = [float(m.group(i)) for i in range(3, 10)]
            total = float(m.group(10))
            if abs(round(sum(comps), 2) - total) > 1e-9:
                problems.append(f"{name}: components sum {round(sum(comps), 2)}, stated {total}")
            # Two scripts share the name `word-open-probe.sh`; key on name+repo.
            scores.setdefault(name, {})
            scores[name] = dict(zip(CRITERIA, comps, strict=True))
            totals.append((name, total))

    if not totals:
        return [f"{path}: no scorecard rows parsed"]

    ordered = [t for _, t in totals]
    if ordered != sorted(ordered, reverse=True):
        for i in range(len(ordered) - 1):
            if ordered[i] < ordered[i + 1]:
                problems.append(
                    f"order: {totals[i][0]} ({ordered[i]}) precedes "
                    f"{totals[i + 1][0]} ({ordered[i + 1]})"
                )

    section = ""
    for line in lines:
        if m := re.match(r"^## (\d+)\. ", line):
            section = m.group(1)
        criterion = SECTION_CRITERION.get(section)
        if not criterion:
            continue
        if m := DETAIL.match(line):
            name, shown = m.group(1), float(m.group(2))
            expected = scores.get(name, {}).get(criterion)
            if expected is not None and abs(expected - shown) > 1e-9:
                problems.append(
                    f"§{section} {criterion} row for {name}: shows {shown}, "
                    f"scorecard says {expected}"
                )
    return [f"{path.name}: {p}" for p in problems]


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    found: list[str] = []
    for raw in argv:
        found.extend(check(Path(raw)))
    for p in found:
        print(f"FAIL {p}")
    if not found:
        print(f"ok   {len(argv)} audit file(s): sums, ordering and detail rows agree")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

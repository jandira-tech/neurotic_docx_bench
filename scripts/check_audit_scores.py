#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Check the Word-driver audit's scorecard against itself.

Four classes of drift, three of which have already happened in this document by
hand, are checked mechanically now:

1. a row's Σ not matching the seven criteria beside it;
2. the table not being sorted by Σ, which is how it claims to be ordered;
3. a per-criterion detail table (§6 C4, §7 C5, §8 C6, §9 C7) carrying a score
   that disagrees with the same script's cell in the scorecard. That one bit
   twice: §8's C6 row for `word-convert.sh` sat at 0.85 for two revisions while
   the scorecard said 0.80. Grouped rows count: a detail row may name several
   scripts ("`word-open-probe.sh` ×2"), and every name in it is checked;
4. two scorecard rows for the same script name (it exists in two repositories)
   whose scores have drifted apart, which a grouped detail row cannot restate.

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
# The first cell is free text that mentions one or more scripts, because the
# detail tables group scripts that share a score: "`word-open-probe.sh` ×2",
# "`render/word.py`, `word_validate_batch.py`", "family A (6 files)". Anchoring
# on a lone backticked name skipped every grouped row -- 6 of 54 in §6-§9.
DETAIL = re.compile(r"^\| ([^|]*`[^|]*) \| ([01]\.\d{2}) \| ")
NAME = re.compile(r"`([^`]+)`")
# Which criterion each detail section scores, keyed by its heading number.
SECTION_CRITERION = {"6": "C4", "7": "C5", "8": "C6", "9": "C7"}
# The row pattern stays loose on purpose: a row it does not match is skipped
# silently, so a strict pattern there would hide the malformed row. Each cell
# is held to the audit's own grammar here and reported when it is off.
SCORE = re.compile(r"\d\.\d{2}")
MAX_TOTAL = float(len(CRITERIA))


def check(path: Path) -> list[str]:
    """Return every drift found in one audit file, as human-readable lines.

    An empty list means the four classes in the module docstring all hold. A
    file that cannot be read, or that parses to no scorecard at all, reports
    that rather than passing silently -- "ok" on a file nobody managed to read
    is the one outcome worse than a failure.
    """
    problems: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        # A typo'd path in CI should name itself, not raise through main().
        return [f"{path}: cannot read ({exc.strerror})"]

    # Keyed on (name, repo): two scripts share the name `word-open-probe.sh`,
    # and keying on the name alone let the second row silently replace the
    # first, so a divergence between the two copies could not be detected.
    scores: dict[tuple[str, str], dict[str, float]] = {}
    by_name: dict[str, list[tuple[str, dict[str, float]]]] = {}
    totals: list[tuple[str, float]] = []
    matched = 0
    for line in lines:
        if m := SCORECARD.match(line):
            matched += 1
            name, repo = m.group(1), m.group(2)
            cells = [m.group(i) for i in range(3, 11)]
            if bad := [c for c in cells if not SCORE.fullmatch(c)]:
                problems.append(f"{name} ({repo}): not a d.dd score: {', '.join(map(repr, bad))}")
                continue
            comps = [float(c) for c in cells[:7]]
            total = float(cells[7])
            for criterion, value in zip(CRITERIA, comps, strict=True):
                if not 0.0 <= value <= 1.0:
                    problems.append(f"{name} ({repo}): {criterion} {value} outside [0.00, 1.00]")
            if not 0.0 <= total <= MAX_TOTAL:
                problems.append(f"{name} ({repo}): total {total} outside [0.00, {MAX_TOTAL:.2f}]")
            if (name, repo) in scores:
                problems.append(f"{name} ({repo}): scored twice in the scorecard")
            if abs(round(sum(comps), 2) - total) > 1e-9:
                problems.append(f"{name}: components sum {round(sum(comps), 2)}, stated {total}")
            criteria = dict(zip(CRITERIA, comps, strict=True))
            scores[name, repo] = criteria
            by_name.setdefault(name, []).append((repo, criteria))
            totals.append((name, total))

    if not matched:
        return [f"{path}: no scorecard rows parsed"]

    ordered = [t for _, t in totals]
    problems.extend(
        f"order: {totals[i][0]} ({ordered[i]}) precedes {totals[i + 1][0]} ({ordered[i + 1]})"
        for i in range(len(ordered) - 1)
        if ordered[i] < ordered[i + 1]
    )

    # Two copies of one script that have drifted apart are wrong on their own,
    # whatever the detail tables happen to restate. Checking this inside the
    # detail-row loop only looked at that section's criterion, so C1 to C3 were
    # never examined and C4 to C7 were skipped whenever no row named the script.
    for name, entries in sorted(by_name.items()):
        if len(entries) < 2:
            continue
        for criterion in CRITERIA:
            seen = {repo: criteria[criterion] for repo, criteria in entries}
            if len(set(seen.values())) > 1:
                problems.append(
                    f"{criterion} scorecard copies for {name} disagree across repos ({seen})"
                )

    section = ""
    for line in lines:
        if m := re.match(r"^## (\d+)\. ", line):
            section = m.group(1)
        criterion = SECTION_CRITERION.get(section)
        if not criterion:
            continue
        if m := DETAIL.match(line):
            cell, shown = m.group(1), float(m.group(2))
            for name in NAME.findall(cell):
                entries = by_name.get(name)
                if not entries:
                    continue
                seen = {repo: criteria[criterion] for repo, criteria in entries}
                if len(set(seen.values())) > 1:
                    # Already reported above, against every criterion rather
                    # than only this section's. A grouped row cannot restate a
                    # value the copies do not agree on, so there is nothing
                    # further to compare here.
                    continue
                expected = next(iter(seen.values()))
                if abs(expected - shown) > 1e-9:
                    problems.append(
                        f"§{section} {criterion} row for {name}: shows {shown}, "
                        f"scorecard says {expected}"
                    )
    return [f"{path.name}: {p}" for p in problems]


def main(argv: list[str]) -> int:
    """Check every file named on the command line. Exit 0 clean, 1 drift, 2 usage."""
    if any(a in {"-h", "--help"} for a in argv):
        print(__doc__)
        return 0
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

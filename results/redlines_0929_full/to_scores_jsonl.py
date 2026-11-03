"""Write this run's redline scores as ``scores.jsonl`` lines for ``bench report``.

    uv run python results/redlines_0929_full/to_scores_jsonl.py

Reads ``scores_<tool>.json`` (``measure.py``) for every tool and writes one ``action: redline``
line per tool: the denominator is every Word compare of ``pool_pairs.csv`` (3502), a compare
with no scored PDF counts 0 in ``itt_mean`` / ``itt_median``. ``subset`` holds the same
statistics over only the compares docxodus scored, as if the bench held only the pairs
docxodus redlined and Word exported. The tools are the keys of ``versions.json``. Rewrites
``scores.jsonl``.

A lane scored on a FIXED SET (#129) instead of the run's pool is a lane of its own: its
scores file is ``scores_<tool>_set-<set>.json`` and its compares are the keys of
``set-<set>.csv``, so its denominator is the set (600), not the pool (3502). Its line
carries the set's name, and it has no ``subset`` (the pool's docxodus subset means
nothing over a different denominator). Such a lane is found by its file name, not by a
list here: every ``scores_<tool>_set-*.json`` in this folder is one.
"""

from __future__ import annotations

import csv
import json
import statistics
from datetime import UTC, datetime
from pathlib import Path

from neurotic_docx_bench import pipeline

HERE = Path(__file__).parent
# The run's tools and their labels, in report order. A new tool joins by a line here
# (scripts/release_jubarte.py adds each jubarte release it scores).
VERSIONS: dict[str, str] = json.loads((HERE / "versions.json").read_text())
TOOLS = tuple(VERSIONS)
SUBSET_OF = "docxodus"


def set_lane(tool: str) -> tuple[str, Path] | None:
    """The fixed set a lane was scored on, and that set's compare list.

    ``scores_<tool>_set-<set>.json`` → the set's name and ``set-<set>.csv`` (the
    ``--sample-csv`` of ``measure.py``). None when the lane is a pool lane.
    """
    found = []
    for f in sorted(HERE.glob(f"scores_{tool}_set-*.json")):
        name = f.stem[len(f"scores_{tool}_set-"):]
        # Only a file whose set list exists is the lane's own scores file; the others
        # (e.g. scores_<tool>_set-<set>_stamp_matched.json) are labelled side figures.
        if (HERE / f"set-{name}.csv").is_file():
            found.append((f, name))
    if not found:
        return None
    if len(found) > 1:
        raise SystemExit(f"{tool}: {len(found)} set score files: {[p.name for p, _ in found]}")
    name = found[0][1]
    keys = HERE / f"set-{name}.csv"
    return name, keys


def _stats(xs: list[float]) -> dict:
    if not xs:
        return {"n": 0}
    return {"n": len(xs), "mean": statistics.fmean(xs), "median": statistics.median(xs)}


def summarize(rows: dict[str, dict], keys: list[str]) -> dict:
    """ITT over ``keys`` (0 for a compare with no row) and scored-only statistics."""
    here = {k: rows[k] for k in keys if k in rows}
    overall = {k: pipeline.overall_from_result(r) for k, r in here.items()}
    scored = list(overall.values())
    itt = [overall.get(k, 0.0) for k in keys]
    return {
        "pairs": len(keys),
        "scored": len(here),
        "itt_mean": statistics.fmean(itt),
        "itt_median": statistics.median(itt),
        "overall": _stats(scored)
        | {
            "exact_100": sum(x >= 100 for x in scored),
            "at_least_90": sum(x >= 90 for x in scored),
            "below_50": sum(x < 50 for x in scored),
        },
        "ink_jaccard": _stats([r["ink_jaccard"] for r in here.values() if r.get("ink_jaccard") is not None]),
        "text_boundary": _stats([r["text_boundary"] for r in here.values() if r.get("text_boundary") is not None]),
    }


def main() -> None:
    keys = [r["key"] for r in csv.DictReader(open(HERE / "pool_pairs.csv"))]
    # The subset every pool lane reports: the compares docxodus scored (the run's
    # reference tool). A set lane has no subset — its denominator is a different set.
    subset_ref = HERE / f"scores_{SUBSET_OF}.json"
    subset_rows = json.loads(subset_ref.read_text())["rows"] if subset_ref.is_file() else {}
    subset_keys = [k for k in keys if k in subset_rows]
    stamp = datetime.now(UTC).isoformat(timespec="seconds")
    with (HERE / "scores.jsonl").open("w") as fh:
        for tool in TOOLS:
            lane = set_lane(tool)
            if lane is None:
                rows = json.loads((HERE / f"scores_{tool}.json").read_text())["rows"]
                unknown = len(set(rows) - set(keys))
                if unknown:
                    raise SystemExit(f"{tool}: {unknown} row(s) not in pool_pairs.csv")
                line = {"track": HERE.name, "tool": tool, "action": "redline"} | summarize(rows, keys)
                line["subset"] = {"of": SUBSET_OF} | summarize(rows, subset_keys)
                print(f"{tool}: ITT {line['itt_mean']:.2f}/{line['itt_median']:.2f} "
                      f"({line['subset']['itt_mean']:.2f}/{line['subset']['itt_median']:.2f}), "
                      f"scored {line['scored']}/{line['pairs']} "
                      f"({line['subset']['scored']}/{line['subset']['pairs']})")
            else:
                set_name, set_keys_file = lane
                set_keys = [r["key"] for r in csv.DictReader(open(set_keys_file))]
                rows = json.loads((HERE / f"scores_{tool}_set-{set_name}.json").read_text())["rows"]
                unknown = len(set(rows) - set(set_keys))
                if unknown:
                    raise SystemExit(f"{tool}: {unknown} row(s) not in {set_keys_file.name}")
                line = {"track": HERE.name, "tool": tool, "action": "redline",
                        "set": set_name} | summarize(rows, set_keys)
                print(f"{tool}: set {set_name} ITT {line['itt_mean']:.2f}/{line['itt_median']:.2f}, "
                      f"scored {line['scored']}/{line['pairs']}")
            line["timestamp"] = stamp
            fh.write(json.dumps(line) + "\n")


if __name__ == "__main__":
    main()

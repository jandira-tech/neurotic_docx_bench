"""Write this run's redline scores as ``scores.jsonl`` lines for ``bench report``.

    uv run python results/redlines_0929_full/to_scores_jsonl.py

Reads ``scores_<tool>.json`` (``measure.py``) for every tool and writes one ``action: redline``
line per tool: the denominator is every Word compare of ``pool_pairs.csv`` (3502), a compare
with no scored PDF counts 0 in ``itt_mean`` / ``itt_median``. ``subset`` holds the same
statistics over only the compares docxodus scored, as if the bench held only the pairs
docxodus redlined and Word exported. The tools are the keys of ``versions.json``. Rewrites
``scores.jsonl``.
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
    rows = {t: json.loads((HERE / f"scores_{t}.json").read_text())["rows"] for t in TOOLS}
    unknown = {t: len(set(r) - set(keys)) for t, r in rows.items() if set(r) - set(keys)}
    if unknown:
        raise SystemExit(f"rows not in pool_pairs.csv: {unknown}")
    subset_keys = [k for k in keys if k in rows[SUBSET_OF]]
    stamp = datetime.now(UTC).isoformat(timespec="seconds")
    with (HERE / "scores.jsonl").open("w") as fh:
        for tool in TOOLS:
            line = {"track": HERE.name, "tool": tool, "action": "redline"} | summarize(rows[tool], keys)
            line["subset"] = {"of": SUBSET_OF} | summarize(rows[tool], subset_keys)
            line["timestamp"] = stamp
            fh.write(json.dumps(line) + "\n")
            print(f"{tool}: ITT {line['itt_mean']:.2f}/{line['itt_median']:.2f} "
                  f"({line['subset']['itt_mean']:.2f}/{line['subset']['itt_median']:.2f}), "
                  f"scored {line['scored']}/{line['pairs']} ({line['subset']['scored']}/{line['subset']['pairs']})")


if __name__ == "__main__":
    main()

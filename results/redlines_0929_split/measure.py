"""Score the tool side of the 400/400 accept/reject split against Word, with the bench's scorer.

    uv run python results/redlines_0929_split/measure.py jubarte-rust docxodus superdoc
    uv run python results/redlines_0929_split/measure.py word-identity   # control

For each tool and action: the tool's redline with every change accepted (or rejected) by
Word and exported by Word (``<tool>/<action>/by_word/<key>_<tool><suffix>.pdf``, run.sh)
against Word's own compare accepted (or rejected) the same way
(``corpus/word/<action>/pdf/<key>.pdf``), through ``pipeline.score_folders_plain`` on link
folders named ``<key>.pdf``. The denominator is every pair of the action (400): a pair
with no tool redline or no Word PDF is ``missing`` and counts 0 in the intent-to-treat
columns (``itt_mean``, ``itt_median``), as in the bench. ``word-identity`` scores Word's
own PDFs against themselves and must read 100.

Each tool is scored in its own temporary work folder, so its rasters are gone before the
next starts. Appends one line per tool and action to ``scores.jsonl``.
"""

from __future__ import annotations

import csv
import json
import statistics
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from neurotic_docx_bench import kernels, pipeline

HERE = Path(__file__).parent
CORPUS = Path("corpus/word")
SUFFIX = {"accept_all": "_accepted_tracking", "reject_all": "_rejected_tracking"}


def _scalars(row: dict) -> dict:
    return {k: v for k, v in row.items() if isinstance(v, (int, float, str, bool)) or v is None}


def _stats(xs: list[float]) -> dict:
    if not xs:
        return {"n": 0}
    return {"n": len(xs), "mean": statistics.fmean(xs), "median": statistics.median(xs)}


def score(tool: str, action: str, keys: list[str]) -> dict:
    with tempfile.TemporaryDirectory(prefix=f"measure-{action}-{tool}.") as tmp:
        o, c, work = (Path(tmp) / d for d in ("oracle", "candidate", "work"))
        for d in (o, c, work):
            d.mkdir()
        for key in keys:
            (o / f"{key}.pdf").symlink_to((CORPUS / action / "pdf" / f"{key}.pdf").resolve())
            if tool == "word-identity":
                cand = CORPUS / action / "pdf" / f"{key}.pdf"
            else:
                cand = HERE / tool / action / "by_word" / f"{key}_{tool}{SUFFIX[action]}.pdf"
            if cand.is_file():
                (c / f"{key}.pdf").symlink_to(cand.resolve())
        rows = {k: _scalars(v) for k, v in pipeline.score_folders_plain(o, c, work).items()}
    overall = {k: pipeline.overall_from_result(r) for k, r in rows.items()}
    itt = [overall.get(k.lower(), overall.get(k, 0.0)) for k in keys]
    scored = list(overall.values())
    return {
        "track": "redlines_0929_split",
        "tool": tool,
        "action": action,
        "pairs": len(keys),
        "scored": len(rows),
        "missing": sorted(k for k in keys if k.lower() not in overall and k not in overall),
        "itt_mean": statistics.fmean(itt),
        "itt_median": statistics.median(itt),
        "overall": _stats(scored)
        | {
            "exact_100": sum(x >= 100 for x in scored),
            "at_least_90": sum(x >= 90 for x in scored),
            "below_50": sum(x < 50 for x in scored),
        },
        "ink_jaccard": _stats([r["ink_jaccard"] for r in rows.values() if r.get("ink_jaccard") is not None]),
        "text_boundary": _stats([r["text_boundary"] for r in rows.values() if r.get("text_boundary") is not None]),
        "scorer_backend": kernels.backend_id(),
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        "rows": rows,
    }


def main() -> None:
    pairs = list(csv.DictReader(open(HERE / "pool_pairs.csv")))
    with (HERE / "scores.jsonl").open("a") as fh:
        for tool in sys.argv[1:]:
            for action in ("accept_all", "reject_all"):
                keys = sorted(r["key"] for r in pairs if r["action"] == action)
                line = score(tool, action, keys)
                fh.write(json.dumps(line, sort_keys=True) + "\n")
                fh.flush()
                o = line["overall"]
                print(
                    f"{tool} {action}: {line['scored']}/{line['pairs']} scored, "
                    f"ITT mean {line['itt_mean']:.2f} median {line['itt_median']:.2f}; scored-only mean "
                    f"{o.get('mean', 0):.2f} median {o.get('median', 0):.2f}, 100: {o.get('exact_100', 0)}"
                )


if __name__ == "__main__":
    main()

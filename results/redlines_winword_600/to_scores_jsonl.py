"""Turn this run's ``scores_<test>.json`` summaries into the bench's run files.

    python results/redlines_winword_600/to_scores_jsonl.py

Writes ``scores.jsonl`` (one line per (tool, action), the shape every ``results/redlines_*``
run uses) and ``versions.json``. Only the seven tests ``run_all.sh`` scored are published;
the figures are the summaries' own, unrounded.
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRACK = HERE.name
# test -> (tool id, action)
TESTS = {
    "redline": ("docxodus-16.1.0", "redline"),
    "redline-jubarte": ("jubarte-0.20.0", "redline"),
    "redline-folio-emit": ("folio-0.70.0-emit", "redline"),
    "redline-superdoc": ("superdoc-2.31.0", "redline"),
    "word-mac": ("word-mac", "redline"),
    "convert": ("docxodus-16.1.0", "convert"),
    "convert-jubarte": ("jubarte-0.20.0", "convert"),
}
VERSIONS = {
    "docxodus-16.1.0": "docxodus 16.1.0 (npm/WASM)",
    "jubarte-0.20.0": "jubarte 0.20.0 (release)",
    "folio-0.70.0-emit": 'folio 0.70.0 (@stll/folio-core, onUnverified: "emit")',
    "superdoc-2.31.0": "superdoc-sdk 2.31.0",
    "word-mac": "Word for Mac's own compare (calibration, not a tool)",
}


def main() -> None:
    lines = []
    for test, (tool, action) in TESTS.items():
        doc = json.loads((HERE / f"scores_{test}.json").read_text())
        s = doc["summary"]
        itt = s["overall_itt"]
        lines.append(
            {
                "track": TRACK,
                "tool": tool,
                "action": action,
                "pairs": s["pairs"],
                "scored": s["scored"],
                "itt_mean": itt["mean"],
                "itt_median": itt["median"],
                "overall": s["overall"],
                "ink_jaccard": s.get("ink_jaccard"),
                "reference": s["reference"],
                "set": s["set"],
                "dpi": s["dpi"],
                "scorer": s["scorer"],
                "timestamp": "2026-11-24T11:17:10+00:00",
            }
        )
    (HERE / "scores.jsonl").write_text("".join(json.dumps(x) + "\n" for x in lines))
    (HERE / "versions.json").write_text(json.dumps(VERSIONS, indent=2) + "\n")


if __name__ == "__main__":
    main()

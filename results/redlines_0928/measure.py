"""Score the 0928 tool runs against Word, both tracks, with the bench's own scorers.

    uv run python results/redlines_0928/measure.py redlines jubarte-rust docxodus superdoc
    uv run python results/redlines_0928/measure.py accepted jubarte-rust docxodus superdoc

redlines: ``<tool>/pdf_by_word/<key>_<tool>.pdf`` (the tool's redline, rendered by Word) against
``oracle_pdf/<key>.pdf`` (Word's own compare, rendered by Word), through
``pipeline.score_folders_full``.

accepted: ``<tool>/accepted/by_word/<cmp>_accepted_tracking_<tool>.pdf`` (the tool's redline
with every change accepted by Word) against the corpus render of Word's own compare
accepted the same way (``corpus/word`` pool ``accepted_tracking_0928``), through
``pipeline.score_folders_plain`` on link folders named ``<cmp>.pdf``.

Each tool is scored in its own temporary work folder, so its rasters are gone before the
next tool starts. Writes ``scores_<track>_<tool>.json``: a summary and one row per pair
with the scalar columns of the score row; pairs of the pool without a candidate PDF are
listed as ``missing``.
"""

from __future__ import annotations

import csv
import json
import statistics
import sys
import tempfile
from pathlib import Path

from neurotic_docx_bench import pipeline

HERE = Path(__file__).parent
CORPUS = Path("corpus/word")
ACCEPTED_POOL = CORPUS / "pools" / "accepted_tracking_0928_renders.csv"


def _scalars(row: dict) -> dict:
    return {k: v for k, v in row.items() if isinstance(v, (int, float, str, bool)) or v is None}


def _summary(rows: dict[str, dict], expected: int) -> dict:
    overall = [pipeline.overall_from_result(r) for r in rows.values()]
    ink = [r["ink_jaccard"] for r in rows.values() if r.get("ink_jaccard") is not None]
    tb = [r["text_boundary"] for r in rows.values() if r.get("text_boundary") is not None]

    def stats(xs: list[float]) -> dict:
        if not xs:
            return {"n": 0}
        return {"n": len(xs), "mean": statistics.fmean(xs), "median": statistics.median(xs)}

    return {
        "pairs": expected,
        "scored": len(rows),
        "missing": expected - len(rows),
        "overall": stats(overall) | {
            "exact_100": sum(x >= 100 for x in overall),
            "at_least_90": sum(x >= 90 for x in overall),
            "below_50": sum(x < 50 for x in overall),
        },
        "ink_jaccard": stats(ink),
        "text_boundary": stats(tb),
    }


def _word_dir(tool: str, new: str, old: str) -> Path:
    """The Word-made folder: ``provenance.py --apply`` renames ``old`` to ``new``."""
    return HERE / tool / new if (HERE / tool / new).exists() else HERE / tool / old


def redlines(tool: str) -> tuple[dict, list[str]]:
    oracle = HERE / "oracle_pdf"
    keys = sorted(p.stem for p in oracle.glob("*.pdf"))
    with tempfile.TemporaryDirectory(prefix=f"measure-{tool}.") as work:
        rows = pipeline.score_folders_full(oracle, _word_dir(tool, "pdf_by_word", "pdf"), Path(work), candidate_tool=tool)
    return {k: _scalars(v) for k, v in rows.items()}, keys


def accepted(tool: str) -> tuple[dict, list[str]]:
    word = {}
    for row in csv.DictReader(open(ACCEPTED_POOL)):
        cmp_id = row["key"].split("_")[1]
        word[cmp_id] = CORPUS / row["pdf"]
    selected = sorted(p.stem for p in (HERE / tool / "accepted" / "src").glob("*.docx"))
    suffix = f"_accepted_tracking_{tool}"
    with tempfile.TemporaryDirectory(prefix=f"measure-acc-{tool}.") as tmp:
        o, c, work = (Path(tmp) / d for d in ("oracle", "candidate", "work"))
        for d in (o, c, work):
            d.mkdir()
        for cmp_id in selected:
            (o / f"{cmp_id}.pdf").symlink_to(word[cmp_id].resolve())
        for pdf in _word_dir(tool, "accepted/by_word", "accepted/out").glob(f"*{suffix}.pdf"):
            (c / f"{pdf.stem.removesuffix(suffix)}.pdf").symlink_to(pdf.resolve())
        rows = pipeline.score_folders_plain(o, c, work)
    return {k: _scalars(v) for k, v in rows.items()}, selected


def identity(tool: str) -> tuple[dict, list[str]]:
    """Control: Word's accepted renders scored against themselves (``tool`` is a label)."""
    selected = [row["pdf"] for row in csv.DictReader(open(ACCEPTED_POOL))]
    with tempfile.TemporaryDirectory(prefix="measure-identity.") as tmp:
        o, c, work = (Path(tmp) / d for d in ("oracle", "candidate", "work"))
        for d in (o, c, work):
            d.mkdir()
        for rel in selected:
            for d in (o, c):
                (d / Path(rel).name).symlink_to((CORPUS / rel).resolve())
        rows = pipeline.score_folders_plain(o, c, work)
    return {k: _scalars(v) for k, v in rows.items()}, [Path(r).stem for r in selected]


def main() -> None:
    track, tools = sys.argv[1], sys.argv[2:]
    run = {"redlines": redlines, "accepted": accepted, "identity": identity}[track]
    for tool in tools:
        rows, expected = run(tool)
        summary = _summary(rows, len(expected))
        out = HERE / f"scores_{track}_{tool}.json"
        missing = sorted(set(expected) - set(rows))
        out.write_text(json.dumps({"summary": summary, "missing": missing, "rows": rows}, indent=1, sort_keys=True))
        o = summary["overall"]
        print(
            f"{track} {tool}: {summary['scored']}/{summary['pairs']} scored, "
            f"mean {o.get('mean', 0):.2f}, median {o.get('median', 0):.2f}, "
            f"100: {o['exact_100'] if o['n'] else 0}, >=90: {o['at_least_90'] if o['n'] else 0} -> {out}"
        )


if __name__ == "__main__":
    main()

"""Copy the accepted-changes pairs where jubarte-rust trails another tool into jubarte-redlines.

    uv run python results/redlines_0928/export_jubarte_accepted_gaps.py [--dest DIR]

A pair is exported when jubarte-rust's accepted copy scores below 100 and below at least one
other tool's accepted copy of the same pair (docxodus, superdoc), or when jubarte-rust has no
accepted copy while another tool has one. Scores are the ``overall_from_result`` values in
``scores_accepted_<tool>.json`` (written by ``measure.py accepted``).

Every folder holds one file per pair, named by the compare id (``<cmp>.docx`` / ``<cmp>.pdf``)
so the same pair lines up across folders:

- ``_original_unaccepted_docx/``: Word's own compare of base and next, tracked changes intact.
- ``_word_sot_accepted_docx/``: that Word redline with every change accepted by Word (the
  source of truth the accepted track scores against).
- ``_jubarted_unaccepted_docx/``: jubarte-rust's redline of the same base and next.
- ``_jubarte_unaccepted_pdf/``: jubarte-rust's redline exported to PDF by Microsoft Word.
- ``_inputs_base_next_docx/``: ``<cmp>__base.docx`` and ``<cmp>__next.docx``, to rerun jubarte.
- ``_word_sot_accepted_pdf/``: the Word accepted copy exported to PDF by Word (the oracle).
- ``_jubarte_accepted_by_word/``: jubarte's redline with every change accepted by Word, DOCX
  and PDF (the candidate that was scored).

Writes ``notes.md`` and ``pairs.csv``. Refuses to write into an existing destination.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path

from neurotic_docx_bench import pipeline

HERE = Path(__file__).parent
CORPUS = Path("corpus/word")
POOL = CORPUS / "pools" / "accepted_tracking_0928_renders.csv"
SELECTION = HERE / "accept_selection.csv"
OTHERS = ["docxodus", "superdoc"]
VERSIONS = {
    "jubarte-rust": "jubarte-redlines 0.9.3 @673aff74 (native CLI)",
    "docxodus": "docxodus 12.6.4",
    "superdoc": "superdoc-sdk 2.15.0",
}


def word_dir(tool: str, new: str, old: str) -> Path:
    return HERE / tool / new if (HERE / tool / new).exists() else HERE / tool / old


def scores(tool: str) -> dict[str, dict]:
    path = HERE / f"scores_accepted_{tool}.json"
    return json.loads(path.read_text())["rows"] if path.exists() else {}


def fmt(x: float | None) -> str:
    return "n/a" if x is None else f"{x:.2f}"


def note(r: dict) -> str:
    if r["jubarte"] is None:
        return "Word crashes on accept"
    return "near tie" if r["gap"] < 1 else ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dest", type=Path, default=Path("../jubarte-redlines/_to_improve_accepted_changes"))
    args = ap.parse_args()
    if args.dest.exists():
        raise SystemExit(f"{args.dest} exists; move it aside first")

    selection = {row["id"]: row for row in csv.DictReader(SELECTION.open())}
    word_accepted = {row["key"].split("_")[1]: row for row in csv.DictReader(POOL.open())}
    rows = {t: scores(t) for t in ["jubarte-rust", *OTHERS]}
    jub_in = HERE / "jubarte-rust" / "accepted" / "src"
    jub_pdf = word_dir("jubarte-rust", "pdf_by_word", "pdf")
    jub_acc = word_dir("jubarte-rust", "accepted/by_word", "accepted/out")

    picked = []
    for cmp_id in sorted(p.stem for p in jub_in.glob("*.docx")):
        j = rows["jubarte-rust"].get(cmp_id)
        js = pipeline.overall_from_result(j) if j else None
        other = {t: pipeline.overall_from_result(rows[t][cmp_id]) for t in OTHERS if cmp_id in rows[t]}
        if not other:
            continue
        best_tool, best = max(other.items(), key=lambda kv: kv[1])
        if js is None or (js < 100 and best > js):
            picked.append((cmp_id, j, js, other, best_tool, best))

    folders = {
        name: args.dest / name
        for name in (
            "_original_unaccepted_docx",
            "_word_sot_accepted_docx",
            "_jubarted_unaccepted_docx",
            "_jubarte_unaccepted_pdf",
            "_inputs_base_next_docx",
            "_word_sot_accepted_pdf",
            "_jubarte_accepted_by_word",
        )
    }
    for d in folders.values():
        d.mkdir(parents=True)

    table, missing_files = [], []

    def copy(src: Path, folder: str, name: str) -> None:
        if src.exists():
            shutil.copy2(src, folders[folder] / name)
        else:
            missing_files.append(f"{folder}/{name} (no {src})")

    for cmp_id, j, js, other, best_tool, best in picked:
        sel, acc = selection[cmp_id], word_accepted[cmp_id]
        copy(CORPUS / sel["docx"], "_original_unaccepted_docx", f"{cmp_id}.docx")
        copy(CORPUS / acc["docx"], "_word_sot_accepted_docx", f"{cmp_id}.docx")
        copy(CORPUS / acc["pdf"], "_word_sot_accepted_pdf", f"{cmp_id}.pdf")
        copy(jub_in / f"{cmp_id}.docx", "_jubarted_unaccepted_docx", f"{cmp_id}.docx")
        copy(jub_pdf / f"{sel['key']}_jubarte-rust.pdf", "_jubarte_unaccepted_pdf", f"{cmp_id}.pdf")
        copy(CORPUS / f"{sel['base']}.docx", "_inputs_base_next_docx", f"{cmp_id}__base.docx")
        copy(CORPUS / f"{sel['next']}.docx", "_inputs_base_next_docx", f"{cmp_id}__next.docx")
        for ext in ("docx", "pdf"):
            copy(jub_acc / f"{cmp_id}_accepted_tracking_jubarte-rust.{ext}", "_jubarte_accepted_by_word", f"{cmp_id}.{ext}")
        table.append(
            {
                "cmp": cmp_id,
                "state": sel["state"],
                "jubarte": js,
                "docxodus": other.get("docxodus"),
                "superdoc": other.get("superdoc"),
                "best_other": best_tool,
                "gap": None if js is None else best - js,
                "jubarte_ink_jaccard": j.get("ink_jaccard") if j else None,
                "jubarte_text_boundary": j.get("text_boundary") if j else None,
                "pages_jubarte": j.get("page_count_candidate") if j else None,
                "pages_word": j.get("page_count_oracle") if j else None,
                "base": sel["base_name"],
                "next": sel["next_name"],
                "corpus_key": sel["key"],
            }
        )

    table.sort(key=lambda r: -(r["gap"] if r["gap"] is not None else 1e9))
    with (args.dest / "pairs.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(table[0]) if table else ["cmp"])
        w.writeheader()
        w.writerows(table)

    n_scored = {t: len(r) for t, r in rows.items()}
    lines = [
        "# Accepted-changes pairs where jubarte-rust trails another tool",
        "",
        "Exported from neurotic-docx-bench `results/redlines_0928` by",
        "`results/redlines_0928/export_jubarte_accepted_gaps.py` on 2026-09-28.",
        "",
        "## What the accepted-changes track measures",
        "",
        "100 pairs (base, next) were drawn from the Word corpus (`corpus/word`, set",
        "`accepted_tracking_0928`). For each pair Microsoft Word compared base with next (the",
        "redline in `_original_unaccepted_docx/`), and Word then accepted every tracked change",
        "(`_word_sot_accepted_docx/`, source of truth). Each tool redlined the same base and next;",
        "Word opened the tool's redline, accepted every change and exported a PDF. That PDF is",
        "scored against Word's accepted copy exported the same way. A tool whose redline records",
        "the edits faithfully accepts back into the next document, so a low score means content",
        "or formatting was lost or mis-recorded in the redline.",
        "",
        "Scores are the bench's page-fair overall score (0 to 100) from `pipeline.score_folders_plain`",
        "on 150 DPI rasters; ink_jaccard and text_boundary are docxide's metrics (0 to 1).",
        "",
        "## Selection",
        "",
        "A pair is here when jubarte-rust's accepted copy scores below 100 **and** below at least",
        "one other tool's accepted copy of the same pair, or when jubarte-rust has no accepted copy",
        "while another tool has one. Pairs no other tool scored are not here.",
        "",
        f"- Scored accepted copies: jubarte-rust {n_scored['jubarte-rust']}, docxodus {n_scored['docxodus']},"
        f" superdoc {n_scored['superdoc']} (of 100; superdoc refused most pairs when redlining).",
        "- docxodus has fewer because Word could not open 23 of its redlines cleanly; a second",
        "  attempt is queued, so this export can grow when it is rerun.",
        f"- Pairs exported: **{len(table)}**. {sum(r['gap'] is not None and r['gap'] < 1 for r in table)} of them"
        " trail by less than 1 point: both tools fail those pairs about equally, so they are jubarte",
        "  failures but not evidence that another tool does better (marked `near tie` below).",
        "- A jubarte score of `n/a` means Word crashed (\"Connection is invalid\") while accepting",
        "  every change of jubarte's redline, twice; the same redline exports to PDF without",
        "  trouble (`_jubarte_unaccepted_pdf/`). The Word-invalid part is in the tracked changes.",
        "",
        "Versions: " + "; ".join(f"{t} = {v}" for t, v in VERSIONS.items()) + "; Microsoft Word 16.114.",
        "",
        "## Folders (one file per pair, named by compare id)",
        "",
        "| Folder | Content | Made by |",
        "|---|---|---|",
        "| `_original_unaccepted_docx/` | Word's redline of base vs next, changes still tracked | Microsoft Word compare |",
        "| `_word_sot_accepted_docx/` | that redline with all changes accepted (source of truth) | Microsoft Word accept all |",
        "| `_jubarted_unaccepted_docx/` | jubarte-rust's redline of base vs next | jubarte-rust |",
        "| `_jubarte_unaccepted_pdf/` | jubarte-rust's redline exported to PDF | Microsoft Word (PDF export) |",
        "| `_inputs_base_next_docx/` | `<cmp>__base.docx`, `<cmp>__next.docx`, to rerun jubarte | corpus originals |",
        "| `_word_sot_accepted_pdf/` | Word accepted copy exported to PDF (the scoring oracle) | Microsoft Word (PDF export) |",
        "| `_jubarte_accepted_by_word/` | jubarte's redline with all changes accepted, DOCX and PDF (the scored candidate) | Microsoft Word accept all + PDF export |",
        "",
        "The last three folders were not in the request; they are the inputs and the two PDFs",
        "that were actually compared, so a gap can be reproduced and seen without rerunning Word.",
        "",
        "## Pairs (largest gap first)",
        "",
        "| cmp | state | jubarte | docxodus | superdoc | gap | note | ink_jaccard | text_boundary | pages j/w | base -> next |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in table:
        lines.append(
            f"| {r['cmp']} | {r['state']} | {fmt(r['jubarte'])} | {fmt(r['docxodus'])} | {fmt(r['superdoc'])}"
            f" | {fmt(r['gap'])} | {note(r)} | {fmt(r['jubarte_ink_jaccard'])} | {fmt(r['jubarte_text_boundary'])}"
            f" | {r['pages_jubarte']}/{r['pages_word']} | `{r['base'][:40]}` -> `{r['next'][:40]}` |"
        )
    if missing_files:
        lines += ["", "## Files that could not be copied", ""]
        lines += [f"- {m}" for m in missing_files]
    (args.dest / "notes.md").write_text("\n".join(lines) + "\n")
    print(f"{len(table)} pairs -> {args.dest}; {len(missing_files)} files missing")
    for m in missing_files:
        print("  missing:", m)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

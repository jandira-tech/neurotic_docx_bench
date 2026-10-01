"""Turn the scoring checkpoints of one engine into the two converter reports the ledger ingests.

Reads the pixel checkpoint (``docx_to_pdf_<name>.checkpoint.jsonl``), the docxide-metrics
checkpoint and the convert log, then writes ``docx_to_pdf_<name>_corpus-all.json`` and
``docxide_metrics_<name>_corpus-all.json`` with the same schema ``bench docx-to-pdf`` and
``bench docxide-metrics`` write, so ``bench ingest-converter-reports`` can append them.
A fixture without a candidate PDF is a generate failure and scores 0 (intent-to-treat).

    uv run python scripts/build_converter_reports.py --name docxide_0.17.1 --tool docxide-pdf \
        --version "docxide-pdf v0.17.1" --candidate results/docxide_0.17.1_work/candidate \
        --docxide-ckpt results/docxide_metrics_docxide-pdf_0.17.1.docxide.checkpoint.jsonl \
        --convert-log results/regen_others.log --engine docxide
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from neurotic_docx_bench import docx_to_pdf as d2p
from neurotic_docx_bench import docxide_metrics as dm

R = Path("results")


def rows(path: Path, field: str, key: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for line in path.read_text().splitlines():
        if line.endswith("}"):
            r = json.loads(line)
            out[r[key]] = r[field]
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", required=True)
    ap.add_argument("--tool", required=True)
    ap.add_argument("--version", required=True)
    ap.add_argument("--candidate", type=Path, required=True)
    ap.add_argument("--docxide-ckpt", type=Path, required=True)
    ap.add_argument("--convert-log", type=Path, required=True)
    ap.add_argument("--engine", choices=("docxide", "soffice"), required=True)
    args = ap.parse_args()

    base = json.loads((R / "docx_to_pdf_jubarte_0.10.1.json").read_text())
    dbase = json.loads((R / "docxide_metrics_jubarte_0.10.1.json").read_text())
    stems = base["stems"]
    errors: dict[str, str] = {}
    marker = f"with {args.engine}"
    section = False
    for line in args.convert_log.read_text().splitlines():
        if marker in line and "to convert" in line:
            section = True
        elif "to convert with" in line:
            section = False
        if section and line.startswith("FAILED "):
            stem, _, err = line[7:].partition(": ")
            errors[stem] = err
    have = {p.stem for p in args.candidate.glob("*.pdf")}
    failures = [
        {"doc": s, "stage": "generate", "error": errors.get(s, "no PDF written")} for s in stems if s not in have
    ]
    now = datetime.now(UTC).isoformat()

    pixel = {k: v["overall_score"] for k, v in rows(R / f"docx_to_pdf_{args.name}.checkpoint.jsonl", "result", "key").items()}
    pixel = {s: pixel[s] for s in stems if s in pixel}
    report = {k: base[k] for k in ("n", "oracle", "stems", "track", "warnings")} | {"generated_at": now}
    report["tools"] = {args.tool: d2p._tool_report(args.tool, None, stems, pixel, failures, version=args.version)}
    (R / f"docx_to_pdf_{args.name}_corpus-all.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    drows = rows(args.docxide_ckpt, "row", "stem")
    dreport = {k: v for k, v in dbase.items() if k != "tools"} | {"generated_at": now}
    dreport["tools"] = {args.tool: dm._tool_report(args.tool, None, stems, drows, failures, version=args.version)}
    (R / f"docxide_metrics_{args.name}_corpus-all.json").write_text(json.dumps(dreport, indent=2, sort_keys=True) + "\n")
    t, d = report["tools"][args.tool], dreport["tools"][args.tool]
    print(f"{args.tool}: pixel n_scored {t['n_scored']}/{t['itt_n']} failures {t['failures']}; "
          f"jaccard n_scored {d['n_scored']} failures {d['failures']}")


if __name__ == "__main__":
    main()

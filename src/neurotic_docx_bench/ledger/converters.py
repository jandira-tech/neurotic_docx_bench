"""Converter reports (docx_to_pdf, docx_to_pdf_no_redline_docs, docxide_metrics) become
append-only store lines, one per (report, tool), so the tables come from the store and
not from whichever JSON the last run wrote."""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from neurotic_docx_bench import version

DEFAULT_CONVERTERS_PATH = Path("results/converters.jsonl")
DOCXIDE_TRACK = "docxide_metrics"
DOCXIDE_PRIMARY = "jaccard"
DOCXIDE_SCORER = "docxide-150dpi"


def stems_docset_id(stems: Iterable[str]) -> str:
    return hashlib.sha256("\n".join(sorted(set(stems))).encode("utf-8")).hexdigest()[
        :12
    ]


def _num(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return default
    return float(value)


def _failed_docs(data: dict[str, Any]) -> list[str]:
    out: set[str] = set()
    failures: Any = data.get("generate_failures") or []
    for f in failures if isinstance(failures, list) else []:
        if isinstance(f, dict) and f.get("doc"):
            out.add(str(f["doc"]))
    return sorted(out)


def _pixel_scores(per_doc: dict[str, Any], failed: set[str]) -> dict[str, float]:
    out: dict[str, float] = {}
    for stem, value in per_doc.items():
        if isinstance(value, bool) or not isinstance(value, int | float):
            continue
        if str(stem) in failed:
            continue
        out[str(stem)] = float(value)
    return out


def _lens_scores(
    per_doc: dict[str, Any], lens: str, failed: set[str]
) -> dict[str, float]:
    out: dict[str, float] = {}
    for stem, entry in per_doc.items():
        if not isinstance(entry, dict) or str(stem) in failed:
            continue
        value = entry.get(lens)
        if isinstance(value, int | float) and not isinstance(value, bool):
            out[str(stem)] = float(value)
    return out


def lines_from_report(
    report: Mapping[str, Any],
    *,
    hardware: Mapping[str, object] | None,
    report_path: str,
) -> list[dict]:
    track = str(report.get("track") or "")
    stems = [str(s) for s in (report.get("stems") or [])]
    docset = stems_docset_id(stems) if stems else None
    ts = str(report.get("generated_at") or "")
    lines: list[dict] = []
    tools: Any = report.get("tools")
    if not isinstance(tools, dict):
        return lines
    for tool, raw_data in tools.items():
        if not isinstance(raw_data, dict):
            continue
        data: dict[str, Any] = raw_data
        per_doc_raw: Any = data.get("per_doc")
        per_doc: dict[str, Any] = per_doc_raw if isinstance(per_doc_raw, dict) else {}
        failed = _failed_docs(data)
        failed_set = set(failed)
        extra: dict[str, dict[str, float]] = {}
        if track == DOCXIDE_TRACK:
            metrics_raw: Any = data.get("metrics")
            metrics: dict[str, Any] = (
                metrics_raw if isinstance(metrics_raw, dict) else {}
            )
            primary_raw: Any = metrics.get(DOCXIDE_PRIMARY)
            primary: dict[str, Any] = (
                primary_raw if isinstance(primary_raw, dict) else {}
            )
            lens, scorer = DOCXIDE_PRIMARY, DOCXIDE_SCORER
            scores = _lens_scores(per_doc, DOCXIDE_PRIMARY, failed_set)
            mean = _num(primary.get("mean"))
            median = _num(primary.get("median"))
            for k, v in metrics.items():
                if k != DOCXIDE_PRIMARY and isinstance(v, dict):
                    extra[str(k)] = {
                        "mean": _num(v.get("mean")),
                        "median": _num(v.get("median")),
                    }
        else:
            lens, scorer = "pixel", "v1"
            scores = _pixel_scores(per_doc, failed_set)
            mean = _num(data.get("mean"))
            median = _num(data.get("median"))
        lines.append(
            {
                "source": "converter",
                "id_run": str(uuid.uuid7()),
                "track": track,
                "tool": str(tool),
                "version": data.get("version"),
                "timestamp": ts,
                "oracle": str(report.get("oracle") or ""),
                "dpi": report.get("dpi"),
                "docset_id": docset,
                "lens": lens,
                "scorer": scorer,
                "itt_n": int(_num(data.get("itt_n"))),
                "n_scored": int(_num(data.get("n_scored"), default=len(scores))),
                "failures": int(_num(data.get("failures"))),
                "failed_docs": failed,
                "mean": mean,
                "median": median,
                "perfects": int(_num(data.get("perfects"))),
                "scores": scores,
                "extra": extra,
                "hardware": dict(hardware) if hardware else None,
                "report_path": report_path,
                "bench_version": version.bench_version(),
            }
        )
    return lines


def append_report(
    path: Path,
    report: Mapping[str, Any],
    *,
    hardware: Mapping[str, object] | None,
    report_path: str,
) -> int:
    lines = lines_from_report(report, hardware=hardware, report_path=report_path)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("a", encoding="utf-8") as fh:
        fh.writelines(json.dumps(line) + "\n" for line in lines)
    return len(lines)

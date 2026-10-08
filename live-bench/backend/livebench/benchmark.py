# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
"""Sequential benchmark policy, independent of transport, disk and real tools."""

from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from livebench.models import Document, ToolFailure, batch_id, result_id


class Tools(Protocol):
    def perform(self, tool: str, operation: str, inputs: list[Path], output: Path) -> Path: ...
    def score(self, oracle: Path, candidate: Path, work: Path) -> dict: ...
    def functional(self, candidate: Path, previous: Path, current: Path, work: Path) -> dict: ...
    def artifacts(self, work: Path, prefix: str) -> list[dict]: ...


class Benchmark:
    def __init__(self, tools: Tools, clock: Callable[[], float], now: Callable[[], str]):
        self.tools, self.clock, self.now = tools, clock, now

    def run(
        self,
        run_id: str,
        sequence: int,
        size: int,
        previous: Document,
        current: Document,
        work: Path,
        phase: Callable[[str], None],
    ) -> dict[str, Any]:
        stages: list[dict] = []
        scores: list[dict] = []

        def perform(
            tool: str, operation: str, inputs: list[Path], name: str, target_tool: str | None = None
        ) -> Path | None:
            phase(f"{tool}:{operation}")
            start = self.clock()
            stage = {"tool": tool, "operation": operation}
            if target_tool:
                stage["target_tool"] = target_tool
            try:
                output = self.tools.perform(tool, operation, inputs, work / name)
                stage.update(status="ok", artifact=f"{run_id}/{sequence}/{name}")
            except ToolFailure as exc:
                output = None
                stage.update(status=exc.status, error=str(exc))
            stages.append({**stage, "duration_ms": round((self.clock() - start) * 1000, 3)})
            return output

        def score(
            tool: str,
            benchmark: str,
            candidate: Path | None,
            reference: Path | None,
            reference_tool: str | None,
            renderer: str | None,
            functional: dict | None = None,
        ):
            row = {
                "tool": tool,
                "benchmark": benchmark,
                "reference_tool": reference_tool,
                "reference_renderer": renderer,
                "overall": None,
                "status": "unavailable",
            }
            if functional is not None:
                row["functional"] = functional
            if reference is None:
                scores.append(row)
                return
            if tool == reference_tool:
                row.update(status="reference")
            elif candidate is None:
                failure = next(
                    (
                        s
                        for s in reversed(stages)
                        if s.get("target_tool", s["tool"]) == tool
                        and s["status"] != "ok"
                        and s["operation"] in ("compare", "convert", "redline_render")
                    ),
                    None,
                )
                status = failure["status"] if failure else "broken"
                row.update(status=status, overall=None if status in ("error", "unavailable") else 0)
            else:
                phase(f"{tool}:score_{benchmark}")
                start = self.clock()
                try:
                    metrics = self.tools.score(reference, candidate, work / f"score-{benchmark}-{tool}")
                    row.update(status="ok", overall=metrics["overall"], metrics=metrics)
                    stages.append(
                        {
                            "tool": tool,
                            "operation": f"score_{benchmark}",
                            "status": "ok",
                            "duration_ms": round((self.clock() - start) * 1000, 3),
                        }
                    )
                except ToolFailure as exc:
                    # A scoring infrastructure failure must never become a candidate zero.
                    stages.append(
                        {
                            "tool": "scorer",
                            "operation": f"score_{benchmark}",
                            "status": "error",
                            "error": str(exc),
                            "duration_ms": round((self.clock() - start) * 1000, 3),
                        }
                    )
                    row.update(status="error")
            scores.append(row)

        if current.path is None or current.security.get("status") == "rejected":
            stages.append(
                {
                    "tool": "safety" if current.path else "download",
                    "operation": "security_preflight" if current.path else "download",
                    "status": "broken",
                    "duration_ms": 0,
                    "error": current.error or "fixture download failed",
                }
            )
            for task, vendors in (
                ("convert", ("jubarte", "soffice", "docxide")),
                ("redline", ("jubarte", "docxodus", "superdoc-redlines")),
            ):
                for vendor in vendors:
                    score(vendor, task, None, None, None, None)
        else:
            word_pdf = perform("word", "convert", [current.path], "word-convert.pdf")
            lo_pdf = perform("soffice", "convert", [current.path], "soffice-convert.pdf")
            jub_pdf = perform("jubarte", "convert", [current.path], "jubarte-convert.pdf")
            docxide_pdf = perform("docxide", "convert", [current.path], "docxide-convert.pdf")
            reference = word_pdf or lo_pdf
            ref_tool = "word" if word_pdf else ("soffice" if lo_pdf else None)
            score("jubarte", "convert", jub_pdf, reference, ref_tool, ref_tool)
            score("soffice", "convert", lo_pdf, reference, ref_tool, ref_tool)
            score("docxide", "convert", docxide_pdf, reference, ref_tool, ref_tool)
            if previous.path is None or previous.security.get("status") == "rejected":
                stages.append(
                    {
                        "tool": "chain",
                        "operation": "compare",
                        "status": "unavailable",
                        "duration_ms": 0,
                        "error": "previous sampled fixture was not downloadable or failed safety preflight",
                    }
                )
                for vendor in ("jubarte", "docxodus", "superdoc-redlines"):
                    score(vendor, "redline", None, None, None, None)
            else:
                pair = [previous.path, current.path]
                word_docx = perform("word", "compare", pair, "word-redline.docx")
                docxodus_docx = perform("docxodus", "compare", pair, "docxodus-redline.docx")
                jubarte_docx = perform("jubarte", "compare", pair, "jubarte-redline.docx")
                superdoc_docx = perform(
                    "superdoc-redlines", "compare", pair, "superdoc-redlines-redline.docx"
                )
                word_redline_pdf = (
                    perform("word", "redline_render", [word_docx], "word-redline.pdf") if word_docx else None
                )
                # A Word renderer failure switches the entire redline cohort to one common renderer.
                redline_ref = "word" if word_redline_pdf else "docxodus"
                renderer = "word" if word_redline_pdf else "soffice"
                rendered = {}
                for vendor, docx in (
                    ("docxodus", docxodus_docx),
                    ("jubarte", jubarte_docx),
                    ("superdoc-redlines", superdoc_docx),
                ):
                    rendered[vendor] = (
                        perform(
                            renderer, "redline_render", [docx], f"{vendor}-redline-{renderer}.pdf", vendor
                        )
                        if docx
                        else None
                    )
                ref_pdf = word_redline_pdf if redline_ref == "word" else rendered["docxodus"]
                for vendor, docx in (
                    ("jubarte", jubarte_docx),
                    ("docxodus", docxodus_docx),
                    ("superdoc-redlines", superdoc_docx),
                ):
                    functional = None
                    if docx:
                        phase(f"{vendor}:functional")
                        start = self.clock()
                        try:
                            functional = self.tools.functional(
                                docx, previous.path, current.path, work / f"functional-{vendor}"
                            )
                        except ToolFailure as exc:
                            stages.append(
                                {
                                    "tool": "scorer",
                                    "target_tool": vendor,
                                    "operation": "functional",
                                    "status": "error",
                                    "error": str(exc),
                                    "duration_ms": round((self.clock() - start) * 1000, 3),
                                }
                            )
                    score(
                        vendor,
                        "redline",
                        rendered[vendor],
                        ref_pdf,
                        redline_ref if ref_pdf else None,
                        renderer if ref_pdf else None,
                        functional,
                    )
                if jubarte_docx:
                    perform("jubarte", "native_redline_render", [jubarte_docx], "jubarte-redline-native.pdf")
        return {
            "id": current.review_id or result_id(run_id, sequence),
            "run_id": run_id,
            "sequence": sequence,
            "batch_id": batch_id(run_id, sequence, size),
            "source": current.public(),
            "previous": previous.public(),
            "completed_at": self.now(),
            "stages": stages,
            "scores": scores,
            "artifacts": self.tools.artifacts(work, f"{run_id}/{sequence}"),
        }

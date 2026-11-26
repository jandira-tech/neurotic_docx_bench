#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
"""Report scheduled cells, observed outcomes and the predeclared harmful-edit margin."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from harness.grading import margin_check
from harness.ledger import read_jsonl
from harness.models import REFUSAL_CLASSES, GradeRecord, RunConfig, RunRecord


def _percent(numerator: int, denominator: int) -> str:
    return f"{100 * numerator / denominator:.1f}%" if denominator else "—"


def _table(headers, rows):
    return [
        "| " + " | ".join(map(str, headers)) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ] + ["| " + " | ".join(map(str, row)) + " |" for row in rows]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="report.py")
    parser.add_argument("--runs-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--margin-unintended",
        type=int,
        default=None,
        help="Must equal the margin recorded before execution.",
    )
    parser.add_argument(
        "--margin-preservation",
        type=int,
        default=None,
        help="Must equal the margin recorded before execution.",
    )
    args = parser.parse_args(argv)
    try:
        config = RunConfig.model_validate_json(
            (args.runs_root / "config.json").read_text()
        )
    except (OSError, ValueError) as exc:
        print(
            f"refusing report: invalid or unbound run configuration: {exc}",
            file=sys.stderr,
        )
        return 1
    for name in ("margin_unintended", "margin_preservation"):
        value = getattr(args, name)
        if value is not None and value != getattr(config, name):
            print(f"{name} differs from the predeclared RunConfig", file=sys.stderr)
            return 1
    runs = [
        RunRecord.model_validate(row)
        for row in read_jsonl(args.runs_root / "runs.jsonl")
    ]
    grades = [
        GradeRecord.model_validate(row)
        for row in read_jsonl(args.runs_root / "grades.jsonl")
    ]
    # Match by the whole scheduled identity, never a surviving-row denominator.
    by_cell = {(r.order_index, r.task_id, r.arm, r.repetition): r for r in runs}
    by_run = {g.run_id: g for g in grades}
    cells = [
        (e, by_cell.get((e.order_index, e.task_id, e.arm, e.repetition)))
        for e in config.order
    ]
    missing = [(e, r) for e, r in cells if r is None]
    lines = [
        "# Held-out pilot report",
        "",
        f"Scheduled: {len(cells)}. Runs recorded: {len(runs)}. Missing: {len(missing)}. Graded: {len(grades)}.",
        "",
        "## Scheduled cells",
        "",
    ]
    lines += _table(
        ["Order", "Task", "Arm", "Rep", "Run", "Grade"],
        [
            [
                e.order_index,
                e.task_id,
                e.arm,
                e.repetition,
                r.run_id if r else "missing",
                "graded" if r and r.run_id in by_run else "missing",
            ]
            for e, r in cells
        ],
    )
    lines += [
        "",
        "## Tool correctness, task completion, and claim accuracy per arm",
        "",
    ]

    def for_arm(arm):
        return [(e, r) for e, r in cells if e.arm == arm]

    rows = []
    for arm in ("A", "B"):
        subset = for_arm(arm)
        gs = [by_run[r.run_id] for _, r in subset if r and r.run_id in by_run]
        n = len(subset)
        rows.append(
            [
                arm,
                n,
                _percent(sum(g.tool_correctness_overall for g in gs), n),
                _percent(sum(g.task_completion_overall for g in gs), n),
                _percent(sum(g.claim_accuracy == "accurate" for g in gs), n),
                sum(bool(r and r.right_censored) for _, r in subset),
            ]
        )
    lines += _table(
        ["Arm", "Runs", "Tool OK", "Task OK", "Claim accurate", "Censored"], rows
    )
    lines += ["", "## Counts per family and arm", ""]
    # Family of missing cells is loaded from the immutable task manifest saved by run.py.
    task_families = config.task_families
    task_families.update({r.task_id: r.task_family for r in runs})
    families = sorted(set(task_families.values()) or {"unknown"})
    rows = []
    for family in families:
        for arm in ("A", "B"):
            subset = [
                (e, r)
                for e, r in for_arm(arm)
                if task_families.get(e.task_id, "unknown") == family
            ]
            rows.append(
                [
                    family,
                    arm,
                    len(subset),
                    sum(
                        bool(
                            r
                            and by_run.get(r.run_id)
                            and by_run[r.run_id].task_completion_overall
                        )
                        for _, r in subset
                    ),
                ]
            )
    lines += _table(["Family", "Arm", "Scheduled", "Task OK"], rows)
    lines += [
        "",
        "## Unintended edits and preservation defects (exposed snapshot dimensions only)",
        "",
    ]
    rows = []
    totals = {}
    for arm in ("A", "B"):
        gs = [by_run[r.run_id] for _, r in for_arm(arm) if r and r.run_id in by_run]
        assessed = [
            g
            for g in gs
            if g.preservation_status == "assessed"
            and g.unintended_edit_count is not None
            and g.preservation_defect_count is not None
        ]
        totals[arm] = {
            "unintended_edits": sum(g.unintended_edit_count or 0 for g in assessed),
            "preservation_defects": sum(
                g.preservation_defect_count or 0 for g in assessed
            ),
        }
        rows.append(
            [
                arm,
                len(assessed),
                len(for_arm(arm)) - len(assessed),
                totals[arm]["unintended_edits"] if assessed else "not assessed",
                totals[arm]["preservation_defects"] if assessed else "not assessed",
            ]
        )
    lines += _table(
        ["Arm", "Assessed", "Not assessed", "Unintended edits", "Preservation defects"],
        rows,
    )
    lines += ["", "## Unintended edits and preservation defects per family and arm", ""]
    rows = []
    for family in families:
        for arm in ("A", "B"):
            subset = [
                (e, r)
                for e, r in for_arm(arm)
                if task_families.get(e.task_id, "unknown") == family
            ]
            assessed = [
                by_run[r.run_id]
                for _, r in subset
                if r
                and r.run_id in by_run
                and by_run[r.run_id].preservation_status == "assessed"
                and by_run[r.run_id].unintended_edit_count is not None
                and by_run[r.run_id].preservation_defect_count is not None
            ]
            rows.append(
                [
                    family,
                    arm,
                    len(assessed),
                    len(subset) - len(assessed),
                    sum(g.unintended_edit_count or 0 for g in assessed)
                    if assessed
                    else "not assessed",
                    sum(g.preservation_defect_count or 0 for g in assessed)
                    if assessed
                    else "not assessed",
                ]
            )
    lines += _table(
        [
            "Family",
            "Arm",
            "Assessed",
            "Not assessed",
            "Unintended edits",
            "Preservation defects",
        ],
        rows,
    )
    unassessed = sorted({item for g in grades for item in g.unassessed})
    lines += [
        "",
        "Not assessed: "
        + (
            ", ".join(unassessed)
            if unassessed
            else "unavailable snapshot dimensions; no broad preservation claim"
        ),
        "",
        "## Refusal classes per arm",
        "",
    ]
    rows = []
    for arm in ("A", "B"):
        counts = Counter(
            by_run[r.run_id].refusal_class or "(none)"
            for _, r in for_arm(arm)
            if r and r.run_id in by_run
        )
        rows.append([arm] + [counts[label] for label in (*REFUSAL_CLASSES, "(none)")])
    lines += _table(["Arm", *REFUSAL_CLASSES, "(none)"], rows)
    lines += [
        "",
        "## Regression margin",
        "",
        f"Predeclared margin: unintended={config.margin_unintended}, preservation={config.margin_preservation}.",
    ]
    incomplete = (
        not cells
        or bool(missing)
        or any(
            r is None
            or r.run_id not in by_run
            or by_run[r.run_id].preservation_status != "assessed"
            or by_run[r.run_id].unintended_edit_count is None
            or by_run[r.run_id].preservation_defect_count is None
            or any(e.adjudication_required for e in by_run[r.run_id].unintended_edits)
            for _, r in cells
        )
    )
    # A one-arm smoke and unpaired/censored cells cannot establish a paired gate.
    pairs = Counter((e.task_id, e.repetition) for e, _ in cells)
    incomplete |= any(n != 2 for n in pairs.values()) or any(
        r and r.right_censored for _, r in cells
    )
    if incomplete:
        lines.append(
            "**Gate: INCONCLUSIVE** — missing/unassessed, unpaired, censored or ambiguous outcomes remain; unavailable measurements are not zeros."
        )
    else:
        result = margin_check(
            arm_a=totals["A"],
            arm_b=totals["B"],
            margin_unintended=config.margin_unintended,
            margin_preservation=config.margin_preservation,
        )
        lines.append(
            f"**Gate: {'PASS' if result.passed else 'FAIL'}** — {result.reason}"
        )
    lines += [
        "",
        "Expand trials where release-relevant uncertainty remains. This initial pilot supports no universal effect-size claim.",
        "",
        "## Right-censored runs (timeout / cancelled)",
        "",
    ]
    lines += _table(
        ["Run", "Task", "Arm", "Stop reason"],
        [[r.run_id, r.task_id, r.arm, r.stop_reason] for r in runs if r.right_censored],
    )
    lines += ["", "## Inspection errors", ""]
    lines += _table(
        ["Run", "Error"],
        [[g.run_id, error] for g in grades for error in g.inspection_errors],
    )
    lines += ["", "## Claim accuracy detail", ""]
    counts = Counter(g.claim_accuracy for g in grades)
    lines += _table(
        ["Outcome", "Runs"],
        [[x, counts[x]] for x in ("accurate", "inaccurate", "missing")],
    )
    lines += [
        "",
        "Missing artifacts, missing grades and right-censored cells remain in scheduled denominators. Rubric items are unassessed until independently adjudicated. Any LLM rubric requires an independent artifact-sample audit.",
        "",
    ]
    text = "\n".join(lines)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

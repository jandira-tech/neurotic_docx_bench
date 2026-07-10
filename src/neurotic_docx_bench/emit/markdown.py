"""Human-readable Markdown report for a JSONL line (or a set of them)."""

from __future__ import annotations


def render_markdown(line: dict) -> str:
    """Render one tool-run line as a Markdown section."""
    agg = line.get("aggregate", {})
    lines = [
        f"## {line.get('tool')}  ({line.get('render')})",
        "",
        f"- **version:** {line.get('tool_version') or 'n/a'}",
        f"- **docs:** {line.get('n_docs')}",
        f"- **baseline:** `{line.get('baseline_ref')}`",
        "",
        "| metric | value |",
        "| --- | ---: |",
    ]
    for key in (
        "overall_mean",
        "overall_median",
        "page_mean",
        "page_median",
        "exact_100",
        "at_least_90",
        "below_50",
        "min",
        "max",
        "std",
        "q1",
        "q3",
    ):
        if key in agg:
            lines.append(f"| {key} | {agg[key]} |")
    return "\n".join(lines) + "\n"


def render_markdown_all(lines: list[dict]) -> str:
    return "\n".join(render_markdown(ln) for ln in lines)

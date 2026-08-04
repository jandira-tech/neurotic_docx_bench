"""Aggregate the folio apples-to-apples comparison into results-compare/COMPARISON.md.

Inputs (all under results-compare/):
  bench.jsonl                       — canonical bench rows (scores + per-doc timings)
  cdp_<tool>_<benchmark>.jsonl      — Chrome-DevTools per-doc metrics
  lighthouse/<tool>_run<i>.json     — Lighthouse performance runs
  *_rusage_*.txt                    — /usr/bin/time -l peak-RSS captures
  word_validate_<tool>_<what>.jsonl — Word-validity gate results
  bundle_sizes.json                 — production vite build output sizes (optional)

Baseline = tool_version 0.3.1 (core) / 0.5.0 (react); current = 0.11.0 / 0.10.2.
"""

from __future__ import annotations

import json
import re
import statistics
from pathlib import Path

RC = Path(__file__).resolve().parent.parent / "results-compare"

BASE_VERSIONS = {"0.3.1", "0.5.0"}
CURR_VERSIONS = {"0.11.0", "0.10.2"}
# The jubarte-wasm pkg version (folio orchestrator + forced jubarte-wasm lane).
WASM_VERSIONS = {"0.1.0"}

SIDES = ("baseline", "current", "folio-wasm")


def side_of(version: str | None) -> str | None:
    if version in BASE_VERSIONS:
        return "baseline"
    if version in CURR_VERSIONS:
        return "current"
    if version in WASM_VERSIONS:
        return "folio-wasm"
    return None


def fmt(v, nd=2):
    if v is None:
        return "—"
    return f"{v:.{nd}f}" if isinstance(v, float) else str(v)


def pct(vals: list[float], p: float) -> float | None:
    if not vals:
        return None
    s = sorted(vals)
    idx = min(len(s) - 1, max(0, round(p / 100 * (len(s) - 1))))
    return s[idx]


def load_bench_rows() -> dict[tuple[str, str], dict]:
    """(side, benchmark) -> newest row."""
    rows: dict[tuple[str, str], dict] = {}
    path = RC / "bench.jsonl"
    if not path.exists():
        return rows
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        version = str(d.get("tool_version"))
        side = side_of(version)
        if side is None:
            continue
        # Every playwright run ALSO emits its scores under the script_redlines
        # label (bench artifact: _execute_run always scores vs source_of_truth).
        # The real script_redlines lanes are the headless (core-version) rows —
        # drop the react-version duplicates.
        if d["benchmark"] == "script_redlines" and version in {"0.5.0", "0.10.2"}:
            continue
        rows[(side, d["benchmark"])] = d  # newest wins
    return rows


def timing_stats(row: dict, key: str) -> dict[str, float] | None:
    vals = [t[key] for t in (row.get("timings") or {}).values() if t.get(key) is not None]
    if not vals:
        return None
    return {
        "median_s": statistics.median(vals),
        "mean_s": statistics.fmean(vals),
        "p95_s": pct(vals, 95),
        "max_s": max(vals),
        "n": len(vals),
    }


def load_cdp() -> dict[tuple[str, str], list[dict]]:
    out: dict[tuple[str, str], list[dict]] = {}
    for p in sorted(RC.glob("cdp_*.jsonl")):
        for line in p.read_text().splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            key = (d["tool"], d["benchmark"])
            out.setdefault(key, []).append(d)
    return out


def cdp_summary(rows: list[dict]) -> dict:
    ok = [r for r in rows if r.get("ok")]
    heap = [r["metrics_after_gc"]["JSHeapUsedSize"] / 1e6 for r in ok]
    heap_delta = [
        (r["metrics_after_gc"]["JSHeapUsedSize"] - r["metrics_baseline"]["JSHeapUsedSize"]) / 1e6
        for r in ok
    ]
    render = [r["render_ms"] for r in ok]
    script = [r["metrics_after_render"]["ScriptDuration"] * 1000 for r in ok]
    layout = [r["metrics_after_render"]["LayoutDuration"] * 1000 for r in ok]
    nodes = [r["metrics_after_gc"]["Nodes"] for r in ok]
    return {
        "n": len(ok),
        "fail": len(rows) - len(ok),
        "render_ms_median": pct(render, 50),
        "render_ms_p95": pct(render, 95),
        "render_ms_max": max(render) if render else None,
        "heap_mb_median": pct(heap, 50),
        "heap_mb_p95": pct(heap, 95),
        "heap_mb_max": max(heap) if heap else None,
        "heap_delta_mb_median": pct(heap_delta, 50),
        "heap_delta_mb_max": max(heap_delta) if heap_delta else None,
        "script_ms_median": pct(script, 50),
        "layout_ms_median": pct(layout, 50),
        "dom_nodes_median": pct(nodes, 50),
    }


def load_lighthouse() -> dict[str, dict]:
    out: dict[str, list[dict]] = {}
    for p in sorted((RC / "lighthouse").glob("*_run*.json")) if (RC / "lighthouse").is_dir() else []:
        tool = re.sub(r"_run\d+\.json$", "", p.name)
        d = json.loads(p.read_text())
        audits = d.get("audits", {})

        def num(aid):
            a = audits.get(aid) or {}
            return a.get("numericValue")

        out.setdefault(tool, []).append(
            {
                "perf": (d.get("categories", {}).get("performance", {}) or {}).get("score"),
                "fcp_ms": num("first-contentful-paint"),
                "lcp_ms": num("largest-contentful-paint"),
                "tbt_ms": num("total-blocking-time"),
                "si_ms": num("speed-index"),
                "bootup_ms": num("bootup-time"),
                "mainthread_ms": num("mainthread-work-breakdown"),
                "bytes_total": num("total-byte-weight"),
            },
        )
    med: dict[str, dict] = {}
    for tool, runs in out.items():
        med[tool] = {
            k: (statistics.median([r[k] for r in runs if r[k] is not None]) if any(r[k] is not None for r in runs) else None)
            for k in runs[0]
        }
        med[tool]["n_runs"] = len(runs)
    return med


def load_rusage() -> dict[str, dict]:
    out = {}
    for p in sorted(RC.glob("**/*rusage*.txt")) + sorted(
        Path("runs-compare").glob("*/generate_rusage.txt"),
    ):
        text = p.read_text()
        peak = re.search(r"(\d+)\s+maximum resident set size", text)
        real = re.search(r"([\d.]+)\s+real", text)
        out[str(p)] = {
            "peak_rss_mb": int(peak.group(1)) / 1e6 if peak else None,
            "real_s": float(real.group(1)) if real else None,
        }
    return out


def load_word_validate() -> dict[str, dict]:
    out = {}
    for p in sorted(RC.glob("word_validate_*.jsonl")):
        rows = [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
        ok = sum(1 for r in rows if r["word_valid"])
        out[p.stem.replace("word_validate_", "")] = {
            "n": len(rows),
            "valid": ok,
            "invalid": len(rows) - ok,
            "invalid_docs": [r["doc"] for r in rows if not r["word_valid"]][:20],
        }
    return out


def main() -> None:
    bench = load_bench_rows()
    cdp = load_cdp()
    lh = load_lighthouse()
    rusage = load_rusage()
    wv = load_word_validate()

    lines: list[str] = []
    add = lines.append
    add("# folio apples-to-apples: vendored bench folio vs current build")
    add("")
    add("Baseline = `src/neurotic_docx_bench/utils/folio` (folio-core 0.3.1, folio-react 0.5.0, agents 0.1.0).")
    add("Current = `reconciliation_plan/folio` working tree (folio-core 0.11.0, folio-react 0.10.2, agents 0.6.1), staged identically.")
    add("Same corpora, same oracle, same scoring (144 dpi), same harness contract, same machine, same session.")
    add("")

    # ── fidelity scores ──
    add("## Fidelity scores (0-100 vs Word oracle)")
    add("")
    add("| benchmark | side | docs | mean | median | ≥90 | =100 | <50 | failures |")
    add("|---|---|---|---|---|---|---|---|---|")
    for benchmark in [
        "script_redlines",
        "accepted_changes",
        "roundtrip",
        "visual_rendering",
        "visual_redlines",
        "visual_accepted_changes",
    ]:
        for s in SIDES:
            row = bench.get((s, benchmark))
            if not row:
                if s == "folio-wasm":
                    continue  # wasm lane only runs the generator benchmarks
                add(f"| {benchmark} | {s} | — | — | — | — | — | — | — |")
                continue
            failures = row.get("failures")
            nfail = len(failures) if isinstance(failures, list) else (failures or 0)
            add(
                f"| {benchmark} | {s} | {row.get('n_docs')} | {fmt(row.get('overall_mean'))} | "
                f"{fmt(row.get('overall_median'))} | {row.get('at_least_90')} | {row.get('exact_100')} | "
                f"{row.get('below_50')} | {nfail} |",
            )
    add("")

    # ── pipeline timings from bench rows ──
    add("## Pipeline timings (bench-measured, per document)")
    add("")
    add("| benchmark | side | step | n | median s | mean s | p95 s | max s |")
    add("|---|---|---|---|---|---|---|---|")
    for benchmark in ["script_redlines", "visual_rendering", "visual_redlines", "visual_accepted_changes"]:
        for s in SIDES:
            row = bench.get((s, benchmark))
            if not row:
                continue
            for step in ("generate_s", "render_s"):
                st = timing_stats(row, step)
                if not st:
                    continue
                add(
                    f"| {benchmark} | {s} | {step} | {st['n']} | {fmt(st['median_s'], 3)} | "
                    f"{fmt(st['mean_s'], 3)} | {fmt(st['p95_s'], 3)} | {fmt(st['max_s'], 3)} |",
                )
    add("")

    # ── CDP ──
    if cdp:
        add("## Chrome DevTools (CDP) per-document metrics — viewer harness")
        add("")
        add(
            "| benchmark | side | n | fail | render ms med | render ms p95 | render ms max | "
            "postGC heap MB med | p95 | max | heap Δ MB med | script ms med | layout ms med | DOM nodes med |",
        )
        add("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        order = sorted(cdp.keys(), key=lambda k: (k[1], k[0]))
        for tool, benchmark in order:
            s = cdp_summary(cdp[(tool, benchmark)])
            side = "baseline" if "base" in tool else "current"
            add(
                f"| {benchmark} | {side} | {s['n']} | {s['fail']} | {fmt(s['render_ms_median'], 0)} | "
                f"{fmt(s['render_ms_p95'], 0)} | {fmt(s['render_ms_max'], 0)} | {fmt(s['heap_mb_median'], 1)} | "
                f"{fmt(s['heap_mb_p95'], 1)} | {fmt(s['heap_mb_max'], 1)} | {fmt(s['heap_delta_mb_median'], 1)} | "
                f"{fmt(s['script_ms_median'], 0)} | {fmt(s['layout_ms_median'], 0)} | {fmt(s['dom_nodes_median'], 0)} |",
            )
        add("")

    # ── lighthouse ──
    if lh:
        add("## Lighthouse (harness page, desktop preset, median of runs)")
        add("")
        add("| side | perf score | FCP ms | LCP ms | TBT ms | speed index | bootup ms | main-thread ms | total bytes |")
        add("|---|---|---|---|---|---|---|---|---|")
        for tool in sorted(lh):
            m = lh[tool]
            side = "baseline" if "base" in tool else "current"
            add(
                f"| {side} | {fmt(m['perf'])} | {fmt(m['fcp_ms'], 0)} | {fmt(m['lcp_ms'], 0)} | "
                f"{fmt(m['tbt_ms'], 0)} | {fmt(m['si_ms'], 0)} | {fmt(m['bootup_ms'], 0)} | "
                f"{fmt(m['mainthread_ms'], 0)} | {fmt(m['bytes_total'], 0)} |",
            )
        add("")

    # ── bundle sizes ──
    bundle = RC / "bundle_sizes.json"
    if bundle.exists():
        add("## Production bundle (vite build of the harness)")
        add("")
        add("| side | JS bytes | CSS bytes | total bytes |")
        add("|---|---|---|---|")
        for side, d in json.loads(bundle.read_text()).items():
            add(f"| {side} | {d['js']} | {d['css']} | {d['total']} |")
        add("")

    # ── memory (rusage) ──
    if rusage:
        add("## Node generator memory (/usr/bin/time -l)")
        add("")
        add("| capture | peak RSS MB | wall s |")
        add("|---|---|---|")
        for path, d in rusage.items():
            add(f"| {Path(path).name} ({Path(path).parent.name}) | {fmt(d['peak_rss_mb'], 0)} | {fmt(d['real_s'], 1)} |")
        add("")

    # ── word validity ──
    if wv:
        add("## Word validity (Microsoft Word open gate)")
        add("")
        add("| artifact set | n | valid | invalid | first invalid docs |")
        add("|---|---|---|---|---|")
        for name, d in sorted(wv.items()):
            docs = ", ".join(d["invalid_docs"]) if d["invalid_docs"] else "—"
            add(f"| {name} | {d['n']} | {d['valid']} | {d['invalid']} | {docs} |")
        add("")

    out = RC / "COMPARISON.md"
    out.write_text("\n".join(lines) + "\n")
    print(f"wrote {out} ({len(lines)} lines)")


if __name__ == "__main__":
    main()

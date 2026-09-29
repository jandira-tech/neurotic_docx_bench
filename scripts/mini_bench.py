# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
"""DOCX->PDF mini-bench: the worst n documents of one converter run, plus n/4 spread
over the rest of its distribution, converted by every tool and scored by both scorers.

    uv run python scripts/mini_bench.py select --run 01a0e620 --n 200 --out results/mini_bench/<name>
    uv run python scripts/mini_bench.py convert --out results/mini_bench/<name> [--tools a,b] [--jubarte BIN]
    uv run python scripts/mini_bench.py score --out results/mini_bench/<name> [--tools a,b]

``select`` reads one ``results/converters.jsonl`` line (``--run`` is an ``id_run``
prefix; its ``scores`` map is ``<state>__<stem>`` -> score, failed documents count 0),
sorts ascending (ties by key) and keeps the first n (``worst``) and the midpoint of each
of n/4 equal strata of the rest (``spread``). It writes ``selection.csv`` (every document
by name, with its source score) and ``files.txt`` (the Word PDFs, the
``--origin list --files-list`` input of ``bench docx-to-pdf``), so the set reproduces.

``convert`` writes ``<out>/pdf/<tool>/<state>__<stem>.pdf`` and one ``convert.jsonl``
row per document and tool (ok, ms, error), with a per-call timeout. The CLI tools use
``docx_to_pdf.convert_command``; ``soffice`` runs headless with its own profile;
``office2pdf-lib`` is office2pdf as a library, in-process (``tools/d2p-warm``, the
``office2pdf::convert_bytes`` call of the crate README). Conversions are sequential, so
the ms column is a single-load figure, not the speed benchmark.

``score`` runs ``docx_to_pdf.run_eval`` (pixel scorer) and ``docxide_metrics.run_eval``
(Jaccard / text boundary) in score-only mode over the whole selection: a document a tool
did not convert is scored 0 (intent-to-treat). Rasters live in a temporary folder that
is removed after each tool. Reports go to ``<out>/reports/``, one ledger line per tool
and scorer to ``<out>/converters.jsonl`` (not the main ``results/converters.jsonl``, so
a 250-document run never stands in for a full-corpus row), and ``SUMMARY.md``.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import selectors
import shutil
import signal
import statistics
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus" / "word"
WARM_BIN = ROOT / "tools" / "d2p-warm" / "bin"
# pymupdf-pro joins only a --max-pages <= 3 selection: unlicensed it converts only the
# first 3 pages, and the pixel scorer compares min(pages), so on a longer document it
# would be scored on a truncated copy.
DEFAULT_TOOLS = (
    "jubarte",
    "docxide-pdf",
    "soffice",
    "office2pdf",
    "office2pdf-lib",
    "genoffice",
    "rdocx",
    "dxpdf",
    "pdfitdown",
    "libreoffice_convert_rust",
    "doxx",
)


@dataclass(frozen=True)
class Pick:
    key: str
    score: float
    rank: int  # 1-based position in the ascending source ranking
    bucket: str  # worst | spread


def split_key(key: str) -> tuple[str, str]:
    state, sep, stem = key.partition("__")
    if not sep:
        raise ValueError(f"not a <state>__<stem> key: {key}")
    return state, stem


def filter_pages(scores: dict[str, float], pages_of, max_pages: int | None) -> dict[str, float]:
    """Keep documents whose Word PDF has at most ``max_pages`` pages (None keeps all)."""
    if max_pages is None:
        return dict(scores)
    return {k: v for k, v in scores.items() if pages_of(k) <= max_pages}


def _word_pdf_pages(key: str) -> int:
    import pymupdf

    state, stem = split_key(key)
    with pymupdf.open(CORPUS / state / "pdf" / f"{stem}.pdf") as doc:
        return doc.page_count


def select_docs(scores: dict[str, float], n: int, failed: list[str] | tuple[str, ...] = ()) -> list[Pick]:
    """The n lowest scores, then the midpoint of each of n//4 equal strata of the rest."""
    merged = dict(scores)
    for key in failed:
        merged.setdefault(key, 0.0)
    ranked = sorted(merged.items(), key=lambda kv: (kv[1], kv[0]))
    worst = [Pick(k, s, i + 1, "worst") for i, (k, s) in enumerate(ranked[:n])]
    rest = ranked[n:]
    m = min(n // 4, len(rest))
    spread = []
    for j in range(m):
        idx = int((j + 0.5) * len(rest) / m)
        k, s = rest[idx]
        spread.append(Pick(k, s, n + idx + 1, "spread"))
    return worst + spread


def _run_line(prefix: str) -> dict:
    rows = [json.loads(ln) for ln in open(ROOT / "results" / "converters.jsonl") if ln.strip()]
    hits = [r for r in rows if r["id_run"].startswith(prefix)]
    if len(hits) != 1:
        raise SystemExit(f"--run {prefix}: {len(hits)} converters.jsonl lines match (need exactly 1)")
    return hits[0]


def cmd_select(args: argparse.Namespace) -> None:
    line = _run_line(args.run)
    failed = [f["doc"] if isinstance(f, dict) else f for f in line.get("failed_docs") or []]
    pool = {**{k: 0.0 for k in failed}, **line["scores"]}
    pool = filter_pages(pool, _word_pdf_pages, args.max_pages)
    picks = select_docs(pool, args.n)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    missing = []
    with open(out / "selection.csv", "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["bucket", "rank", "key", "source_score", "docx", "pdf"])
        for p in picks:
            state, stem = split_key(p.key)
            docx = CORPUS / state / "docx" / f"{stem}.docx"
            pdf = CORPUS / state / "pdf" / f"{stem}.pdf"
            if not (docx.is_file() and pdf.is_file()):
                missing.append(p.key)
            w.writerow([p.bucket, p.rank, p.key, round(p.score, 4), docx.relative_to(ROOT), pdf.relative_to(ROOT)])
    if missing:
        raise SystemExit(f"{len(missing)} selected document(s) lack their docx or Word PDF, first {missing[0]}")
    (out / "files.txt").write_text(
        "".join(f"{(CORPUS / split_key(p.key)[0] / 'pdf' / (split_key(p.key)[1] + '.pdf')).relative_to(ROOT)}\n" for p in picks)
    )
    meta = {
        "source_run": line["id_run"],
        "source_track": line["track"],
        "source_tool": line["tool"],
        "source_version": line["version"],
        "source_lens": line["lens"],
        "source_docset": line.get("docset_id"),
        "source_itt_n": line["itt_n"],
        "max_pages": args.max_pages,
        "pool_after_page_filter": len(pool),
        "n_worst": sum(p.bucket == "worst" for p in picks),
        "n_spread": sum(p.bucket == "spread" for p in picks),
        "rule": "ascending (score, key); worst = first n; spread = midpoint of each of n//4 equal strata of the rest",
    }
    (out / "selection.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(f"selected {len(picks)} ({meta['n_worst']} worst + {meta['n_spread']} spread) from {line['tool']} {line['version']} → {out}")


def _selection(out: Path) -> list[dict]:
    return list(csv.DictReader(open(out / "selection.csv")))


def _capped(cmd: list[str], timeout: float, cwd: Path | None = None) -> tuple[int, str, bool]:
    """Run in its own process group; past ``timeout`` SIGKILL the group (helpers included)."""
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True, cwd=cwd)
    try:
        text, _ = proc.communicate(timeout=timeout)
        return proc.returncode, text or "", False
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        return -9, f"timeout after {timeout}s", True


def _is_pdf(p: Path) -> bool:
    return p.is_file() and p.stat().st_size > 0 and p.read_bytes()[:5] == b"%PDF-"


class LibWorker:
    """tools/d2p-warm worker: ``src\\tdst`` in, ``ok <ms>`` / ``err <ms> <msg>`` out."""

    def __init__(self, tool: str, timeout: float) -> None:
        self.tool, self.timeout, self.proc = tool, timeout, None

    def convert(self, src: Path, dst: Path) -> tuple[bool, str]:
        if self.proc is None or self.proc.poll() is not None:
            self.proc = subprocess.Popen(
                [str(WARM_BIN / f"d2p-warm-{self.tool}"), self.tool],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1,
            )
        self.proc.stdin.write(f"{src}\t{dst}\n")
        self.proc.stdin.flush()
        sel = selectors.DefaultSelector()
        sel.register(self.proc.stdout, selectors.EVENT_READ)
        ready = sel.select(self.timeout)
        sel.close()
        line = self.proc.stdout.readline() if ready else ""
        if not line:
            self.proc.kill()
            self.proc.wait()
            self.proc = None
            return False, f"timeout after {self.timeout}s or worker died"
        status, _ms, *msg = line.rstrip("\n").split(" ", 2)
        return status == "ok", (msg[0] if msg else "")

    def close(self) -> None:
        if self.proc is not None and self.proc.poll() is None:
            self.proc.stdin.close()
            self.proc.wait()


LIB_TOOLS = {"office2pdf-lib": "office2pdf"}


def versions(tools: list[str], jubarte: Path | None) -> dict[str, str]:
    from neurotic_docx_bench import docx_to_pdf as d2p

    out = {}
    for t in tools:
        if t == "soffice":
            out[t] = subprocess.run(["soffice", "--version"], capture_output=True, text=True).stdout.strip()
        elif t == "genoffice":
            out[t] = subprocess.run(["genoffice", "--version"], capture_output=True, text=True).stdout.strip()
        elif t in LIB_TOOLS:
            lock = (ROOT / "tools" / "d2p-warm" / "Cargo.lock").read_text()
            crate = LIB_TOOLS[t]
            ver = next((b.split('version = "')[1].split('"')[0] for b in lock.split("[[package]]") if f'name = "{crate}"\n' in b), "?")
            out[t] = f"{crate} {ver} (library, tools/d2p-warm)"
        elif t == "docxide-pdf":
            meta = subprocess.run(["cargo", "install", "--list"], capture_output=True, text=True).stdout
            out[t] = next((ln.rstrip(":") for ln in meta.splitlines() if ln.startswith("docxide-pdf ")), "docxide-pdf")
        else:
            binary = jubarte if (t == "jubarte" and jubarte) else d2p.resolve_tool_binary(t)
            out[t] = d2p.tool_version(binary) or Path(binary).name
            if t == "jubarte" and jubarte and "-" in Path(jubarte).name:
                out[t] += "@" + Path(jubarte).name.rsplit("-", 1)[1]
    return out


def cmd_convert(args: argparse.Namespace) -> None:
    from neurotic_docx_bench import docx_to_pdf as d2p

    out = Path(args.out)
    rows = _selection(out)
    if args.tools:
        tools = args.tools.split(",")
    else:
        max_pages = json.loads((out / "selection.json").read_text()).get("max_pages")
        tools = [*DEFAULT_TOOLS, *(["pymupdf-pro"] if max_pages is not None and max_pages <= 3 else [])]
    jubarte =Path(args.jubarte).resolve() if args.jubarte else None
    vers = versions(tools, jubarte)
    (out / "versions.json").write_text(json.dumps(vers, indent=2) + "\n")
    log = open(out / "convert.jsonl", "a")
    for tool in tools:
        dest_dir = out / "pdf" / tool
        dest_dir.mkdir(parents=True, exist_ok=True)
        lo_tmp = Path(tempfile.mkdtemp(prefix=f"mini-{tool}.")) if tool == "soffice" else None
        worker = LibWorker(LIB_TOOLS[tool], args.timeout) if tool in LIB_TOOLS else None
        binary = None
        if tool not in LIB_TOOLS and tool not in ("soffice",):
            binary = jubarte if (tool == "jubarte" and jubarte) else d2p.resolve_tool_binary(tool)
        ok_n = 0
        for i, r in enumerate(rows, 1):
            src = (ROOT / r["docx"]).resolve()
            dst = dest_dir / f"{r['key']}.pdf"
            if _is_pdf(dst):
                ok_n += 1
                continue
            dst.unlink(missing_ok=True)
            t0 = time.perf_counter()
            if worker is not None:
                ok, err = worker.convert(src, dst)
            elif tool == "soffice":
                rc, text, _ = _capped(
                    ["soffice", f"-env:UserInstallation=file://{lo_tmp / 'profile'}", "--headless",
                     "--convert-to", "pdf", "--outdir", str(lo_tmp / "o"), str(src)],
                    args.timeout,
                )
                made = lo_tmp / "o" / f"{src.stem}.pdf"
                if made.exists():
                    shutil.move(str(made), str(dst))
                ok, err = rc == 0, text.strip()[-500:]
            else:
                cmd = d2p.convert_command(tool, src, dst, binary=binary)
                # doxx writes next to its cwd; give each call a scratch cwd.
                with tempfile.TemporaryDirectory(prefix=f"mini-{tool}.") as cwd:
                    rc, text, _ = _capped(cmd, args.timeout, cwd=Path(cwd))
                ok, err = rc == 0, text.strip()[-500:]
            ms = (time.perf_counter() - t0) * 1000
            ok = ok and _is_pdf(dst)
            if not ok:
                dst.unlink(missing_ok=True)
            ok_n += ok
            log.write(json.dumps({"tool": tool, "version": vers[tool], "key": r["key"], "ok": ok, "ms": round(ms, 3),
                                  **({} if ok else {"error": err or "no PDF written"})}) + "\n")
            log.flush()
            if i % 25 == 0 or i == len(rows):
                print(f"{tool}: {i}/{len(rows)} ({ok_n} PDFs)", flush=True)
        if worker is not None:
            worker.close()
        if lo_tmp is not None:
            shutil.rmtree(lo_tmp, ignore_errors=True)


def _itt(report_tool: dict, keys: list[str], field: str | None) -> list[float]:
    """Per-document values over the whole selection; a missing document counts 0."""
    per = report_tool.get("per_doc") or {}
    vals = []
    for k in keys:
        v = per.get(k)
        if isinstance(v, dict):
            v = v.get(field) if field else None
        vals.append(float(v) if isinstance(v, (int, float)) else 0.0)
    return vals


def cmd_score(args: argparse.Namespace) -> None:
    from neurotic_docx_bench import docx_to_pdf as d2p
    from neurotic_docx_bench import docxide_metrics as dm
    from neurotic_docx_bench import hardware
    from neurotic_docx_bench.ledger import converters as conv
    from neurotic_docx_bench.word_pdf_source import select_corpus_word_pdfs, word_pdf_from_config

    out = Path(args.out)
    rows = _selection(out)
    vers = json.loads((out / "versions.json").read_text())
    tools = args.tools.split(",") if args.tools else list(vers)
    root, states = word_pdf_from_config(ROOT / "bench.yaml")
    sel = select_corpus_word_pdfs(
        origin="list", root=root, states=states, files_list=[ROOT / r["pdf"] for r in rows],
        score_only=False, locations=[], tool=None,
    )
    fixtures = sel.fixtures
    if len(fixtures) != len(rows):
        raise SystemExit(f"selection has {len(rows)} documents, the corpus resolved {len(fixtures)}: {sel.warnings[:3]}")
    reports = out / "reports"
    reports.mkdir(exist_ok=True)
    track = f"mini_bench:{out.name}"
    hw = hardware.hardware_info()
    for tool in tools:
        pdf_dir = out / "pdf" / tool
        cands = {f.stem: pdf_dir / f"{f.stem}.pdf" for f in fixtures if (pdf_dir / f"{f.stem}.pdf").is_file()}
        for scorer, runner in (("pixel", d2p.run_eval), ("docxide", dm.run_eval)):
            json_out = reports / f"{tool}__{scorer}.json"
            if json_out.exists() and not args.force:
                print(f"{tool} {scorer}: exists, skipped")
                continue
            with tempfile.TemporaryDirectory(prefix=f"mini-score-{tool}.") as tmp:
                kw = dict(tools=(tool,), work_dir=Path(tmp), fixtures=fixtures, check_pins=False,
                          score_only=True, candidates=cands, warnings=sel.warnings)
                if scorer == "pixel":
                    report = runner(json_out, track=track, jobs=args.jobs, **kw)
                else:
                    report = runner(json_out, fixture_track=track, score_workers=args.jobs, **kw)
            report["tools"][tool]["version"] = vers.get(tool)
            json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
            rel = json_out.resolve()
            rel = rel.relative_to(ROOT) if rel.is_relative_to(ROOT) else rel
            conv.append_report(out / "converters.jsonl", report, hardware=hw, report_path=str(rel))
            print(f"{tool} {scorer}: {len(cands)}/{len(fixtures)} converted", flush=True)
    write_summary(out)


def write_summary(out: Path) -> None:
    rows = _selection(out)
    vers = json.loads((out / "versions.json").read_text())
    meta = json.loads((out / "selection.json").read_text())
    buckets = {"all": [r["key"] for r in rows], "worst": [r["key"] for r in rows if r["bucket"] == "worst"],
               "spread": [r["key"] for r in rows if r["bucket"] == "spread"]}
    table = []
    for tool in vers:
        px_p, dx_p = out / "reports" / f"{tool}__pixel.json", out / "reports" / f"{tool}__docxide.json"
        if not (px_p.exists() and dx_p.exists()):
            continue
        px = json.loads(px_p.read_text())["tools"][tool]
        dx = json.loads(dx_p.read_text())["tools"][tool]
        made = sum(1 for k in buckets["all"] if (out / "pdf" / tool / f"{k}.pdf").is_file())
        line = {"tool": tool, "version": vers[tool], "pdfs": made}
        for b, keys in buckets.items():
            pix = _itt(px, keys, None)
            jac = _itt(dx, keys, "jaccard")
            tb = _itt(dx, keys, "text_boundary")
            line[b] = (statistics.fmean(pix), statistics.median(pix), statistics.fmean(jac), statistics.fmean(tb))
        table.append(line)
    table.sort(key=lambda d: -d["all"][0])
    n = len(rows)
    md = [
        f"# Mini-bench {out.name}",
        "",
        f"{meta['n_worst']} worst + {meta['n_spread']} spread documents of {meta['source_tool']} "
        f"{meta['source_version']} ({meta['source_lens']}, run `{meta['source_run']}`, {meta['source_itt_n']} documents). "
        f"Rule: {meta['rule']}. The list is `selection.csv`.",
        "",
        "Every column is intent-to-treat over the selection: a document a tool did not convert counts 0. "
        "Pixel is the bench scorer (144 DPI); Jaccard and text boundary are the docxide-pdf metrics (150 DPI).",
        "",
        f"| Tool | Version | PDFs /{n} | Pixel mean | Pixel median | Jaccard mean | Text boundary mean | Pixel mean, worst | Pixel mean, spread |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for d in table:
        a, w, s = d["all"], d["worst"], d["spread"]
        md.append(f"| {d['tool']} | {d['version']} | {d['pdfs']} | {a[0]:.2f} | {a[1]:.2f} | {a[2]:.2f} | {a[3]:.2f} | {w[0]:.2f} | {s[0]:.2f} |")
    (out / "SUMMARY.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("select")
    s.add_argument("--run", required=True, help="id_run prefix of a results/converters.jsonl line")
    s.add_argument("--n", type=int, default=200)
    s.add_argument("--max-pages", type=int, help="keep documents whose Word PDF has at most this many pages")
    s.add_argument("--out", required=True)
    c = sub.add_parser("convert")
    c.add_argument("--out", required=True)
    c.add_argument("--tools", help="default: DEFAULT_TOOLS, plus pymupdf-pro when the selection is <= 3 pages")
    c.add_argument("--jubarte", help="jubarte binary (default: docx_to_pdf's resolution)")
    c.add_argument("--timeout", type=float, default=120)
    sc = sub.add_parser("score")
    sc.add_argument("--out", required=True)
    sc.add_argument("--tools", help="default: every tool in versions.json")
    sc.add_argument("--jobs", type=int, default=6)
    sc.add_argument("--force", action="store_true")
    sm = sub.add_parser("summary")
    sm.add_argument("--out", required=True)
    args = ap.parse_args()
    {"select": cmd_select, "convert": cmd_convert, "score": cmd_score, "summary": lambda a: write_summary(Path(a.out))}[args.cmd](args)


if __name__ == "__main__":
    main()

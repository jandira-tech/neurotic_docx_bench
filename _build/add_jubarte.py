"""Add a jubarte column to docxide-pdf's published engine comparison site.

The other engines' page images and scores are taken as published on docxide-pdf's
gh-pages (built by its CI on 2026-09-15 at @261618a9). jubarte is converted and scored
here with docxide's own tools: the same fixtures (input.docx vs Word's reference.pdf),
mutool at 150 DPI, and docxide's `page-metrics` binary. docxide-pdf 0.17.1 is also
re-converted and re-scored locally (not shown on the site) to check that this machine
reproduces the published docxide numbers.

    python3 add_jubarte.py            # convert + score + write site/index.html
    JOBS=8 python3 add_jubarte.py
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCXIDE = HERE / "docxide-pdf"
SITE = HERE / "site"
WORK = HERE / "work"
FIXTURES = DOCXIDE / "tests" / "fixtures"
METRICS_BIN = DOCXIDE / "tools" / "target" / "release" / "page-metrics"
DOCXIDE_BIN = DOCXIDE / "target" / "release" / "docxide-pdf"
JUBARTE_BIN = HERE.parent / "jubarte-redlines" / "target" / "release" / "jubarte"
WORD_FONTS = Path("/Applications/Microsoft Word.app/Contents/Resources/DFonts")
DPI = "150"
JUBARTE_ARGS = ["--revisions", "word", "--compress"]

sys.path.insert(0, str(DOCXIDE / "tools"))
import engine_compare as ec  # noqa: E402


def published() -> tuple[list, list, dict, list]:
    s = (SITE / "index.html").read_text()
    grab = lambda n: json.loads(re.search(r"const " + n + r" = (.*?);\n", s).group(1))  # noqa: E731
    return grab("DATA"), grab("ENGINES"), grab("VERSIONS"), grab("METRICS")


def pngs(pdf: Path, out: Path) -> list[Path]:
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    subprocess.run(["mutool", "draw", "-F", "png", "-r", DPI, "-o", str(out / "page_%03d.png"), str(pdf)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    return sorted(out.glob("page_*.png"))


def metrics(ref_pdf: Path, pdf: Path, ref_dir: Path, dir_: Path) -> dict:
    r = subprocess.run([str(METRICS_BIN), str(ref_pdf), str(pdf), str(ref_dir), str(dir_)],
                       capture_output=True, text=True)
    try:
        m = json.loads(r.stdout)
    except ValueError:
        return {}
    return {k: round(m[k] * 100, 1) for k in ec.METRICS if m.get(k) is not None}


def convert(cmd: list[str], pdf: Path, env: dict | None = None) -> tuple[bool, float, str]:
    pdf.unlink(missing_ok=True)
    t = time.perf_counter()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300, env=env)
    except subprocess.TimeoutExpired:
        return False, time.perf_counter() - t, "timeout 300 s"
    dt = time.perf_counter() - t
    why = " | ".join(((r.stderr or "") + (r.stdout or "")).strip().splitlines()[-3:])[-300:]
    return pdf.is_file() and r.returncode == 0, dt, why


def process(case: dict) -> dict:
    g, c = case["group"], case["case"]
    fx = FIXTURES / g / c
    docx, ref_pdf = fx / "input.docx", fx / "reference.pdf"
    work = WORK / g / c
    work.mkdir(parents=True, exist_ok=True)
    ref_dir = work / "reference"
    pngs(ref_pdf, ref_dir)
    out: dict = {"group": g, "case": c}

    jpdf = work / "jubarte.pdf"
    ok, dt, why = convert([str(JUBARTE_BIN), "convert", str(docx), "-o", str(jpdf), "--force", *JUBARTE_ARGS], jpdf)
    out["jubarte_time"] = dt
    if ok:
        jdir = work / "jubarte"
        pages = pngs(jpdf, jdir)
        out["jubarte_scores"] = metrics(ref_pdf, jpdf, ref_dir, jdir)
        dest = SITE / g / c / "jubarte"
        shutil.rmtree(dest, ignore_errors=True)
        dest.mkdir(parents=True)
        for p in pages:
            subprocess.run(["cwebp", "-quiet", "-lossless", str(p), "-o", str(dest / (p.stem + ".webp"))],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        out["jubarte_pages"] = [f"{g}/{c}/jubarte/{p.stem}.webp" for p in pages]
        shutil.rmtree(jdir)
    else:
        out["jubarte_error"] = why

    dpdf = work / "docxide.pdf"
    env = {**os.environ, "DOCXSIDE_FONTS": str(WORD_FONTS)}
    ok, dt, why = convert([str(DOCXIDE_BIN), str(docx), str(dpdf)], dpdf, env)
    out["docxide_time"] = dt
    if ok:
        ddir = work / "docxide"
        pngs(dpdf, ddir)
        out["docxide_scores"] = metrics(ref_pdf, dpdf, ref_dir, ddir)
        shutil.rmtree(ddir)
    else:
        out["docxide_error"] = why
    shutil.rmtree(ref_dir)
    return out


def main() -> None:
    for b in (METRICS_BIN, DOCXIDE_BIN, JUBARTE_BIN):
        if not b.is_file():
            sys.exit(f"missing {b}")
    data, engines, versions, _ = published()
    jver = subprocess.run([str(JUBARTE_BIN), "--version"], capture_output=True, text=True).stdout.split()[-1]
    jobs = int(os.environ.get("JOBS", "8"))
    if os.environ.get("HTML_ONLY"):
        results = json.loads((HERE / "local_scores.json").read_text())["cases"]
    else:
        results = []
        with ThreadPoolExecutor(max_workers=jobs) as pool:
            for i, r in enumerate(pool.map(process, data), 1):
                results.append(r)
                print(f"[{i}/{len(data)}] {r['group']}/{r['case']} jubarte={r.get('jubarte_scores') or r.get('jubarte_error')} "
                      f"docxide_local={r.get('docxide_scores') or r.get('docxide_error')}", flush=True)
        (HERE / "local_scores.json").write_text(json.dumps(
            {"jubarte_version": jver, "jubarte_args": JUBARTE_ARGS, "mutool": subprocess.run(
                ["mutool", "-v"], capture_output=True, text=True).stderr.strip(), "cases": results}, indent=1))

    by = {(r["group"], r["case"]): r for r in results}
    for case in data:
        r = by[(case["group"], case["case"])]
        if r.get("jubarte_pages"):
            case["pages"]["jubarte"] = r["jubarte_pages"]
        if r.get("jubarte_scores"):
            case["scores"]["jubarte"] = r["jubarte_scores"]
    engines = [e for e in engines if e[0] != "jubarte"] + [["jubarte", "jubarte"]]
    versions["jubarte"] = f"{jver} (--revisions word --compress)"
    ec.ENGINES = engines
    note = ("<span><b>jubarte</b> column added 2026-09-28: converted on macOS with the Word fonts installed "
            "there, scored with this site own page-metrics (docxide @261618a9) and mutool at 150 DPI. "
            "Its time is not shown: it was not measured on the CI runner that timed the other engines. "
            "The other columns are the docxide-pdf CI build of 2026-09-15, rendered with its own font pack.</span>")
    ec.HTML_TEMPLATE = ec.HTML_TEMPLATE.replace(
        "extra pages are ignored.</span>' +", "extra pages are ignored.</span>" + note + "' +", 1)
    assert note in ec.HTML_TEMPLATE and "'" not in note
    ec.write_html(data, versions, SITE / "index.html")
    print("site written:", SITE / "index.html")


if __name__ == "__main__":
    main()

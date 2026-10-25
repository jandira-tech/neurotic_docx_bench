"""PyMuPDF Pro 1.28.2 (unlicensed: first 3 pages only) on docxide-pdf's fixtures.

Converted and scored only where Word's reference.pdf has <= 3 pages, the same rule the
bench applies (its below-3-pages set); a longer document would be cut at page 3 and
page-metrics, which averages over the pages both PDFs have, would not see the loss.

    python3 add_pymupdf.py      # -> local_pymupdf.json, work/<group>/<case>/pymupdf.pdf
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import add_jubarte as aj

WRAPPER = aj.HERE.parent / "neurotic_docx_bench" / "src" / "neurotic_docx_bench" / "utils" / "pymupdf-pro" / "pymupdf-pro-convert"


def ref_pages(pdf: Path) -> int:
    out = subprocess.run(["mutool", "info", str(pdf)], capture_output=True, text=True).stdout
    for line in out.splitlines():
        if line.startswith("Pages:"):
            return int(line.split()[1])
    return 0


def process(case: dict) -> dict:
    g, c = case["group"], case["case"]
    fx = aj.FIXTURES / g / c
    ref = fx / "reference.pdf"
    out = {"group": g, "case": c, "ref_pages": ref_pages(ref)}
    if out["ref_pages"] > 3:
        return out
    work = aj.WORK / g / c
    work.mkdir(parents=True, exist_ok=True)
    pdf = work / "pymupdf.pdf"
    ok, dt, why = aj.convert([str(WRAPPER), str(fx / "input.docx"), str(pdf)], pdf)
    out["time"] = dt
    if not ok:
        out["error"] = why
        return out
    ref_dir, dir_ = work / "reference_p", work / "pymupdf"
    aj.pngs(ref, ref_dir)
    out["pages"] = len(aj.pngs(pdf, dir_))
    out["scores"] = aj.metrics(ref, pdf, ref_dir, dir_)
    shutil.rmtree(ref_dir)
    shutil.rmtree(dir_)
    return out


def main() -> None:
    if os.environ.get("PYMUPDFPRO_LICENSE_KEY"):
        raise SystemExit("PYMUPDFPRO_LICENSE_KEY is set; this is the unlicensed measurement")
    data, *_ = aj.published()
    t = time.time()
    with ThreadPoolExecutor(max_workers=int(os.environ.get("JOBS", "8"))) as pool:
        rows = list(pool.map(process, data))
    # SmartOffice's err=795 shows up only under parallel load; a failure gets one serial retry.
    for i, r in enumerate(rows):
        if "error" in r:
            again = process(next(c for c in data if (c["group"], c["case"]) == (r["group"], r["case"])))
            again["retried_after"] = r["error"]
            rows[i] = again
    ver = subprocess.run([str(WRAPPER), "--version"], capture_output=True, text=True).stdout.strip()
    (aj.HERE / "local_pymupdf.json").write_text(json.dumps({"version": ver, "cases": rows}, indent=1))
    n = [r for r in rows if r["ref_pages"] <= 3]
    print(f"{len(n)} cases <= 3 pages, {sum('scores' in r for r in n)} scored, "
          f"{sum('error' in r for r in n)} failed, {time.time() - t:.0f} s")
    for r in n:
        if "error" in r:
            print("  FAIL", r["group"], r["case"], r["error"][:160])


if __name__ == "__main__":
    main()

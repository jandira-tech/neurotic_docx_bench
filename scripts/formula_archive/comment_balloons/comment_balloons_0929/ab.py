# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""A/B harness: variants of a docx's document.xml, rendered by scripts/word_pdf.py (one batch),
counted for Word comment balloons ("Commented [") per page."""
from __future__ import annotations
import re, subprocess, sys, zipfile, json
from pathlib import Path
import fitz

BENCH = Path.home() / "temp/T/neurotic_docx_bench"

def read(docx: Path, part="word/document.xml") -> str:
    return zipfile.ZipFile(docx).read(part).decode("utf8")

def write(src: Path, out: Path, parts: dict[str, str | bytes]) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(src) as zi, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zo:
        for it in zi.infolist():
            v = parts.get(it.filename)
            zo.writestr(it, (v.encode() if isinstance(v, str) else v) if v is not None else zi.read(it.filename))
    return out

def render(folder: Path) -> None:
    with open(folder / "render.log", "w") as log:  # the driver's own log, readable while it runs
        subprocess.run(["uv", "run", "python", "scripts/word_pdf.py", "--src", str(folder / "docx"), "--out", str(folder / "pdf"),
                        "--no-check-preset"], cwd=BENCH, check=True, stdout=log, stderr=subprocess.STDOUT)

def count(pdf: Path) -> dict:
    d = fitz.open(pdf)
    per = [len(re.findall(r"Commented \[", pg.get_text())) for pg in d]
    return {"pages": len(d), "balloons": sum(per), "per_page": per, "width": round(d[0].rect.width), "orient": ["L" if pg.rect.width > pg.rect.height else "P" for pg in d]}

def report(folder: Path) -> dict:
    out = {}
    for docx in sorted((folder / "docx").glob("*.docx")):
        pdf = folder / "pdf" / f"{docx.stem}.pdf"
        out[docx.stem] = count(pdf) if pdf.is_file() else None
        r = out[docx.stem]
        print(f"{docx.stem:55s} " + (f"pages={r['pages']:3d} balloons={r['balloons']:3d} per_page={r['per_page']} {''.join(r['orient'])}" if r else "NO PDF"))
    (folder / "result.json").write_text(json.dumps(out, indent=1))
    return out

if __name__ == "__main__":
    f = Path(sys.argv[1]); render(f); report(f)

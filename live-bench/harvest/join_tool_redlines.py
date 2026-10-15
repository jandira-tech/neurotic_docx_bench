"""Join the D1 render failures of tool redlines with the local-Word batch (and any reruns).

usage: join_tool_redlines.py <tool_redline_failures.csv> <tool_redlines_dir>
Reruns: <dir>/word_rerun<N>.stdout with PDFs in <dir>/word_pdf_rerun<N>; a later run overrides.
writes <dir>/manifest.csv and copies Word-broken files to <dir>/word_broken/
"""

import csv
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

src, d = Path(sys.argv[1]), Path(sys.argv[2])
STEM = r"(?:docxodus|jubarte|superdoc-redlines)__[0-9a-f]{8}_\d{4}"


def parse(stdout: Path) -> dict[str, str]:
    text = stdout.read_text(errors="replace")
    text = text[text.rfind("│ failed"):]  # the summary table, then its FAIL list
    return {m.group(1): re.sub(r"\s+", " ", m.group(2)).strip()
            for m in re.finditer(rf"FAIL ({STEM})\.docx:[ \t]*(.*?)(?=\n\s*FAIL |\Z)", text, re.S)}


def stems(folder: Path) -> set[str]:
    return {p.stem for p in folder.glob("*.pdf")}


fails, pdfs = parse(d / "word_run.stdout"), stems(d / "word_pdf")
for out in sorted(d.glob("word_rerun*.stdout"), key=lambda p: int(re.sub(r"\D", "", p.stem) or 0)):
    rf, rp = parse(out), stems(d / out.stem.replace("word_rerun", "word_pdf_rerun"))
    for s in rp:
        fails.pop(s, None)
    fails.update(rf)
    pdfs |= rp

gate = {r["file"].removesuffix(".docx"): r for r in csv.DictReader(open(d / "purexml_gate.csv"))}
broken = d / "word_broken"
broken.mkdir(exist_ok=True)
rows = []
for r in csv.DictReader(open(src)):
    s = f"{r['tool']}__{r['run']}_{int(r['sequence']):04d}"
    g = gate.get(s, {})
    if g.get("opened") != "True":
        local = "deleted_unsafe"
    elif s in fails:
        local = "broken"
    elif s in pdfs:
        local = "opens_ok"
    else:
        local = "no_result"
    if local == "broken":
        shutil.copy2(d / "all" / f"{s}.docx", broken / f"{s}.docx")
    rows.append({"file": f"{s}.docx", **r, "guard_now": g.get("guard_now", ""),
                 "local_word": local, "local_word_error": fails.get(s, "")})

with open(d / "manifest.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader(); w.writerows(rows)


def where(r):
    if r["word_render"]:
        return f"word:{r['word_code']}"
    e = r["soffice_error"]
    return "soffice:" + ("env_no_libs" if "platform independent" in e else
                         "app_error" if "Unspecified Application" in e else
                         "timeout" if "timed out" in e else "pdf_probe" if "Traceback" in e else e[:30])


print("local Word:", dict(Counter(r["local_word"] for r in rows)))
for k, v in sorted(Counter((r["tool"], where(r), r["local_word"]) for r in rows).items()):
    print(f"  {v:4} {k[0]:18} {k[1]:24} {k[2]}")
print("broken errors:", dict(Counter(re.sub(r"\s+", " ", r["local_word_error"])[:80]
                                     for r in rows if r["local_word"] == "broken")))

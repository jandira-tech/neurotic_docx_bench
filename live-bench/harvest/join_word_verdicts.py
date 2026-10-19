"""Join D1 verdicts, the unsafe gate and the local-Word batch into one manifest.

usage: join_word_verdicts.py <analysis_dir> <problematic_dir>
writes <problematic_dir>/manifest.csv and copies Word-broken files to <problematic_dir>/word_broken/
"""

import csv
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

an, pdir = Path(sys.argv[1]), Path(sys.argv[2])

d1 = {r["sha256"]: r for r in csv.DictReader(open(an / "word_rejected_fixtures.csv"))}
for r in csv.DictReader(open(an / "never_sent_fetch.csv")):
    d1.setdefault(r["sha256"], {"sha256": r["sha256"], "url": r["url"], "family": "bench_preflight",
                                "code": r["code"].removeprefix("bench_preflight: "), "type": "",
                                "language": "", "corpus_filename": "", "request_id": ""})
guard = {}
for name in ("guard_reasons.csv", "guard_reasons_never_sent.csv"):
    for r in csv.DictReader(open(an / name)):
        guard[r["sha256"]] = r
gate = {r["file"].removesuffix(".docx"): r for r in csv.DictReader(open(pdir / "purexml_gate.csv"))}

def parse(stdout: Path) -> dict[str, str]:
    text = stdout.read_text(errors="replace")
    # rich wraps long lines; join continuation lines before matching
    text = text[text.rfind("│ failed"):]  # the summary table, then its FAIL list
    return {m.group(1): re.sub(r"\s+", " ", m.group(2)).strip()
            for m in re.finditer(r"FAIL ([0-9a-f]{64})\.docx:[ \t]*(.*?)(?=\n\s*FAIL |\Z)", text, re.S)}


def stems(folder: Path) -> set[str]:
    return {re.search(r"[0-9a-f]{64}", p.stem).group(0) for p in folder.glob("*.pdf")
            if re.search(r"[0-9a-f]{64}", p.stem)}


# a later pass (fresh Word) overrides the first: a cascade of "close" errors is not a verdict
fails, pdfs = parse(pdir / "word_run.stdout"), stems(pdir / "word_pdf")
for out, pdf_dir in (("word_rerun.stdout", "word_pdf_rerun"), ("word_rerun2.stdout", "word_pdf_rerun2"),
                     ("word_rerun3.stdout", "word_pdf_rerun3")):
    if not (pdir / out).exists():
        continue
    rerun_fails, rerun_pdfs = parse(pdir / out), stems(pdir / pdf_dir)
    for sha in rerun_pdfs:
        fails.pop(sha, None)
    fails.update(rerun_fails)
    pdfs |= rerun_pdfs

broken_dir = pdir / "word_broken"
broken_dir.mkdir(exist_ok=True)
rows = []
for sha in sorted(gate):
    g, d, q = gate[sha], d1.get(sha, {}), guard.get(sha, {})
    if g["opened"] != "True":
        local = "not_opened_unsafe"
    elif sha in fails:
        local = "broken"
    elif sha in pdfs:
        local = "opens_ok"
    else:
        local = "no_result"
    if local == "broken":
        shutil.copy2(pdir / "all" / f"{sha}.docx", broken_dir / f"{sha}.docx")
    rows.append({
        "sha256": sha, "url": d.get("url", ""), "type": d.get("type", ""),
        "language": d.get("language", ""), "corpus_filename": d.get("corpus_filename", ""),
        "d1_family": d.get("family", ""), "d1_code": d.get("code", ""),
        "d1_request_id": d.get("request_id", ""),
        "guard_now": q.get("local_code", ""), "guard_now_reason": q.get("reason", ""),
        "guard_now_part": q.get("part", ""),
        "purexml": g["purexml"], "local_word": local, "local_word_error": fails.get(sha, ""),
    })

with open(pdir / "manifest.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader(); w.writerows(rows)

print("local Word verdict:", dict(Counter(r["local_word"] for r in rows)))
print("\nD1 code x local Word:")
for k, v in sorted(Counter((r["d1_code"], r["local_word"]) for r in rows).items(), key=lambda x: -x[1]):
    print(f"  {v:5} {k[0]:40} {k[1]}")
print("\nbroken, by Word error:")
for k, v in Counter(re.sub(r"[0-9a-f]{64}", "<sha>", r["local_word_error"])[:90]
                    for r in rows if r["local_word"] == "broken").most_common():
    print(f"  {v:5} {k}")

# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
"""Page-count guard for the English corpus.

en_pages.py BIN TAG [--baseline]

Converts every document that has a Word PDF (sets a, b, r) with BIN into
grok_run/en_jubarte_pdf_{a,b,r}/, overwriting the previous PDF and deleting
files Word does not have, so the Word and jubarte folders hold the same names.
Counts pages per document for Word and jubarte and writes runs/en_pages_TAG.json.

With --baseline (or when runs/en_pages_baseline.json is missing) the result
becomes the baseline. Otherwise every document whose jubarte page count moved
against the baseline is flagged: CLOSER / FARTHER / SAME-GAP relative to Word.
"""

import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

G = "/Users/arthrod/temp/T/neurotic_docx_bench/grok_run"
L = "/Users/arthrod/temp/T/jubarte-loop"
SETS = {
    "a": ("500_docx_part_a_original", "500_pdf_part_a_original"),
    "b": ("500_docx_part_b_original", "500_pdf_part_b_original"),
    "r": ("500_extra_docx_redlines", "500_extra_pdf_redlines"),
}
BASE = f"{L}/runs/en_pages_baseline.json"


def pages(pdf):
    try:
        out = subprocess.run(["pdfinfo", pdf], capture_output=True, text=True, timeout=60).stdout
    except subprocess.TimeoutExpired:
        return 0
    for line in out.splitlines():
        if line.startswith("Pages:"):
            return int(line.split()[1])
    return 0


def convert(bin_, src, dst):
    try:
        subprocess.run(
            [bin_, "convert", src, "-o", dst, "--force", "--revisions", "word"],
            capture_output=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        pass
    return pages(dst) if os.path.exists(dst) else 0


def main():
    bin_, tag = sys.argv[1], sys.argv[2]
    make_base = "--baseline" in sys.argv[3:] or not os.path.exists(BASE)
    t0 = time.time()
    result = {"bin": bin_, "tag": tag, "sets": {}}
    with ThreadPoolExecutor(max_workers=10) as pool:
        for s, (src_dir, word_dir) in SETS.items():
            out_dir = f"{G}/en_jubarte_pdf_{s}"
            os.makedirs(out_dir, exist_ok=True)
            stems = sorted(f[:-4] for f in os.listdir(f"{G}/{word_dir}") if f.endswith(".pdf"))
            keep = {f"{st}.pdf" for st in stems}
            for f in os.listdir(out_dir):
                if f not in keep:
                    os.remove(f"{out_dir}/{f}")
            for st in stems:
                # a stale PDF must not survive a failed conversion
                if os.path.exists(f"{out_dir}/{st}.pdf"):
                    os.remove(f"{out_dir}/{st}.pdf")
            jobs = {
                st: pool.submit(convert, bin_, f"{G}/{src_dir}/{st}.docx", f"{out_dir}/{st}.pdf")
                for st in stems
            }
            words = dict(zip(stems, pool.map(lambda st: pages(f"{G}/{word_dir}/{st}.pdf"), stems)))
            result["sets"][s] = {st: [words[st], jobs[st].result()] for st in stems}
    with open(f"{L}/runs/en_pages_{tag}.json", "w") as f:
        json.dump(result, f)

    base = None if make_base else json.load(open(BASE))
    print(f"page guard {tag} ({time.time() - t0:.0f}s) bin={os.path.basename(bin_)}")
    moved_total = farther_total = 0
    for s, rows in result["sets"].items():
        wt = sum(w for w, _ in rows.values())
        jt = sum(j for _, j in rows.values())
        exact = sum(1 for w, j in rows.values() if w == j)
        gap = sum(abs(w - j) for w, j in rows.values())
        failed = [st[:12] for st, (_, j) in rows.items() if j == 0]
        line = f"{s} n={len(rows)} word={wt} jubarte={jt} exact={exact} |gap|={gap}"
        if base:
            brows = base["sets"][s]
            bexact = sum(1 for st in rows if st in brows and brows[st][0] == brows[st][1])
            bgap = sum(abs(brows[st][0] - brows[st][1]) for st in rows if st in brows)
            line += f" (baseline exact={bexact} |gap|={bgap})"
        if failed:
            line += f" FAILED={len(failed)} {' '.join(failed[:10])}"
        print(line)
        if not base:
            continue
        for st, (w, j) in rows.items():
            if st not in brows:
                continue
            b = brows[st][1]
            if j == b:
                continue
            moved_total += 1
            d0, d1 = abs(w - b), abs(w - j)
            verdict = "CLOSER" if d1 < d0 else "FARTHER" if d1 > d0 else "SAME-GAP"
            farther_total += verdict != "CLOSER"
            print(f"  {s} {st[:12]} word={w} baseline={b} now={j} {verdict}")
    if make_base:
        with open(BASE, "w") as f:
            json.dump(result, f)
        print(f"baseline saved: {BASE}")
    else:
        print(f"PAGE-GUARD moved={moved_total} not-closer={farther_total} (baseline {base['tag']})")


if __name__ == "__main__":
    main()

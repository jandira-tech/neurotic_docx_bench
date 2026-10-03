# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Simulate 'recursive longest-run alignment with a per-window cost rule' and
score it against Word's verdicts (and matched pairs where known)."""
import csv
import difflib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, "/Users/arthrod/T/neurotic_docx_bench/scripts")
sys.path.insert(0, "/tmp")
from redline_anatomy import paragraphs, words  # noqa: E402

BASE = Path("/Users/arthrod/temp/T/jubarte-redlines/jubarte-app/_scratch/redline-traversal-flow")


def build_dataset(out=BASE / "probes/dataset.json"):
    rows = []
    for wave in ("wave1", "wave2all", "wave3", "wave4"):
        f = BASE / "probes" / wave / "features.csv"
        if not f.exists():
            continue
        for r in csv.DictReader(open(f)):
            name = r["redline"].split("__")[0]
            A = paragraphs(BASE / "probes" / wave / "A" / f"{name}.docx")[int(r["a_index"])].text("rev")
            B = paragraphs(BASE / "probes" / wave / "B" / f"{name}.docx")[int(r["b_index"])].text("rev")
            rows.append({"set": wave, "name": name, "a": A, "b": B, "verdict": r["verdict"]})
    c55 = [p.text("rev") for p in paragraphs(BASE / "inputs/55_Traversal_cover_letter.docx")]
    c56 = [p.text("rev") for p in paragraphs(BASE / "inputs/56_Flow_cover_letter.docx")]
    m55 = [p.text("rev") for p in paragraphs(BASE / "inputs/55_Traversal_metadata.docx")]
    m56 = [p.text("rev") for p in paragraphs(BASE / "inputs/56_Flow_metadata.docx")]
    for name, A, B, v in (("letters p5", c55[5], c56[5], "word-level"), ("meta p14", m55[14], m56[14], "word-level"), ("meta p12", m55[12], m56[12], "word-level"),
                          ("meta p3", m55[3], m56[3], "replaced"), ("meta p6", m55[6], m56[6], "replaced"), ("meta p9", m55[9], m56[9], "replaced")):
        rows.append({"set": "real", "name": name, "a": A, "b": B, "verdict": v})
    out.write_text(json.dumps(rows))
    return rows


def runs_of(pairs):
    s = set(pairs)
    return sum(1 for i, j in s if (i - 1, j - 1) not in s)


def align(a, b, c, beta, min_run=1, lo1=0, lo2=0):
    """Greedy longest-common-run recursion; a window whose cost exceeds beta·L is replaced whole."""
    if not a or not b:
        return set()
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    m = sm.find_longest_match(0, len(a), 0, len(b))
    if m.size < min_run:
        return set()
    left = align(a[: m.a], b[: m.b], c, beta, min_run, lo1, lo2)
    right = align(a[m.a + m.size:], b[m.b + m.size:], c, beta, min_run, lo1 + m.a + m.size, lo2 + m.b + m.size)
    pairs = left | right | {(lo1 + m.a + k, lo2 + m.b + k) for k in range(m.size)}
    cost = (len(a) + len(b) - 2 * len(pairs)) + c * runs_of(pairs)
    if cost > beta * max(len(a), len(b)):
        return set()
    return pairs


def verdict_of(a, b, c, beta, min_run=1):
    return "word-level" if align(a, b, c, beta, min_run) else "replaced"


if __name__ == "__main__":
    ds_path = BASE / "probes/dataset.json"
    rows = json.loads(ds_path.read_text()) if ds_path.exists() and "--rebuild" not in sys.argv else build_dataset()
    sets = [s for s in sys.argv[1:] if not s.startswith("--")] or ["wave1", "wave2all", "wave3", "real"]
    rows = [r for r in rows if r["set"] in sets]
    toks = [([w.lower() for w in words(r["a"])], [w.lower() for w in words(r["b"])]) for r in rows]
    print(f"{len(rows)} pairs from {sets}")
    cs = [0, 0.5, 1, 1.5, 2, 3]
    betas = [1.5, 1.55, 1.6, 1.65, 1.7, 1.75, 1.8, 1.85]
    best = []
    for min_run in (1, 2):
        for c in cs:
            for beta in betas:
                ok = 0
                wrong = []
                for r, (a, b) in zip(rows, toks):
                    v = verdict_of(a, b, c, beta, min_run)
                    if v == r["verdict"]:
                        ok += 1
                    else:
                        wrong.append(r["name"])
                best.append((ok / len(rows), min_run, c, beta, wrong))
    best.sort(key=lambda t: -t[0])
    for acc, min_run, c, beta, wrong in best[:10]:
        print(f"  acc={acc:.3f} min_run={min_run} c={c} beta={beta}  wrong={wrong[:8]}")

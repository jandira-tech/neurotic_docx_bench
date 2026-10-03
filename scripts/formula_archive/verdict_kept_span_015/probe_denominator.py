#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Which denominator fits the symmetric probes? kept / min, max, mean over the Word redlines of the probe waves."""
import csv, glob, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
sys.path.insert(0, "/Users/arthrod/T/neurotic_docx_bench/scripts")
import redline_anatomy as ra
sys.path.insert(0, "/tmp")
from real_rule_check2 import one

R = "/Users/arthrod/T/jubarte-redlines/jubarte-app/_scratch/redline-traversal-flow/probes"
SETS = ["wave1", "wave3", "wave4", "wave5", "wave7", "wave7b", "wave8", "variants", "variants2", "tokens", "real"]

def main():
    files = [f for s in SETS for f in sorted(glob.glob(f"{R}/{s}/word/*.docx"))]
    rows = []
    with ProcessPoolExecutor(6) as ex:
        for f, rs in zip(files, ex.map(one, files, chunksize=4)):
            for r in rs:
                if "error" in r: continue
                r["set"] = Path(f).parent.parent.name
                rows.append(r)
    with open("/tmp/probe_rows.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"{len(files)} redlines, {len(rows)} judged paragraphs")
    dens = {"max": lambda r: max(r["chars_a"], r["chars_b"], 1), "min": lambda r: max(min(r["chars_a"], r["chars_b"]), 1),
            "mean": lambda r: max((r["chars_a"] + r["chars_b"]) / 2, 1)}
    def agree(rs, key, t): return sum((key(r) >= t) == (r["word"] == "word-level") for r in rs) / len(rs)
    def sweep(rs, key): return max((agree(rs, key, k / 1000), k / 1000) for k in range(50, 300, 2))
    asym = [abs(r["chars_a"] - r["chars_b"]) / max(r["chars_a"], r["chars_b"]) for r in rows]
    print(f"length asymmetry |a-b|/max: mean {sum(asym)/len(asym):.3f}, max {max(asym):.3f}")
    print(f"{'den':>5} {'@0.12':>6} {'@0.125':>6} {'@0.13':>6} {'best':>6} {'thr':>6}")
    for d, den in dens.items():
        key = lambda r, den=den: r["kept_all"] / den(r)
        b = sweep(rows, key)
        print(f"{d:>5} {agree(rows, key, 0.12):>6.3f} {agree(rows, key, 0.125):>6.3f} {agree(rows, key, 0.13):>6.3f} {b[0]:>6.3f} {b[1]:>6.3f}")
    # the clean sets only
    clean = [r for r in rows if r["set"] in ("wave7", "wave7b", "wave8", "variants2", "tokens")]
    print(f"clean sets ({len(clean)}):")
    for d, den in dens.items():
        key = lambda r, den=den: r["kept_all"] / den(r)
        b = sweep(clean, key)
        print(f"{d:>5} {agree(clean, key, 0.12):>6.3f} {agree(clean, key, 0.125):>6.3f} {agree(clean, key, 0.13):>6.3f} {b[0]:>6.3f} {b[1]:>6.3f}")
    # corpus isolated pairs + probes, min denominator, joint best
    corpus = [{k: (int(v) if k not in ("file", "word") else v) for k, v in r.items()} for r in csv.DictReader(open("/tmp/real_rule_rows2.csv"))]
    iso = [r for r in corpus if (r["region"] == 1 and r["word"] == "word-level") or (r["region"] == 2 and r["word"] == "replaced")]
    joint = rows + iso
    print(f"probes + corpus isolated pairs ({len(joint)}):")
    for d, den in dens.items():
        key = lambda r, den=den: r["kept_all"] / den(r)
        b = sweep(joint, key)
        print(f"{d:>5} {agree(joint, key, 0.12):>6.3f} {agree(joint, key, 0.125):>6.3f} {agree(joint, key, 0.13):>6.3f} {b[0]:>6.3f} {b[1]:>6.3f}")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Token probes: what Word deleted and inserted for each controlled edit."""
import csv, sys
from pathlib import Path
sys.path.insert(0, "/Users/arthrod/T/neurotic_docx_bench/scripts")
import redline_anatomy as ra
P = Path(sys.argv[1])
print(f"{'probe':22} {'A':32} {'B':32}  Word: del / ins")
for m in csv.DictReader((P / "manifest.csv").open()):
    n = m["name"]; r = P / "word" / f"{n}__vs__{n}.docx"
    if not r.exists():
        print(f"{n:22} (no redline)"); continue
    segs = [(s.kind, s.text) for p in ra.paragraphs(r) for s in p.segments if s.kind != "eq"]
    dels = " | ".join(repr(t) for k, t in segs if k == "del"); ins = " | ".join(repr(t) for k, t in segs if k == "ins")
    print(f"{n:22} {m['a']:32} {m['b']:32}  {dels or '∅'}  /  {ins or '∅'}")

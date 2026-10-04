#!/usr/bin/env python3
"""Word's verdict on each probe of a wave against its meta.csv.

    wave_verdicts.py WAVE_DIR [--engine BIN_OUT_DIR]

Prints one row per pair (name, meta columns, Word's verdict on the judged
paragraph — the third paragraph: two labels, the paragraph, a tail), then
for `short1`: per length, the highest replaced ratio and the lowest
word-level ratio; for `asym1`: agreement of kept/min and kept/max at 0.12
and the best threshold for each.
"""
import csv, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import redline_anatomy as ra


def judged(path):
    paras = ra.paragraphs(Path(path))
    vs = ra.verdicts(paras)
    # the probe paragraph is the one after the two labels; a replaced one is two paragraphs
    body = [v for v in vs if v.verdict != "unchanged"]
    kinds = {v.verdict for v in body}
    if not body:
        return "unchanged", ""
    if kinds <= {"word-level", "mark-only"}:
        p = paras[[v for v in body if v.verdict == "word-level"][0].index]
        eq = "|".join(s.text for s in p.segments if s.kind == "eq" and s.text.strip())
        return "word-level", eq[:60]
    if "replaced" in kinds:
        return "replaced", ""
    return "+".join(sorted(kinds)), ""


def main():
    wave = Path(sys.argv[1])
    rows = list(csv.DictReader((wave / "meta.csv").open()))
    out = []
    for r in rows:
        fs = sorted((wave / "word").glob(f"{r['name']}__vs__*.docx")) or [wave / "word" / f"{r['name']}.docx"]
        f = fs[0]
        if not f.exists():
            r["word"] = "missing"; r["kept"] = ""
        else:
            try:
                r["word"], r["kept"] = judged(f)
            except Exception as e:  # noqa: BLE001
                r["word"], r["kept"] = "error", str(e)[:40]
        out.append(r)
    with (wave / "verdicts.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader(); w.writerows(out)
    have = [r for r in out if r["word"] in ("word-level", "replaced")]
    print(f"{len(out)} pairs, {len(have)} judged, {sum(r['word'] == 'missing' for r in out)} missing, "
          f"{sum(r['word'] not in ('word-level', 'replaced', 'missing') for r in out)} other")
    if "ratio_min" in out[0]:
        for den in ("ratio_min", "ratio_max"):
            key = lambda r, den=den: float(r[den])
            agree = lambda t: sum((key(r) >= t) == (r["word"] == "word-level") for r in have) / len(have)
            best = max((agree(k / 1000), k / 1000) for k in range(0, 500, 5))
            print(f"  {den}: @0.12 {agree(0.12):.3f}  best {best[0]:.3f} @ {best[1]}")
        print(f"  {'name':>22} {'min':>6} {'max':>6}  verdict  kept")
        for r in sorted(have, key=lambda r: (r["direction"], int(r["n"]), int(r["asym"]), float(r["ratio_min"]))):
            print(f"  {r['name']:>22} {float(r['ratio_min']):>6.3f} {float(r['ratio_max']):>6.3f}  {r['word']:10} {r['kept'][:40]}")
    else:
        by = {}
        for r in have:
            by.setdefault((r["group"], int(r["n"])), []).append(r)
        print(f"  {'group':>5} {'n':>4} {'pairs':>5}  replaced max | word-level min")
        for (g, n), rs in sorted(by.items()):
            rep = sorted(float(r["ratio"]) for r in rs if r["word"] == "replaced")
            wl = sorted(float(r["ratio"]) for r in rs if r["word"] == "word-level")
            print(f"  {g:>5} {n:>4} {len(rs):>5}  {rep[-3:]} | {wl[:3]}")
        key = lambda r: float(r["ratio"])
        agree = lambda t, rs: sum((key(r) >= t) == (r["word"] == "word-level") for r in rs) / len(rs)
        best = max((agree(k / 1000, have), k / 1000) for k in range(0, 400, 5))
        print(f"  all: @0.12 {agree(0.12, have):.3f}  best {best[0]:.3f} @ {best[1]}")
        for lo, hi in [(6, 12), (16, 30), (40, 80), (120, 160)]:
            rs = [r for r in have if lo <= int(r["n"]) <= hi]
            if rs:
                b = max((agree(k / 1000, rs), k / 1000) for k in range(0, 400, 5))
                print(f"  n {lo}-{hi}: {len(rs)} pairs @0.12 {agree(0.12, rs):.3f}  best {b[0]:.3f} @ {b[1]}")


if __name__ == "__main__":
    main()

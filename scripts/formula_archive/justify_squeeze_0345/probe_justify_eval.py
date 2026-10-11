# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Read Word's PDFs of the probe_justify.py probes: did the first line keep
its last word (Word narrowed the spaces) or wrap it?

Usage: uv run python scripts/probe_justify_eval.py DOCXDIR PDFDIR [--json OUT]
Prints one row per probe and, per face and space count, the largest
overflow Word kept and the smallest it wrapped, as a share of the line's
space width and of the last word's width.
"""
import json, os, sys, collections
import fitz

def first_line_words(pdf):
    doc = fitz.open(pdf)
    lines = []
    for b in doc[0].get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            t = "".join(s["text"] for s in l["spans"]).strip()
            if t:
                lines.append((round(l["bbox"][1], 1), t))
    lines.sort()
    return lines[0][1].split() if lines else [], len(lines)

def main():
    docx_dir, pdf_dir = sys.argv[1], sys.argv[2]
    out = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
    manifest = json.load(open(os.path.join(docx_dir, "manifest.json")))
    rows = []
    for m in manifest:
        pdf = os.path.join(pdf_dir, m["id"] + ".pdf")
        if not os.path.exists(pdf):
            continue
        words, nlines = first_line_words(pdf)
        line1 = m["text"].split()[: m["nspaces"] + 1]
        kept = len(words) >= len(line1) and words[: len(line1)] == line1
        # a kept line holds exactly line1 (the tail words start line 2)
        exact = words == line1
        space_total = m["nspaces"] * m["space"]
        rows.append(dict(
            id=m["id"], face=m["face"], nspaces=m["nspaces"], last=m["last"], last_w=m["last_w"],
            space=m["space"], over=m["over"], kept=kept, exact=exact, nlines=nlines,
            share_of_spaces=round(m["over"] / space_total, 4) if space_total else None,
            share_of_word=round(m["over"] / m["last_w"], 4),
            per_space=round(m["over"] / m["nspaces"], 3),
        ))
    for r in rows:
        print(f"{r['id']:28} over={r['over']:6.2f} spaces={r['nspaces']:2d} last_w={r['last_w']:5.1f} "
              f"share_sp={r['share_of_spaces']:.3f} per_space={r['per_space']:.2f} share_w={r['share_of_word']:.2f} "
              f"{'KEPT' if r['kept'] else 'wrapped'}{'' if r['exact'] or not r['kept'] else ' (+more)'} lines={r['nlines']}")
    groups = collections.defaultdict(list)
    for r in rows:
        groups[(r["face"], r["nspaces"], r["last"])].append(r)
    print("\nper group: largest kept overflow / smallest wrapped overflow")
    for k in sorted(groups):
        g = groups[k]
        kept = [r for r in g if r["kept"]]
        wrapped = [r for r in g if not r["kept"]]
        mk = max(kept, key=lambda r: r["over"]) if kept else None
        mw = min(wrapped, key=lambda r: r["over"]) if wrapped else None
        print(f"  {k}: kept<= {mk['over'] if mk else None} (share_sp {mk['share_of_spaces'] if mk else None}, per_space {mk['per_space'] if mk else None}, share_w {mk['share_of_word'] if mk else None})"
              f" | wrapped>= {mw['over'] if mw else None} (share_sp {mw['share_of_spaces'] if mw else None}, per_space {mw['per_space'] if mw else None}, share_w {mw['share_of_word'] if mw else None})")
    if out:
        json.dump(rows, open(out, "w"), indent=1)

if __name__ == "__main__":
    main()

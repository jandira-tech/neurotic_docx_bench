#!/usr/bin/env python3
"""Harvest Word's comment-balloon geometry from the corpus Word PDFs (the
pane, every balloon box, its label and text spans, the connector and the
tinted range) into a JSON of per-balloon rows and a printed summary:
author colour → tint pairs, box x offsets from the pane, text insets,
font sizes vs page scale, line pitch, stacking gaps, connector dash/width.

    word_balloon_spec.py [--out /tmp/balloon_spec.json] [--limit N]
"""
from __future__ import annotations
import csv, json, sys, statistics, collections
from pathlib import Path
import pymupdf as fitz

ROOT = Path(__file__).resolve().parents[1]
W = ROOT / "corpus" / "word"
GREY = (0.949, 0.949, 0.949)

def near(a, b, tol=0.02): return all(abs(x - y) < tol for x, y in zip(a, b))

def page_rows(doc_id, state, pdf):
    rows = []
    d = fitz.open(pdf)
    for pno, pg in enumerate(d):
        drs = pg.get_drawings()
        panes = [x["rect"] for x in drs if x.get("fill") and near(x["fill"], GREY) and x["rect"].width > 100]
        if not panes:
            continue
        pane = panes[0]
        W_, H_ = pg.rect.width, pg.rect.height
        # balloons: filled rounded paths with a 'c' item, inside the pane, not grey
        boxes = [x for x in drs if x["rect"].x0 >= pane.x0 and x.get("fill") and not near(x["fill"], GREY)
                 and any(it[0] == "c" for it in x["items"]) and x["rect"].width > 50 and 6 < x["rect"].height < 500]
        strokes = [x for x in drs if x.get("color") and x.get("fill") is None]
        spans = []
        for b in pg.get_text("dict")["blocks"]:
            if b.get("type") != 0: continue
            for l in b["lines"]:
                for s in l["spans"]:
                    if s["bbox"][0] >= pane.x0 - 1: spans.append(s)
        boxes.sort(key=lambda x: x["rect"].y0)
        for i, bx in enumerate(boxes):
            r = bx["rect"]
            border = [x for x in strokes if abs(x["rect"].x0 - r.x0) < 1.0 and abs(x["rect"].y0 - r.y0) < 1.0 and abs(x["rect"].x1 - r.x1) < 1.0 and abs(x["rect"].y1 - r.y1) < 1.0]
            stroke = border[0]["color"] if border else None
            width = border[0].get("width") if border else None
            inside = [s for s in spans if r.y0 - 0.5 <= s["bbox"][1] and s["bbox"][3] <= r.y1 + 0.5 and s["bbox"][0] >= r.x0 - 0.5]
            label = [s for s in inside if "Commented [" in s["text"] or "Comment" in s["font"]]
            lab = next((s for s in inside if s["text"].startswith("Commented [")), None)
            ys = sorted(s["bbox"][1] for s in inside); lines = []
            for y in ys:
                if not lines or y - lines[-1] > 2.0: lines.append(y)
            pitch = statistics.median([b - a for a, b in zip(lines, lines[1:])]) if len(lines) > 1 else None
            # connector: dashed strokes in the author colour ending at the box's left edge
            conn = [x for x in strokes if x.get("dashes") and stroke and near(x["color"], stroke, 0.03) and abs(x["rect"].x1 - r.x0) < 1.5 and r.y0 - 2 <= x["rect"].y1 <= r.y1 + 2]
            horiz = [x for x in strokes if x.get("dashes") and stroke and near(x["color"], stroke, 0.03) and x["rect"].x1 < pane.x0 + 1 and abs(x["rect"].height) < 0.5]
            tints = [x["rect"] for x in drs if x.get("fill") and bx.get("fill") and near(x["fill"], bx["fill"], 0.01) and x["rect"].x1 < pane.x0 and x["rect"].height < 40]
            rows.append(dict(doc=doc_id, state=state, page=pno + 1, page_w=W_, page_h=H_,
                pane=[pane.x0, pane.y0, pane.x1, pane.y1], box=[r.x0, r.y0, r.x1, r.y1],
                fill=bx.get("fill"), stroke=stroke, stroke_w=width,
                label_font=lab["font"] if lab else None, label_size=lab["size"] if lab else None,
                label_text=lab["text"] if lab else None, label_bbox=lab["bbox"] if lab else None,
                text_fonts=sorted({s["font"] for s in inside if s is not lab}), text_size=next((s["size"] for s in inside if s is not lab), None),
                n_lines=len(lines), first_line_y=lines[0] if lines else None, pitch=pitch,
                text_x0=min((s["bbox"][0] for s in inside), default=None), text_x1=max((s["bbox"][2] for s in inside), default=None),
                conn_dash=conn[0]["dashes"] if conn else None, conn_w=conn[0].get("width") if conn else None,
                conn_rect=[conn[0]["rect"].x0, conn[0]["rect"].y0, conn[0]["rect"].x1, conn[0]["rect"].y1] if conn else None,
                horiz_x0=min((x["rect"].x0 for x in horiz), default=None), horiz_x1=max((x["rect"].x1 for x in horiz), default=None),
                horiz_y=horiz[0]["rect"].y0 if horiz else None,
                tints=[[t.x0, t.y0, t.x1, t.y1] for t in tints][:6],
                gap_above=(r.y0 - boxes[i - 1]["rect"].y1) if i else None,
                bx=r.x0 - pane.x0, bx1=pane.x1 - r.x1, sc=pane.x0 / W_,
                tx=(min((s["bbox"][0] for s in inside), default=r.x0) - r.x0), 
                ty=(lines[0] - r.y0) if lines else None, hl=(r.y1 - r.y0) / max(len(lines), 1),
                ls=(lab["size"] / (pane.x0 / W_)) if lab else None))
    return rows

def main():
    out = "/tmp/balloon_spec.json"; limit = None
    a = sys.argv[1:]
    if "--out" in a: out = a[a.index("--out") + 1]
    if "--limit" in a: limit = int(a[a.index("--limit") + 1])
    docs = [r for r in csv.DictReader((W / "documents.csv").open()) if r["state"].startswith("with_comments") and r["pdf"]]
    rows = []
    for r in docs[:limit]:
        p = W / r["pdf"]
        if p.exists():
            try: rows += page_rows(r["id"], r["state"], p)
            except Exception as e: print("skip", r["id"], e, file=sys.stderr)
    Path(out).write_text(json.dumps(rows, indent=0))
    print(len(rows), "balloons from", len({r['doc'] for r in rows}), "documents ->", out)
    def med(k, f=lambda r: True):
        xs = [r[k] for r in rows if r.get(k) is not None]
        return (round(statistics.median(xs), 3), round(min(xs), 3), round(max(xs), 3), len(xs)) if xs else None
    print("box.x0 - pane.x0:", med("bx"))
    print("pane.x1 - box.x1:", med("bx1"))
    print("text_x0 - box.x0:", med("tx"))
    print("box.x1 - text_x1 (max line end):", med("tx1"))
    print("first_line_y - box.y0:", med("ty"))
    print("label_size:", med("label_size"), " text_size:", med("text_size"), " pitch:", med("pitch"))
    print("page scale (pane.x0/page_w):", med("sc"))
    print("label_size / scale-free (label_size / (pane.x0/page_w)):", med("ls"))
    print("stroke_w:", med("stroke_w"), " conn_w:", med("conn_w"))
    print("gap_above:", med("gap_above"))
    print("box height per line (h/n_lines):", med("hl"))
    print("label fonts:", collections.Counter(r["label_font"] for r in rows).most_common(4))
    print("text fonts:", collections.Counter(tuple(r["text_fonts"]) for r in rows).most_common(6))
    print("conn dashes:", collections.Counter(str(r["conn_dash"]) for r in rows).most_common(3))
    pairs = collections.Counter((tuple(round(c, 3) for c in r["stroke"]) if r["stroke"] else None, tuple(round(c, 3) for c in r["fill"])) for r in rows)
    print("stroke → fill pairs:")
    for (s, f), n in pairs.most_common(12): print("  ", s, "→", f, n)

if __name__ == "__main__": main()

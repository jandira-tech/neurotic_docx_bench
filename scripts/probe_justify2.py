# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Round 2 of the justified-line squeeze probes (see probe_justify.py).

Round 1 (Calibri 11 / Times 12, 9 and 14–17 spaces) put Word's cap on the
overflow it absorbs at 5.0pt (Calibri) and 6.2pt (Times) whatever the
number of spaces: 2.0–2.07 space widths, or 0.46–0.52 em. Within one
face both scale alike, so this round varies the space-to-em ratio
(Cambria 0.22, Arial 0.28, Tahoma 0.31, Verdana 0.35 em) and, in Calibri,
the number of spaces (4 and 25) to tell the two apart and to confirm the
cap is not a share of the line's spaces.

Usage: uv run python scripts/probe_justify2.py OUTDIR
"""
import json, os, sys, zipfile, itertools, random
import fitz
from probe_justify import MEASURE, VOCAB, docx, fine_word, width

D = "/Applications/Microsoft Word.app/Contents/Resources/DFonts/"
FONTS = {
    "Verdana": (D + "Verdana.ttf", 12.0),
    "Tahoma": (D + "tahoma.ttf", 12.0),
    "Arial": (D + "arial.ttf", 12.0),
    "Cambria": (D + "Cambria.ttc", 12.0),
    "Calibri": (D + "Calibri.ttf", 11.0),
}
LAST = "tempor"

def build(face, over, nspaces, rng):
    """Line 1 = (nspaces - 1) free words + a fine word + LAST, nspaces
    spaces, natural width MEASURE + over. Free words are concatenations
    of vocabulary words so that 4 spaces fit a 468pt line."""
    path, size = FONTS[face]
    font = fitz.Font(fontfile=path)
    space = width(font, size, " ")
    last_w = width(font, size, LAST)
    for _ in range(200):
        n_free = nspaces - 1
        budget = MEASURE + over - nspaces * space - last_w - 20.0  # ~20pt for the fine word
        avg = budget / n_free
        free = []
        for i in range(n_free):
            w = ""
            target = avg if i < n_free - 1 else budget - sum(width(font, size, x) for x in free)
            while width(font, size, w) < target - 12.0 or not w:
                w += rng.choice(VOCAB)
                if width(font, size, w) > target + 8.0 and len(w) > 2:
                    w = w[: len(w) // 2] or w
                    break
            free.append(w)
        slack = MEASURE + over - (sum(width(font, size, x) for x in free) + nspaces * space + last_w)
        if 4.0 <= slack <= 60.0:
            fine = fine_word(font, size, slack)
            line1 = free + [fine, LAST]
            natural = sum(width(font, size, w) for w in line1) + nspaces * space
            if abs(natural - MEASURE - over) <= 0.3:
                tail = " ".join(rng.choice(VOCAB) for _ in range(14))
                return " ".join(line1) + " " + tail, natural, last_w, space
    raise RuntimeError(f"no probe for {face} {over} {nspaces}")

def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    rng = random.Random(11)
    manifest = []
    plan = []
    for face in ("Verdana", "Tahoma", "Arial", "Cambria"):
        space = width(fitz.Font(fontfile=FONTS[face][0]), FONTS[face][1], " ")
        overs = sorted({round(k * space, 2) for k in (1.5, 1.8, 1.9, 2.0, 2.1, 2.2, 2.4, 2.8)} | {4.5, 5.0, 5.5, 6.0})
        plan += [(face, 9, o) for o in overs]
    for nsp in (4, 25):
        plan += [("Calibri", nsp, o) for o in (3.0, 4.0, 4.5, 5.0, 5.5, 6.0, 7.0)]
    for face, nsp, over in plan:
        text, natural, last_w, space = build(face, over, nsp, rng)
        fid = f"j2_{face.lower()}_s{nsp}_o{str(over).replace('.', 'p')}"
        parts = docx(text, face, FONTS[face][1])
        with zipfile.ZipFile(os.path.join(out, fid + ".docx"), "w", zipfile.ZIP_DEFLATED) as z:
            for name, data in parts.items():
                z.writestr(name, data)
        manifest.append(dict(id=fid, face=face, size=FONTS[face][1], nspaces=nsp, last=LAST, last_w=round(last_w, 2),
                             space=round(space, 3), over=round(natural - MEASURE, 3), text=text))
    json.dump(manifest, open(os.path.join(out, "manifest.json"), "w"), indent=1)
    print(len(manifest), "probes")

if __name__ == "__main__":
    main()

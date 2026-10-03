# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Round 3 of the justified-line squeeze probes: the last-word cap.

Rounds 1–2 (probe_justify.py, probe_justify2.py) fixed the first bound:
Word narrows a justified line's spaces by up to one quarter of their
total width to keep the last word (Calibri, Times, Cambria, Arial,
Tahoma, Verdana; 4–25 spaces). The probes whose last word was the
11pt "ad" wrapped earlier (Calibri between 4.0 and 5.0pt, Times between
4.2 and 6.2pt), so a second bound depends on the last word. This round
holds 20 spaces (quarter bound 12.4pt in Calibri 11) and varies the
last word's width and the overflow.

Usage: uv run python scripts/probe_justify3.py OUTDIR
"""
import json, os, sys, zipfile, random
import fitz
from probe_justify import MEASURE, VOCAB, docx, fine_word, width

D = "/Applications/Microsoft Word.app/Contents/Resources/DFonts/"
FONTS = {
    "Calibri": (D + "Calibri.ttf", 11.0),
    "Times New Roman": (D + "times.ttf", 12.0),
}
LASTS = {"Calibri": ("ad", "sed", "elit", "enim", "tempor", "laboris", "consectetur"),
         "Times New Roman": ("ad", "elit", "laboris")}
NSPACES = 20

def build(face, over, nspaces, last, rng):
    path, size = FONTS[face]
    font = fitz.Font(fontfile=path)
    space = width(font, size, " ")
    last_w = width(font, size, last)
    for _ in range(300):
        n_free = nspaces - 1
        budget = MEASURE + over - nspaces * space - last_w - 20.0
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
            line1 = free + [fine, last]
            natural = sum(width(font, size, w) for w in line1) + nspaces * space
            if abs(natural - MEASURE - over) <= 0.3:
                tail = " ".join(rng.choice(VOCAB) for _ in range(14))
                return " ".join(line1) + " " + tail, natural, last_w, space
    raise RuntimeError(f"no probe for {face} {over} {nspaces} {last}")

def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    rng = random.Random(13)
    manifest = []
    overs = [x / 2 for x in range(4, 25)]  # 2.0 .. 12.0 by 0.5
    for face, lasts in LASTS.items():
        for last in lasts:
            for over in overs:
                text, natural, last_w, space = build(face, over, NSPACES, last, rng)
                fid = f"j3_{face[0].lower()}_{last}_o{str(over).replace('.', 'p')}"
                parts = docx(text, face, FONTS[face][1])
                with zipfile.ZipFile(os.path.join(out, fid + ".docx"), "w", zipfile.ZIP_DEFLATED) as z:
                    for name, data in parts.items():
                        z.writestr(name, data)
                manifest.append(dict(id=fid, face=face, size=FONTS[face][1], nspaces=NSPACES, last=last, last_w=round(last_w, 2),
                                     space=round(space, 3), over=round(natural - MEASURE, 3), text=text))
    json.dump(manifest, open(os.path.join(out, "manifest.json"), "w"), indent=1)
    print(len(manifest), "probes")

if __name__ == "__main__":
    main()

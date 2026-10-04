# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Round 4 of the justified-line squeeze probes: the last-word cap at a
finer step, across sizes.

Round 3 (20 spaces, Calibri 11 / Times 12, 0.5pt steps) bounded the cap
near a third of the word plus a point; an older Times 11 probe kept
"times" (24pt) at 9.7pt and moved it at 9.92, which a single linear law
does not reach. This round steps 0.2pt from 0.30 to 0.46 of the word in
Times 11, Times 12 and Calibri 11 (and Calibri 14 for the size law).

Usage: uv run python scripts/probe_justify4.py OUTDIR
"""
import json, os, sys, zipfile, random
import fitz
from probe_justify import MEASURE, VOCAB, docx, fine_word, width
from probe_justify3 import build, FONTS as F3

D = "/Applications/Microsoft Word.app/Contents/Resources/DFonts/"
FONTS = {
    "Times New Roman": (D + "times.ttf", 11.0),
    "Times12": (D + "times.ttf", 12.0),
    "Calibri": (D + "Calibri.ttf", 11.0),
    "Calibri14": (D + "Calibri.ttf", 14.0),
}
FACE_NAME = {"Times New Roman": "Times New Roman", "Times12": "Times New Roman", "Calibri": "Calibri", "Calibri14": "Calibri"}
WORDS = ("ad", "times", "enim", "laboris")
NSPACES = 20

def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    rng = random.Random(17)
    manifest = []
    for key, (path, size) in FONTS.items():
        F3[key] = (path, size)  # build() looks the face up in probe_justify3.FONTS
        font = fitz.Font(fontfile=path)
        for last in WORDS:
            w = width(font, size, last)
            over = round(0.30 * w, 1)
            while over <= 0.46 * w:
                text, natural, last_w, space = build(key, over, NSPACES, last, rng)
                fid = f"j4_{key.lower().replace(' ', '')}_{last}_o{str(over).replace('.', 'p')}"
                parts = docx(text, FACE_NAME[key], size)
                with zipfile.ZipFile(os.path.join(out, fid + ".docx"), "w", zipfile.ZIP_DEFLATED) as z:
                    for name, data in parts.items():
                        z.writestr(name, data)
                manifest.append(dict(id=fid, face=key, size=size, nspaces=NSPACES, last=last, last_w=round(last_w, 2),
                                     space=round(space, 3), over=round(natural - MEASURE, 3), text=text))
                over = round(over + 0.2, 1)
    json.dump(manifest, open(os.path.join(out, "manifest.json"), "w"), indent=1)
    print(len(manifest), "probes")

if __name__ == "__main__":
    main()

# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import glob, fitz, re
for stem,needles in (("62780fc256",["Call to Order","Public Comment","Texas Public F"]),("9453196efa",["Call to order"]),("1fef0faeb8",["in the case of a dispute"])):
    pdf=glob.glob(f"corpus/word/clean/pdf/{stem}*.pdf")[0]; d=fitz.open(pdf)
    for pi,page in enumerate(d):
        spans=[]
        for b in page.get_text("dict")["blocks"]:
            for l in b.get("lines",[]):
                for s in l["spans"]:
                    spans.append((round(s["origin"][1],2), round(s["bbox"][0],2), round(s["bbox"][2],2), s["text"]))
        for n in needles:
            hit=[s for s in spans if n in s[3]]
            for h in hit[:1]:
                same=[s for s in spans if abs(s[0]-h[0])<0.6 and s[1]<h[1]]
                print(stem, "p%d"%(pi+1), repr(n), "text x0=%.2f"%h[1], "labels before it:", [(s[1],s[2],s[3]) for s in same])
        if any(any(n in s[3] for s in spans) for n in needles): break
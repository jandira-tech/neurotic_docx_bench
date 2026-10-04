# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import json,subprocess,collections
exec(open('an.py').read().split("print(len(C)")[0])
import freetype
F={'Times New Roman':'/System/Library/Fonts/Supplemental/Times New Roman.ttf','Calibri':'/Applications/Microsoft Word.app/Contents/Resources/DFonts/Calibri.ttf',
   'Arial':'/System/Library/Fonts/Supplemental/Arial.ttf','Courier New':'/System/Library/Fonts/Supplemental/Courier New.ttf',
   'Georgia':'/System/Library/Fonts/Supplemental/Georgia.ttf','Verdana':'/System/Library/Fonts/Supplemental/Verdana.ttf'}
faces={k:freetype.Face(p) for k,p in F.items()}
def adv(face,ch,ppem):
    face.set_pixel_sizes(0,ppem); face.load_char(ch, freetype.FT_LOAD_DEFAULT|freetype.FT_LOAD_TARGET_MONO)
    return face.glyph.advance.x/64.0
def lin(face,ch):
    face.load_char(ch, freetype.FT_LOAD_NO_SCALE); return face.glyph.advance.x/face.units_per_EM*12
for ppem in list(range(8,41))+[48,50,64,96,100,200]:
    acc=collections.Counter(); tot=collections.Counter()
    for c,word in zip(C,cp):
        f=faces[c['font']]; s=12/ppem
        txt='ab '*c['K']+'i'*c['j']+' tail'
        hw=sum(adv(f,ch,ppem) for ch in set(txt) for _ in [0]) # placeholder
        w=sum(adv(f,ch,ppem)*txt.count(ch) for ch in set(txt))*s
        pred = w <= 468.0+1e-6
        tot[c['font']]+=1; acc[c['font']]+= (pred==word)
    print(ppem, ' '.join(f"{k.split()[0][:5]}:{acc[k]}/{tot[k]}" for k in F))
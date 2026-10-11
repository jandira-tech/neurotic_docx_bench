# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import fitz, glob, os
for f in sorted(glob.glob('/tmp/hpprobe/pdf/*.pdf')):
    p=fitz.open(f)[0]; name=os.path.basename(f)
    lines=[]
    for b in p.get_text('rawdict')['blocks']:
        for l in b['lines']:
            chars=[c for s in l['spans'] for c in s['chars']]
            txt=''.join(c['c'] for c in chars)
            if not txt.strip(): 
                lines.append((round(chars[0]['origin'][1],2), round(chars[0]['origin'][0],2), round(l['spans'][0]['size'],2), 'MARK', 0, 0)); continue
            xs=[c['bbox'][0] for c in chars]
            adv=round((xs[-1]-xs[0])/(len(xs)-1),4) if len(xs)>1 else 0
            lines.append((round(chars[0]['origin'][1],2), round(xs[0],2), round(l['spans'][0]['size'],2), txt.rstrip()[:40], len(txt.rstrip()), adv))
    lines.sort()
    imgs=[tuple(round(v,2) for v in p.get_image_bbox(i)) for i in p.get_images(full=True)]
    if name.startswith('h'):
        print(name, 'imgs', imgs)
        for y,x,sz,t,n,adv in lines[:7]: print(f'   y {y:7.2f} x {x:6.2f} sz {sz:5.2f} {t!r}')
    else:
        first=lines[0]
        print(f'{name:22s} line1 chars {first[4]:3d} adv {first[5]:.4f} x1 {round(first[1]+first[5]*(first[4]-1)+first[5],2):7.2f}  text {first[3]!r}')
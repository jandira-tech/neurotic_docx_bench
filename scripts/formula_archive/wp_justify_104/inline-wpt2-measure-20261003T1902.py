# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import fitz, glob
nat={'tnr':456.2,'arial':444.85}
for f in sorted(glob.glob('/tmp/wpt2/pdf/*.pdf')):
    p=fitz.open(f)[0]
    ls=[l for b in p.get_text('rawdict')['blocks'] if 'lines' in b for l in b['lines']]
    ls.sort(key=lambda l: l['spans'][0]['chars'][0]['origin'][1])
    chars=[c for s in ls[0]['spans'] for c in s['chars']]; txt=''.join(c['c'] for c in chars).rstrip()
    kept='mmmm' in txt
    # advance of the letters 'alpha' vs natural (first 5 glyphs) and of a space
    advs=[chars[i+1]['bbox'][0]-chars[i]['bbox'][0] for i in range(len(chars)-1)]
    letters=[a for a,c in zip(advs,chars) if c['c']!=' ']; spaces=[a for a,c in zip(advs,chars) if c['c']==' ']
    name=f.split('/')[-1][:-4]; fam='tnr' if 'tnr' in name else 'arial'
    print(f"{name:14s} {'KEEP' if kept else 'wrap'} chars {len(txt):3d} x1 {round(chars[-1]['bbox'][2],2):7.2f} letters a:{round(advs[0],3)} l:{round(advs[1],3)} p:{round(advs[2],3)} spaces {round(min(spaces),3)}..{round(max(spaces),3)}")
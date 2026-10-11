# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import json, os, glob, shutil, fitz
m=json.load(open('/tmp/hold-word/map.json'))
out=open('/private/tmp/claude-501/-Users-arthrod-temp-T-jubarte-redlines-jubarte-app/04b835d2-6536-4ebd-a05f-091729378476/tasks/bvdtt16ow.output').read()
diff=[l.split()[0] for l in out.splitlines() if ' DIFF ' in l]
replaced=[]
for h in diff:
    src=m[h]; stem=os.path.basename(src)[:-5]
    refs=glob.glob(f'{os.path.dirname(os.path.dirname(src))}/pdf/{stem}*.pdf')
    assert len(refs)==1, (h, refs)
    fresh=f'/tmp/hold-word/pdf/{h}.pdf'
    shutil.copy(refs[0], f'/tmp/hold-word/{h}_old_ref.pdf')
    shutil.copy(fresh, refs[0]); replaced.append(refs[0])
    print('replaced', refs[0][-70:])
open('/tmp/hold-word/replaced.txt','w').write('\n'.join(replaced)+'\n')
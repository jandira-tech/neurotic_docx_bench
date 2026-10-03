# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import os
for f in os.listdir('src'): os.remove('src/'+f)
doc('src/o50.docx',[r5,r0])
doc('src/o10.docx',[r1,r0])
doc('src/o15.docx',[r1,r5])
doc('src/o51.docx',[r5,r1])
rA=[(1000,'pct',1)]+[(1440,'dxa',1)]*5
rB=[(2880,'dxa',1)]*2+[(500,'pct',1)]*4
doc('src/oAB.docx',[rA,rB])
doc('src/oBA.docx',[rB,rA])
doc('src/oA.docx',[rA])
doc('src/oB.docx',[rB])
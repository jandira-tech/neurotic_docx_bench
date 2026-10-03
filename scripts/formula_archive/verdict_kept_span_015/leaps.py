# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
p = "/tmp/prose_summary.py"; s = open(p).read()
s = s.replace('''    vs = [v for v in ra.verdicts(R) if v.verdict != "unchanged" and (v.a_index == 2 or (v.a_index is None and v.b_index == 2))]''',
'''    ia, ib = ra.identity(ra.rebuild(R, "orig"), A), ra.identity(ra.rebuild(R, "rev"), B)
    phantom = not (ia["exact"] and ib["exact"])
    vs = [v for v in ra.verdicts(R) if v.verdict != "unchanged" and (v.a_index == 2 or (v.a_index is None and v.b_index == 2))]''')
s = s.replace('''    rec = {**m, "verdict": verdict, "max_chars": mx,''', '''    rec = {**m, "verdict": verdict, "phantom": phantom, "max_chars": mx,''')
open(p, "w").write(s)
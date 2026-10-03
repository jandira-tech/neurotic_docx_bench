# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import sys,re,subprocess
pdf,page,lo,hi=sys.argv[1],sys.argv[2],float(sys.argv[3]),float(sys.argv[4])
s=subprocess.run(['mutool','draw','-F','stext','-o','-',pdf,page],capture_output=True,text=True).stdout
for m in re.finditer(r'<font name="([^"]*)" size="([^"]*)">(.*?)</font>',s,re.S):
    ch=re.findall(r'<char c="([^"]*)" quad="([\d.]+) [\d.]+ ([\d.]+)[^"]*" x="[\d.]+" y="([\d.]+)"',m.group(3))
    ch=[c for c in ch if lo<=float(c[3])<=hi]
    if ch: print(m.group(1),m.group(2),f'y{float(ch[0][3]):.1f}',' '.join(f'{c[0]}@{float(c[1]):.1f}' for c in ch))
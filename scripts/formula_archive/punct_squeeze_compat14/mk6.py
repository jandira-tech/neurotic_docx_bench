# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
exec(open('mk3.py').read().split("cx='<w:compat")[0])
import os
os.makedirs('src9',exist_ok=True)
CSC='<w:characterSpacingControl w:val="compressPunctuation"/>'
ALL='<w:spaceForUL/><w:balanceSingleByteDoubleByteWidth/><w:doNotLeaveBackslashAlone/><w:ulTrailSpace/><w:doNotExpandShiftReturn/><w:adjustLineHeightInTable/><w:useFELayout/>'
B=sq('left')
mk2('src9/x0_ctrl.docx',B,'',CSC)
mk2('src9/x1_all.docx',B,ALL,CSC)
for f in ['spaceForUL','balanceSingleByteDoubleByteWidth','doNotLeaveBackslashAlone','ulTrailSpace','doNotExpandShiftReturn','adjustLineHeightInTable','useFELayout']:
    mk2(f'src9/x_{f}.docx',B,f'<w:{f}/>',CSC)
mk2('src9/x2_kern.docx',B.replace('<w:sz w:val="24"/>','<w:kern w:val="2"/><w:sz w:val="24"/>'),'',CSC)
mk2('src9/x3_zh.docx',B.replace('<w:sz w:val="24"/>','<w:sz w:val="24"/><w:lang w:val="en-US" w:eastAsia="zh-CN"/>'),'',CSC)
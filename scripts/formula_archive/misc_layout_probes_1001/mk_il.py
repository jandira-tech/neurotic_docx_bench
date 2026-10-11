# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
from mkbase import mk
def shape(cy):
    return ('<w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing">'
     f'<wp:extent cx="1829435" cy="{cy}"/><wp:docPr id="1" name="r"/>'
     '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.microsoft.com/office/word/2010/wordprocessingShape">'
     '<wps:wsp xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape"><wps:cNvSpPr/><wps:spPr>'
     f'<a:xfrm><a:off x="0" y="0"/><a:ext cx="1829435" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
     '<a:solidFill><a:srgbClr val="434242"/></a:solidFill></wps:spPr><wps:bodyPr/></wps:wsp></a:graphicData></a:graphic></wp:inline></w:drawing>')
def doc(sz, text_after=True):
    pp='<w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr>'
    rf=lambda f,s: f'<w:rPr><w:rFonts w:ascii="{f}" w:hAnsi="{f}"/><w:sz w:val="{s}"/></w:rPr>'
    p1=f'<w:p>{pp}<w:r>{rf("Arial",20)}<w:t>TOP</w:t></w:r></w:p>'
    rule=f'<w:p>{pp}<w:r>{rf("Calibri",sz)}{shape(6097)}</w:r>' + (f'<w:r>{rf("Arial",20)}<w:t xml:space="preserve"> </w:t></w:r>' if text_after else '') + '</w:p>'
    p3=f'<w:p>{pp}<w:r>{rf("Arial",20)}<w:t>NEXT</w:t></w:r></w:p>'
    return p1+rule+p3
for sz in [20,44,72]:
    mk(f'src/il_{sz}.docx',doc(sz),15)
    mk(f'src/il_{sz}_alone.docx',doc(sz,False),15)
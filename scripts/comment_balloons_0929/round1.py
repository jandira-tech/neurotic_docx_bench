import re, sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / "temp/T/comment_balloons"))
from ab import read, write
C = Path("corpus/word"); OUT = Path.home() / "temp/T/comment_balloons/r1/docx"
SECT = re.compile(r"<w:sectPr\b.*?</w:sectPr>", re.S)

def portrait(s):  # landscape pgSz -> portrait
    return re.sub(r'<w:pgSz w:w="(\d+)" w:h="(\d+)" w:orient="landscape"\s*/>', lambda m: f'<w:pgSz w:w="{m.group(2)}" w:h="{m.group(1)}"/>', s)
def landscape(s):
    return re.sub(r'<w:pgSz w:w="(\d+)" w:h="(\d+)"\s*/>', lambda m: f'<w:pgSz w:w="{max(int(m.group(1)), int(m.group(2)))}" w:h="{min(int(m.group(1)), int(m.group(2)))}" w:orient="landscape"/>', s)
def mid_sects(b):  # sectPr inside a paragraph's pPr
    return [m for m in SECT.finditer(b) if m.start() < b.rindex("<w:sectPr")]

z = C / "with_comments_tracking/docx/b175a00954_file_27.docx"; b = read(z)
write(z, OUT / "Z00_file27_control.docx", {})
write(z, OUT / "Z01_file27_landscape_to_portrait.docx", {"word/document.xml": portrait(b)})
ms = mid_sects(b)
land = [m for m in ms if 'orient="landscape"' in m.group(0)][0]
write(z, OUT / "Z02_file27_drop_landscape_break.docx", {"word/document.xml": b[:land.start()] + b[land.end():]})
bb = b
for m in reversed(ms): bb = bb[:m.start()] + bb[m.end():]
write(z, OUT / "Z03_file27_single_section.docx", {"word/document.xml": bb})

def sandwich(b, mid_orient):
    final = SECT.findall(b)[-1]
    final_plain = re.sub(r"<w:sectPrChange\b.*?</w:sectPrChange>", "", final, flags=re.S)
    body_ps = [m for m in re.finditer(r"<w:p\b[^>]*>.*?</w:p>|<w:p\b[^>]*/>", b[:b.rindex("<w:sectPr")], re.S)]
    # only top-level paragraphs: skip ones inside tables by checking tbl depth
    top = [m for m in body_ps if b[:m.start()].count("<w:tbl>") == b[:m.start()].count("</w:tbl>")]
    i1, i2 = top[len(top) // 3], top[2 * len(top) // 3]
    brk = lambda s: f"<w:p><w:pPr>{s}</w:pPr></w:p>"
    s2 = landscape(final_plain) if mid_orient == "L" else final_plain
    return b[:i1.end()] + brk(final_plain) + b[i1.end():i2.end()] + brk(s2) + b[i2.end():]

for tag, stem in (("S1", "with_comments_tracking/docx/a4c38b1bf5_4c17189eb7a543ae96f42443a9f4001a3be8fec6e47f7481"),
                  ("S2", "with_comments_clean/docx/0f6e71381a_7057d180ffd30c96a71aa95e32993d39bf2e59a1eff850b7")):
    s = C / f"{stem}.docx"; b = read(s)
    write(s, OUT / f"{tag}0_control.docx", {})
    write(s, OUT / f"{tag}1_sandwich_P_L_P.docx", {"word/document.xml": sandwich(b, "L")})
    write(s, OUT / f"{tag}2_sandwich_P_P_P.docx", {"word/document.xml": sandwich(b, "P")})
    last = b.rindex("<w:sectPr")
    write(s, OUT / f"{tag}3_all_landscape.docx", {"word/document.xml": b[:last] + landscape(b[last:])})
print(sorted(p.name for p in OUT.iterdir()))

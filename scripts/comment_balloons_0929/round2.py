import sys; from pathlib import Path
sys.path.insert(0, str(Path.home() / "temp/T/comment_balloons"))
from ab import read, write
from blocklib import blocks, has_marker, drop
Z = Path.home() / "temp/T/neurotic_docx_bench/corpus/word/with_comments_tracking/docx/b175a00954_file_27.docx"
OUT = Path.home() / "temp/T/comment_balloons/r2/docx"
b = read(Z); bl = blocks(b)
rem = [i for i, x in enumerate(bl) if not has_marker(b, x)]
k = 8; chunks = [rem[j * len(rem) // k:(j + 1) * len(rem) // k] for j in range(k)]
write(Z, OUT / "R2_00_control.docx", {})
write(Z, OUT / "R2_99_drop_all_unmarked.docx", {"word/document.xml": drop(b, bl, rem)})
for j, c in enumerate(chunks):
    write(Z, OUT / f"R2_{j+1:02d}_drop_blocks_{c[0]}-{c[-1]}.docx", {"word/document.xml": drop(b, bl, c)})

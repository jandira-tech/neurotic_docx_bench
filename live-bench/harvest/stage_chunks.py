"""Copy every docx under really_broken into <out>/cNN/in folders (copies; originals untouched).
usage: stage_chunks.py <really_broken> <out>"""
import shutil, sys
from pathlib import Path
rb, out = Path(sys.argv[1]), Path(sys.argv[2])
groups = [("tool_redlines/repair_prompt", 12), ("fixtures/repair_prompt", 8),
          ("tool_redlines/unconfirmed", 6), ("tool_redlines/crashes_word", 4)]
n = 0
for sub, size in groups:
    files = sorted(p for p in (rb / sub).glob("*.docx") if not p.name.startswith("~$"))
    for i in range(0, len(files), size):
        d = out / f"c{n:02d}" / "in"; d.mkdir(parents=True)
        for f in files[i:i + size]:
            shutil.copy2(f, d / f.name)
        print(f"c{n:02d} {sub} {len(files[i:i + size])}"); n += 1

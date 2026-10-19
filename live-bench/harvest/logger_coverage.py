"""Did word_screen_log.py capture Word's dialog for each file of a logger_all run?

For every <run>/cNN/in/*.docx: Word's verdict (driver stdout FAIL line, or a PDF in cNN/pdf) and
the DIALOG lines of the screen log, between the chunk's start and the next chunk's start, whose
text names the file. Names are matched loosely, because OCR wraps them across lines with a hyphen: both sides
lose spaces, '|', '-', '_' and case; a fixture is matched on the first 16 hex of its sha256, a tool
redline on <tool><run><seq>. Dialogs naming no file (Microsoft Error Reporting, the follow-up OK box
cut short) are counted per chunk.

usage: logger_coverage.py <screen_log> <logger_all_dir>   writes <logger_all_dir>/coverage.csv
"""

import csv
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

log, root = Path(sys.argv[1]), Path(sys.argv[2])
day = datetime.now().strftime("%Y-%m-%d")


def norm(s: str) -> str:
    return re.sub(r"[\s|_\-]", "", s).lower()


# DIALOG events: (time, header, text)
events, cur = [], None
for line in log.read_text(errors="replace").splitlines():
    m = re.match(r"(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d{3}) DIALOG (\[.*)", line)
    if m:
        cur = [datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S.%f"), m.group(2), ""]
        events.append(cur)
    elif cur and line.startswith("    says: "):
        cur[2] = line[10:]
        cur = None

chunks = sorted(p for p in root.glob("c[0-9][0-9]") if (p / "start").exists())
starts = [datetime.strptime(f"{day} {(c / 'start').read_text().strip()}", "%Y-%m-%d %H:%M:%S") for c in chunks]
rows, unnamed = [], Counter()
for i, c in enumerate(chunks):
    lo, hi = starts[i], starts[i + 1] if i + 1 < len(starts) else datetime.max
    evs = [e for e in events if lo <= e[0] < hi]
    out = (c / "word.stdout").read_text(errors="replace") if (c / "word.stdout").exists() else ""
    fails = {m.group(1): re.sub(r"\s+", " ", m.group(2)).strip()
             for m in re.finditer(r"FAIL (\S+\.docx):[ \t]*(.*?)(?=\n\s*FAIL |\Z)", out[out.rfind("│ failed"):], re.S)}
    pdfs = {p.stem for p in (c / "pdf").glob("*.pdf")} if (c / "pdf").exists() else set()
    named = set()
    for f in sorted((c / "in").glob("*.docx")):
        m = re.match(r"(docxodus|jubarte|superdoc-redlines)__([0-9a-f]{8})_(\d{4})$", f.stem)
        key = norm(f"{m.group(1)}{m.group(2)}{m.group(3)}") if m else f.stem[:16].lower()
        hits = [e for e in evs if key in norm(e[2])]
        named |= {id(e) for e in hits}
        verdict = "opens_ok" if f.stem in pdfs else ("broken: " + fails[f.name][:70] if f.name in fails
                                                     else "no result")
        texts = Counter("repair prompt" if "unreadable content" in e[2] else
                        "error opening (OK)" if "error trying to" in e[2] else e[2][:60] for e in hits)
        rows.append({"chunk": c.name, "file": f.name, "word": verdict, "dialogs_naming_file": sum(texts.values()),
                     "what": "; ".join(f"{k} x{v}" for k, v in texts.items())})
    for e in evs:
        if id(e) not in named:
            unnamed[(c.name, e[1].split("]")[0] + "]", e[2][:70])] += 1

with open(root / "coverage.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader(); w.writerows(rows)

print(f"{len(rows)} files in {len(chunks)} chunks")
print("Word:", dict(Counter(r["word"].split(":")[0] for r in rows)))
print("captured a dialog naming the file:", sum(1 for r in rows if r["dialogs_naming_file"]),
      "| broken with none:", [r["file"] for r in rows if r["word"].startswith("broken") and not r["dialogs_naming_file"]])
print("dialogs naming no file:")
for (c, owner, text), n in sorted(unnamed.items()):
    print(f"  {c} {n:3} {owner} {text}")

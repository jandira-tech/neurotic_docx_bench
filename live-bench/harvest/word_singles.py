"""Open each file alone in Word (one word_pdf_focus batch per file), so a degraded Word cannot
poison the verdict of the files after it. Files are never modified: each is copied into its own
staging dir.

usage: word_singles.py <neurotic_docx_bench repo> <out_dir> <docx>...
writes <out_dir>/singles.csv (file, verdict, error) and PDFs to <out_dir>/pdf/; resumes on rerun.
"""

import csv
import re
import shutil
import subprocess
import sys
from pathlib import Path

repo, out = Path(sys.argv[1]), Path(sys.argv[2])
files = [Path(p) for p in sys.argv[3:]]
pdf_dir, stage_root = out / "pdf", out / "stage"
pdf_dir.mkdir(parents=True, exist_ok=True)
csv_path = out / "singles.csv"
done = {r["file"] for r in csv.DictReader(open(csv_path))} if csv_path.exists() else set()


def word_docs() -> int:
    r = subprocess.run(["osascript", "-e", 'tell application "Microsoft Word" to count of documents'],
                       capture_output=True, text=True)
    return int(r.stdout.strip() or 0) if r.returncode == 0 else 0


for i, f in enumerate(files, 1):
    if f.name in done:
        continue
    if word_docs():  # ghosts or a recovered doc left by the previous file: start from a fresh Word
        subprocess.run(["osascript", "-e", 'tell application "Microsoft Word" to quit saving no'],
                       capture_output=True)
        for _ in range(30):
            if subprocess.run(["pgrep", "-x", "Microsoft Word"], capture_output=True).returncode:
                break
            subprocess.run(["/bin/sleep", "1"])
        if word_docs():
            sys.exit(f"Word still holds documents before {f.name}; stopping")
    stage = stage_root / f.stem
    shutil.rmtree(stage, ignore_errors=True)
    stage.mkdir(parents=True)
    shutil.copy2(f, stage / f.name)
    proc = subprocess.run(
        ["uv", "run", "python", "scripts/word_pdf_focus.py", "--src", str(stage), "--out", str(pdf_dir),
         "--no-check-preset", "--timeout", "180", "--label", "single", "--log", str(out / "singles.log")],
        cwd=repo, capture_output=True, text=True)
    text = proc.stdout + proc.stderr
    (out / "stdout").mkdir(exist_ok=True)
    (out / "stdout" / f"{f.stem}.txt").write_text(text)
    if (pdf_dir / f"{f.stem}.pdf").exists():
        verdict, err = "opens_ok", ""
    else:
        m = re.search(rf"FAIL {re.escape(f.name)}:[ \t]*(.*?)(?=\n\s*FAIL |\Z)", text[text.rfind("│ failed"):], re.S)
        err = re.sub(r"\s+", " ", m.group(1)).strip() if m else f"no FAIL line (exit {proc.returncode})"
        verdict = "broken" if "loaded empty" in err else "failed_other"
    shutil.rmtree(stage, ignore_errors=True)
    new = not csv_path.exists()
    with open(csv_path, "a", newline="") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(["file", "verdict", "error"])
        w.writerow([f.name, verdict, err])
    print(f"[{i}/{len(files)}] {f.name}: {verdict} {err[:100]}", flush=True)

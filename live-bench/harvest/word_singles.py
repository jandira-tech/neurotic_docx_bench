"""Open each file alone in Word (one scripts/word_pdf.py batch per file), so a degraded Word cannot
poison the verdict of the files after it. Files are never modified: each is copied into its own
staging dir.

usage: word_singles.py <neurotic_docx_bench repo> <out_dir> <docx>...
writes <out_dir>/singles.csv (file, verdict, error) and PDFs to <out_dir>/pdf/; resumes on rerun.
The verdict is the file's last line in the driver's <out_dir>/pdf/manifest.jsonl.
"""

import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

BROKEN = ("repair prompt declined", "loaded empty")  # word_pdf.py's wording, then the 2026-10-13 focus driver's


def verdict(manifest: Path, name: str) -> tuple[str, str]:
    """(opens_ok | broken | failed_other | no_result, error) for ``name`` from word_pdf.py's manifest."""
    lines = [json.loads(s) for s in manifest.read_text().splitlines() if s.strip()] if manifest.exists() else []
    names = {name} | {r["converted_filename"] for r in lines
                      if r.get("status") == "renamed" and r.get("original_filename") == name}
    mine = [r for r in lines if r.get("original_filename") in names and r.get("status") != "renamed"]
    if not mine:
        return "no_result", f"no manifest line for {name}"
    last = mine[-1]
    if last.get("status") in ("ok", "skipped") and last.get("converted_filename"):
        return "opens_ok", ""
    err = last.get("error") or f"status {last.get('status')}"
    return ("broken" if any(b in err for b in BROKEN) else "failed_other"), err


def word_docs() -> int:
    r = subprocess.run(["osascript", "-e", 'tell application "Microsoft Word" to count of documents'],
                       capture_output=True, text=True)
    return int(r.stdout.strip() or 0) if r.returncode == 0 else 0


def main(argv: list[str]) -> None:
    repo, out = Path(argv[1]), Path(argv[2])
    files = [Path(p) for p in argv[3:]]
    pdf_dir, stage_root = out / "pdf", out / "stage"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out / "singles.csv"
    done = {r["file"] for r in csv.DictReader(open(csv_path))} if csv_path.exists() else set()

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
            ["uv", "run", "python", "scripts/word_pdf.py", "--src", str(stage), "--out", str(pdf_dir),
             "--no-check-preset", "--timeout", "180", "--label", "single", "--log", str(out / "singles.log")],
            cwd=repo, capture_output=True, text=True)
        (out / "stdout").mkdir(exist_ok=True)
        (out / "stdout" / f"{f.stem}.txt").write_text(proc.stdout + proc.stderr)
        result, err = verdict(pdf_dir / "manifest.jsonl", f.name)
        if result == "no_result":
            err = f"{err} (exit {proc.returncode})"
        shutil.rmtree(stage, ignore_errors=True)
        new = not csv_path.exists()
        with open(csv_path, "a", newline="") as fh:
            w = csv.writer(fh)
            if new:
                w.writerow(["file", "verdict", "error"])
            w.writerow([f.name, result, err])
        print(f"[{i}/{len(files)}] {f.name}: {result} {err[:100]}", flush=True)


if __name__ == "__main__":
    main(sys.argv)

"""Harvest broken DOCX from the live jubarte-live-bench D1, run after run.

  prepare: new bench_results since the watermark (wrangler, remote) -> candidates not seen before:
           fixtures whose own Word convert was not ok (or never ran), and tool redline docx whose
           redline_render failed (Word or soffice) -> download (sha256-checked) -> today's
           word-endpoint guard + purexml gate -> unsafe files deleted -> the rest copied to
           <run>/word_in/ for Word. Files are never modified.
  collect: Word's verdicts for <run> (word.stdout + word_rerun<N>.stdout, PDFs in word_pdf*/) ->
           broken files copied into really_broken/<fixtures|tool_redlines>/<category>/, rows
           appended to really_broken/manifest.csv, seen.csv updated, Word PDFs deleted.

usage: uv run --no-project --python 3.14 --with httpx python -I harvest.py prepare
       uv run --no-project --python 3.14 python -I harvest.py collect <run_dir>
"""

import csv
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

# The harvest work dir (runs/, seen.csv, watermark.txt) defaults to live-bench/.work next to
# this script; NDB_LIVE_WORK moves it. The 2026-10-13 work dir it migrated from was
# ~/temp/T/d1_jubarte_live_bench (see docs/PUBLISHING.md).
REPO = Path(__file__).resolve().parents[2]
WORK = Path(os.environ.get("NDB_LIVE_WORK", REPO / "live-bench" / ".work"))
SCRIPTS = Path(__file__).resolve().parent
H = WORK / "harvest"
OUT = REPO / "really_broken"
ENDPOINT = Path(os.environ.get("NDB_WORD_ENDPOINT", Path.home() / "T" / "word-endpoint"))
ARTIFACTS = "https://jubarte.pro/live/artifacts/"
FIRST_WATERMARK = "2026-10-13T02:37:42.600Z"  # last completed_at in the 2026-10-12 export
# the first-run bootstrap (before seen.csv exists) reads the pre-migration analysis;
# NDB_LIVE_WORK_LEGACY points at the old ~/temp/T/d1_jubarte_live_bench tree if it is gone
LEGACY = Path(os.environ.get("NDB_LIVE_WORK_LEGACY", Path.home() / "temp/T/d1_jubarte_live_bench"))
SEEN_COLS = ["sha256", "set", "verdict", "harvest_run"]
MANIFEST_COLS = ["set", "file", "category", "tool", "sha256", "artifact", "d1_failed_in", "local_word_error"]
REDLINE_COLS = ["key", "sha256", "size", "tool", "run", "sequence", "word_render", "word_code",
                "soffice_render", "soffice_error"]


def load_seen() -> dict[str, dict]:
    path = H / "seen.csv"
    if path.exists():
        return {r["sha256"]: r for r in csv.DictReader(open(path))}
    seen = {}  # first run: everything the 2026-10-12/13 work already opened or deleted
    for r in csv.DictReader(open(LEGACY / "problematic_fixtures/manifest.csv")):
        seen[r["sha256"]] = {"sha256": r["sha256"], "set": "fixture", "verdict": r["local_word"], "harvest_run": "initial"}
    for r in csv.DictReader(open(LEGACY / "analysis/tool_redline_failures.csv")):
        seen[r["sha256"]] = {"sha256": r["sha256"], "set": "tool_redline", "verdict": "initial", "harvest_run": "initial"}
    return seen


def save_seen(seen: dict[str, dict]) -> None:
    with open(H / "seen.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=SEEN_COLS)
        w.writeheader(); w.writerows(seen.values())


def d1(sql: str) -> list[dict]:
    for attempt in range(3):  # wrangler fails now and then with nothing on stderr; --json puts the error on stdout
        r = subprocess.run(["npx", "-y", "wrangler", "d1", "execute", "jubarte-live-bench", "--remote", "--json",
                            "--command", sql], cwd="/tmp", capture_output=True, text=True, timeout=300)
        if not r.returncode:
            return json.loads(r.stdout)[0]["results"]
        print(f"wrangler failed (attempt {attempt + 1}/3): {(r.stderr + r.stdout)[-800:]}", file=sys.stderr)
        time.sleep(10)
    sys.exit("wrangler failed 3 times")


def new_rows(watermark: str) -> list[dict]:
    rows = []
    while True:
        page = d1("select completed_at, payload from bench_results where completed_at > "
                  f"'{watermark}' order by completed_at limit 40")
        if not page:
            return rows
        rows += [json.loads(p["payload"]) | {"completed_at": p["completed_at"]} for p in page]
        watermark = page[-1]["completed_at"]


def candidates(rows: list[dict], seen: dict) -> tuple[list[dict], list[dict], set[str]]:
    fixtures, redlines, refused = {}, {}, set()
    for r in rows:
        src = r["source"]
        conv = next((s for s in r["stages"] if s["tool"] == "word" and s["operation"] == "convert"), None)
        if conv is None or conv["status"] != "ok":
            code = (m.group(1) if conv and (m := re.search(r'"code": "([a-z_]+)"', conv.get("error") or ""))
                    else (conv or {}).get("error", "never_sent")[:60])
            fixtures[src["sha256"]] = {"sha256": src["sha256"], "url": src["url"], "code": code}
        arts = {a["key"].rsplit("/", 1)[-1]: a for a in r.get("artifacts", [])}
        for s in r["stages"]:
            if s["operation"] != "redline_render" or s["status"] == "ok" or not s.get("target_tool"):
                continue
            a = arts.get(f"{s['target_tool']}-redline.docx")
            if not a:
                continue
            c = redlines.setdefault(a["sha256"], {k: "" for k in REDLINE_COLS} | {
                "key": a["key"], "sha256": a["sha256"], "size": a["size"], "tool": s["target_tool"],
                "run": r["run_id"][:8], "sequence": r["sequence"]})
            if s["tool"] == "word":
                c["word_render"] = s["status"]
                c["word_code"] = (m.group(1) if (m := re.search(r'"code": "([a-z_]+)"', s.get("error") or "")) else (s.get("error") or "")[:60])
            else:
                c["soffice_render"], c["soffice_error"] = s["status"], (s.get("error") or "")[:300]
    for sha in list(fixtures) + list(redlines):
        if sha in seen:
            refused.add(sha)
    return ([f for k, f in fixtures.items() if k not in seen], [c for k, c in redlines.items() if k not in seen], refused)


def write_csv(path: Path, rows: list[dict], cols: list[str]) -> None:
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader(); w.writerows(rows)


def gate(set_dir: Path, guard_csv: Path) -> list[str]:
    """purexml + guard gate; unsafe files are deleted (Arthur, 2026-10-13). Returns the deleted names."""
    subprocess.run(["uv", "run", "--no-project", "--python", "3.13", "--with", "purexml", "python", "-I",
                    str(SCRIPTS / "purexml_gate.py"), str(set_dir / "all"), str(set_dir), str(guard_csv)], check=True)
    deleted = []
    for p in sorted((set_dir / "unsafe_not_opened").glob("*.docx")):
        deleted.append(p.name)
        p.unlink()
        (set_dir / "all" / p.name).unlink(missing_ok=True)
    (set_dir / "deleted_unsafe.txt").write_text("".join(f"{n}\n" for n in deleted))
    return deleted


def prepare() -> None:
    H.mkdir(parents=True, exist_ok=True)
    seen = load_seen()
    wm_file = H / "watermark.txt"
    watermark = wm_file.read_text().strip() if wm_file.exists() else FIRST_WATERMARK
    rows = new_rows(watermark)
    print(f"D1: {len(rows)} new bench_results after {watermark}")
    if not rows:
        save_seen(seen)
        return
    fx, rl, again = candidates(rows, seen)
    run = H / datetime.now().strftime("%Y%m%d_%H%M%S")
    run.mkdir()
    with open(run / "rows.jsonl", "w") as fh:
        fh.writelines(json.dumps(r) + "\n" for r in rows)
    print(f"candidates: {len(fx)} fixtures, {len(rl)} tool redlines new; {len(again)} already seen")
    word_in = run / "word_in"
    word_in.mkdir()
    deleted = []
    if fx:
        d = run / "fixtures"; d.mkdir()
        write_csv(d / "candidates.csv", fx, ["sha256", "url", "code"])
        subprocess.run([sys.executable, "-I", str(SCRIPTS / "fetch_and_guard.py"), str(d / "candidates.csv"),
                        str(d / "all"), str(ENDPOINT), str(d / "guard.csv")], check=True)
        deleted += gate(d, d / "guard.csv")
    if rl:
        d = run / "redlines"; d.mkdir()
        write_csv(d / "candidates.csv", rl, REDLINE_COLS)
        subprocess.run([sys.executable, "-I", str(SCRIPTS / "fetch_tool_redlines.py"), str(d / "candidates.csv"),
                        str(d / "all"), str(ENDPOINT), str(d / "guard.csv")], check=True)
        deleted += gate(d, d / "guard.csv")
    for p in run.glob("*/word_input/*.docx"):
        shutil.copy2(p, word_in / p.name)
    for f in fx:
        seen[f["sha256"]] = {"sha256": f["sha256"], "set": "fixture", "verdict": "pending", "harvest_run": run.name}
    for c in rl:
        seen[c["sha256"]] = {"sha256": c["sha256"], "set": "tool_redline", "verdict": "pending", "harvest_run": run.name}
    save_seen(seen)
    wm_file.write_text(rows[-1]["completed_at"])
    print(f"deleted unsafe: {len(deleted)}; for Word: {len(list(word_in.glob('*.docx')))} in {word_in}")


def parse(stdout: Path) -> dict[str, str]:
    text = stdout.read_text(errors="replace")
    text = text[text.rfind("│ failed"):]
    return {m.group(1): re.sub(r"\s+", " ", m.group(2)).strip()
            for m in re.finditer(r"FAIL (\S+)\.docx:[ \t]*(.*?)(?=\n\s*FAIL |\Z)", text, re.S)}


def category(err: str) -> str:
    if "loaded empty" in err:
        return "repair_prompt"
    if "Connection is invalid" in err:
        return "crashes_word"
    return "unconfirmed"


def collect(run: Path) -> None:
    seen = load_seen()
    fails, pdfs = parse(run / "word.stdout"), {p.stem for p in (run / "word_pdf").glob("*.pdf")}
    for out in sorted(run.glob("word_rerun*.stdout"), key=lambda p: int(re.sub(r"\D", "", p.stem) or 0)):
        rp = {p.stem for p in (run / out.stem.replace("word_rerun", "word_pdf_rerun")).glob("*.pdf")}
        for s in rp:
            fails.pop(s, None)
        fails.update(parse(out))
        pdfs |= rp
    meta = {}
    if (run / "fixtures/candidates.csv").exists():
        for r in csv.DictReader(open(run / "fixtures/candidates.csv")):
            meta[r["sha256"]] = {"set": "fixtures", "tool": "", "sha256": r["sha256"], "artifact": r["url"], "d1_failed_in": r["code"]}
    if (run / "redlines/candidates.csv").exists():
        for r in csv.DictReader(open(run / "redlines/candidates.csv")):
            stem = f"{r['tool']}__{r['run']}_{int(r['sequence']):04d}"
            meta[stem] = {"set": "tool_redlines", "tool": r["tool"], "sha256": r["sha256"], "artifact": ARTIFACTS + r["key"],
                          "d1_failed_in": f"word:{r['word_code']}" if r["word_render"] else "soffice"}
    new_rows, tally = [], Counter()
    for p in sorted((run / "word_in").glob("*.docx")):
        m = meta[p.stem]
        if p.stem in pdfs and p.stem not in fails:
            verdict, err = "opens_ok", ""
        elif p.stem in fails:
            err = fails[p.stem]
            verdict = category(err)
        else:
            verdict, err = "no_result", ""
        tally[(m["set"], m["tool"], verdict)] += 1
        seen[m["sha256"]] = {"sha256": m["sha256"], "set": m["set"], "verdict": verdict, "harvest_run": run.name}
        if verdict in ("repair_prompt", "crashes_word", "unconfirmed"):
            dst = OUT / m["set"] / verdict
            dst.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dst / p.name)
            new_rows.append({"set": {"fixtures": "fixture", "tool_redlines": "tool_redline"}[m["set"]],"file": f"{m['set']}/{verdict}/{p.name}",
                             "category": verdict, "tool": m["tool"], "sha256": m["sha256"], "artifact": m["artifact"],
                             "d1_failed_in": m["d1_failed_in"], "local_word_error": f"{err} | harvest {run.name}"})
    for stem in meta:  # unsafe ones never reached word_in
        if not (run / "word_in" / f"{stem}.docx").exists():
            seen[meta[stem]["sha256"]].update(verdict="deleted_unsafe")
    if new_rows:
        manifest = OUT / "manifest.csv"
        with open(manifest, "a", newline="") as fh:
            csv.DictWriter(fh, fieldnames=MANIFEST_COLS).writerows(new_rows)
    save_seen(seen)
    for d in run.glob("word_pdf*"):
        shutil.rmtree(d)
    print(f"{run.name}: {len(new_rows)} broken added to {OUT}")
    for k, v in sorted(tally.items()):
        print(f"  {v:4} {k[0]:14} {k[1]:18} {k[2]}")
    if tally and any(k[2] == "no_result" for k in tally):
        print("no_result files remain: rerun them into word_rerun<N> before trusting this harvest")


if __name__ == "__main__":
    {"prepare": lambda: prepare(), "collect": lambda: collect(Path(sys.argv[2]))}[sys.argv[1]]()

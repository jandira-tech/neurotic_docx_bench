"""Download refused fixtures (sha256-checked) and re-run word_endpoint.guard on them.

usage: fetch_and_guard.py <word_rejected_fixtures.csv> <download_dir> <word-endpoint repo> <out.csv>
"""

import asyncio
import csv
import hashlib
import sys
import traceback
from pathlib import Path

import httpx

src_csv, dl, repo, out = map(Path, sys.argv[1:5])
dl.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(repo))
from word_endpoint import guard  # noqa: E402

rows = list(csv.DictReader(open(src_csv)))


async def fetch(client, sem, row):
    path = dl / f"{row['sha256']}.docx"
    if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]:
        return
    async with sem:
        for _ in range(3):
            try:
                r = await client.get(row["url"])
                r.raise_for_status()
                if hashlib.sha256(r.content).hexdigest() != row["sha256"]:
                    print("sha mismatch", row["url"], file=sys.stderr)
                    return
                path.write_bytes(r.content)
                return
            except httpx.HTTPError as exc:
                err = exc
        print("download failed", row["url"], err, file=sys.stderr)


async def main():
    sem = asyncio.Semaphore(16)
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        await asyncio.gather(*(fetch(client, sem, r) for r in rows))


asyncio.run(main())

results = []
for row in rows:
    path = dl / f"{row['sha256']}.docx"
    rec = {"sha256": row["sha256"], "d1_code": row["code"], "local_code": "", "reason": "",
           "part": "", "guard_line": ""}
    if not path.exists():
        rec["local_code"] = "not_downloaded"
    else:
        try:
            guard.prepare_docx(path.read_bytes())
            rec["local_code"] = "passes"
        except guard.GuardError as exc:
            rec.update(local_code=exc.code, reason=exc.reason, part=exc.part or "")
            frames = [f for f in traceback.extract_tb(exc.__traceback__) if f.filename.endswith("guard.py")]
            rec["guard_line"] = f"{frames[-1].name}:{frames[-1].lineno}" if frames else ""
            if exc.__cause__ is not None:
                rec["reason"] += f" ({type(exc.__cause__).__name__}: {str(exc.__cause__)[:80]})"
    results.append(rec)

with open(out, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(results[0]))
    w.writeheader(); w.writerows(results)
print("wrote", out, len(results))

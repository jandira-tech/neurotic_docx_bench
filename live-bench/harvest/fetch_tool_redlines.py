"""Download tool redline artifacts from the live site (sha256-checked) and run today's guard.

usage: fetch_tool_redlines.py <tool_redline_failures.csv> <dst_dir> <word-endpoint repo> <guard_out.csv>
Files are named <tool>__<run>_<seq>.docx; guard_out keys them by that stem in its `sha256` column
so purexml_gate.py can read it unchanged.
"""

import asyncio
import csv
import hashlib
import sys
import traceback
import urllib.parse
from pathlib import Path

import httpx

src, dst, repo, out = map(Path, sys.argv[1:5])
dst.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(repo))
from word_endpoint import guard  # noqa: E402

BASE = "https://jubarte.pro/live/artifacts/"
rows = list(csv.DictReader(open(src)))


def stem(r):
    return f"{r['tool']}__{r['run']}_{int(r['sequence']):04d}"


async def fetch(client, sem, r):
    path = dst / f"{stem(r)}.docx"
    if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == r["sha256"]:
        return
    url = BASE + "/".join(urllib.parse.quote(p) for p in r["key"].split("/"))
    async with sem:
        for _ in range(3):
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                if hashlib.sha256(resp.content).hexdigest() != r["sha256"]:
                    print("sha mismatch", url, file=sys.stderr)
                    return
                path.write_bytes(resp.content)
                return
            except httpx.HTTPError as exc:
                err = exc
        print("download failed", url, err, file=sys.stderr)


async def main():
    sem = asyncio.Semaphore(12)
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        await asyncio.gather(*(fetch(client, sem, r) for r in rows))


asyncio.run(main())

res = []
for r in rows:
    path = dst / f"{stem(r)}.docx"
    rec = {"sha256": stem(r), "local_code": "", "reason": "", "part": "", "guard_line": ""}
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
    res.append(rec)
with open(out, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(res[0]))
    w.writeheader(); w.writerows(res)
from collections import Counter
print(Counter(x["local_code"] for x in res))

"""Upload build/<prefix>/ to the public R2 bucket neurotic-docx-bench-pages, skipping keys already there.

    uv run --with httpx python upload_r2.py d2p redlines

Uses wrangler's own OAuth login (run `bunx wrangler whoami` first: it refreshes the token) against
the Cloudflare R2 object API. Objects are immutable (content-addressed by case/engine/page), so
they are served with a one-year cache.
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
import tomllib
from pathlib import Path

import httpx

H = Path(__file__).parent
BUILD = H / "build"
ACCOUNT = "5651b2fe85f9bbb0fc1b8f4ad2cb4e64"
BUCKET = "neurotic-docx-bench-pages"
API = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT}/r2/buckets/{BUCKET}/objects"
TYPES = {".webp": "image/webp", ".pdf": "application/pdf", ".json": "application/json"}


def token() -> str:
    cfgs = [Path.home() / d / "default.toml" for d in (".wrangler/config", "Library/Preferences/.wrangler/config")]
    cfg = max((c for c in cfgs if c.is_file()), key=lambda c: c.stat().st_mtime)  # the live login
    return tomllib.loads(cfg.read_text())["oauth_token"]


async def existing(client: httpx.AsyncClient, prefix: str) -> set[str]:
    keys, cursor = set(), None
    while True:
        params = {"prefix": prefix, "per_page": 1000, **({"cursor": cursor} if cursor else {})}
        r = (await client.get(API, params=params)).json()
        keys |= {o["key"] for o in r.get("result", [])}
        cursor = (r.get("result_info") or {}).get("cursor")
        if not (r.get("result_info") or {}).get("is_truncated"):
            return keys


async def main(prefixes: list[str]) -> None:
    files = [p for pre in prefixes for p in sorted((BUILD / pre).rglob("*")) if p.is_file() and p.suffix in TYPES]
    async with httpx.AsyncClient(headers={"Authorization": f"Bearer {token()}"}, timeout=120) as client:
        have = set()
        for pre in prefixes:
            have |= await existing(client, pre + "/")
        todo = [p for p in files if p.relative_to(BUILD).as_posix() not in have]
        print(f"{len(files)} files, {len(have)} already in R2, {len(todo)} to upload", flush=True)
        sem, failed, done, refresh_lock = asyncio.Semaphore(4), [], 0, asyncio.Lock()  # R2 API: 1200 requests / 300 s

        async def put(p: Path) -> None:
            nonlocal done
            key = p.relative_to(BUILD).as_posix()
            headers = {"Content-Type": TYPES[p.suffix], "Cache-Control": "public, max-age=31536000, immutable"}
            async with sem:
                for attempt in range(6):
                    try:
                        sent = client.headers["Authorization"]
                        r = await client.put(f"{API}/{key}", content=p.read_bytes(), headers=headers)
                        if r.status_code == 200:
                            await asyncio.sleep(0.9)  # stay under the rate limit
                            break
                        if r.status_code == 429:
                            await asyncio.sleep(60)
                            continue
                        if r.status_code in (401, 403):  # the OAuth token lives about an hour: refresh it
                            async with refresh_lock:
                                if client.headers["Authorization"] == sent:
                                    await asyncio.to_thread(subprocess.run, ["bunx", "wrangler", "whoami"], capture_output=True)
                                    client.headers["Authorization"] = f"Bearer {token()}"
                            continue
                    except httpx.HTTPError:
                        pass
                    await asyncio.sleep(2 ** attempt)
                else:
                    failed.append(key)
            done += 1
            if done % 1000 == 0:
                print(f"{done}/{len(todo)}", flush=True)

        await asyncio.gather(*(put(p) for p in todo))
    print(f"uploaded {len(todo) - len(failed)}, failed {len(failed)}", flush=True)
    for k in failed[:20]:
        print("FAILED", k)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))

"""Upload build/<prefix>/ through the throwaway Worker ndb-r2-upload-tmp (R2 binding, no API rate limit).

    uv run --with httpx python upload_worker.py redlines      # SECRET in /tmp/r2up/secret.txt
Keys already in the bucket are skipped (listed through the R2 API, as upload_r2.py does).
"""
import asyncio, sys
from pathlib import Path
import httpx
from upload_r2 import API, BUILD, TYPES, existing, token

WORKER = "https://ndb-r2-upload-tmp.cicero-im.workers.dev/"
SECRET = Path("/tmp/r2up/secret.txt").read_text().strip()


async def main(prefixes):
    async with httpx.AsyncClient(headers={"Authorization": f"Bearer {token()}"}, timeout=120) as api:
        have = set()
        for pre in prefixes:
            have |= await existing(api, pre + "/")
    files = [p for pre in prefixes for p in sorted((BUILD / pre).rglob("*")) if p.is_file() and p.suffix in TYPES]
    todo = [p for p in files if p.relative_to(BUILD).as_posix() not in have]
    print(f"{len(files)} files, {len(have)} already in R2, {len(todo)} to upload", flush=True)
    sem, failed, done = asyncio.Semaphore(32), [], 0
    async with httpx.AsyncClient(timeout=120, http2=False) as client:
        async def put(p):
            nonlocal done
            key = p.relative_to(BUILD).as_posix()
            async with sem:
                for attempt in range(5):
                    try:
                        r = await client.put(WORKER + key, content=p.read_bytes(),
                                             headers={"x-secret": SECRET, "content-type": TYPES[p.suffix]})
                        if r.status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    await asyncio.sleep(2 ** attempt)
                else:
                    failed.append(key)
            done += 1
            if done % 2000 == 0:
                print(f"{done}/{len(todo)}", flush=True)
        await asyncio.gather(*(put(p) for p in todo))
    print(f"uploaded {len(todo) - len(failed)}, failed {len(failed)}", flush=True)
    for k in failed[:20]:
        print("FAILED", k)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))

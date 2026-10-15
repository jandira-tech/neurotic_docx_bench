"""Upload review fixtures to the public R2 bucket `neurotic-docx-bench-pages`.

    uv run --with httpx python scripts/publish/upload_r2.py <local_dir> <r2_prefix> [options]

Examples:
    # publish the wordcraft 400+400 cohort (see docs/PUBLISHING.md)
    uv run --with httpx python scripts/publish/upload_r2.py \
        results/wordcraft_20261014_fresh/compare/oracle wordcraft-20261014/compare/oracle

    # fast path for thousands of files: through the upload Worker (no API rate limit)
    uv run --with httpx python scripts/publish/upload_r2.py <dir> <prefix> \
        --via-worker https://ndb-r2-upload.<account>.workers.dev --secret-file ~/.ndb/upload-secret

    # check an upload: every local file on the bucket with the same byte size
    uv run --with httpx python scripts/publish/upload_r2.py <dir> <prefix> --verify

Auth is wrangler's own OAuth login (`bunx wrangler whoami` refreshes the token; run
`bunx wrangler login` once). Objects are content-addressed and immutable: uploads go
out with a one-year cache header and the Worker path refuses to overwrite an existing
key. Files already in the bucket (by key) are skipped.

Content types: .webp .pdf .json .docx .csv .md .txt .png .svg .html
"""

from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
import tomllib
from pathlib import Path

import httpx

ACCOUNT = "5651b2fe85f9bbb0fc1b8f4ad2cb4e64"
BUCKET = "neurotic-docx-bench-pages"
API = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT}/r2/buckets/{BUCKET}/objects"
TYPES = {
    ".webp": "image/webp",
    ".pdf": "application/pdf",
    ".json": "application/json",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".csv": "text/csv",
    ".md": "text/markdown; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".html": "text/html; charset=utf-8",
}
R2_DEV = "https://pub-92c80eda1059428394970066c8500eda.r2.dev/"  # the bucket's public URL


def token() -> str:
    cfgs = [Path.home() / d / "default.toml" for d in (".wrangler/config", "Library/Preferences/.wrangler/config")]
    cfg = max((c for c in cfgs if c.is_file()), key=lambda c: c.stat().st_mtime)  # the live login
    return tomllib.loads(cfg.read_text())["oauth_token"]


def local_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in TYPES and p.name != ".DS_Store")


async def listing(client: httpx.AsyncClient, prefix: str) -> dict[str, int]:
    """{key: size_bytes} for every object under prefix."""
    out: dict[str, int] = {}
    cursor = None
    while True:
        params = {"prefix": prefix, "per_page": 1000, **({"cursor": cursor} if cursor else {})}
        r = (await client.get(API, params=params)).json()
        for o in r.get("result", []):
            out[o["key"]] = o["size"]
        cursor = (r.get("result_info") or {}).get("cursor")
        if not (r.get("result_info") or {}).get("is_truncated"):
            return out


async def upload_api(client: httpx.AsyncClient, key: str, path: Path, sem: asyncio.Semaphore,
                     failed: list, refresh_lock: asyncio.Lock) -> None:
    headers = {
        "Content-Type": TYPES[path.suffix.lower()],
        "Cache-Control": "public, max-age=31536000, immutable",
    }
    async with sem:
        for attempt in range(6):
            try:
                sent = client.headers["Authorization"]
                r = await client.put(f"{API}/{key}", content=path.read_bytes(), headers=headers)
                if r.status_code == 200:
                    await asyncio.sleep(0.9)  # R2 API: 1200 requests / 300 s
                    return
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
            await asyncio.sleep(2**attempt)
        failed.append(key)


async def upload_worker(client: httpx.AsyncClient, worker: str, secret: str, key: str, path: Path,
                        sem: asyncio.Semaphore, failed: list) -> None:
    async with sem:
        for attempt in range(5):
            try:
                r = await client.put(
                    worker.rstrip("/") + "/" + key,
                    content=path.read_bytes(),
                    headers={"x-secret": secret, "content-type": TYPES[path.suffix.lower()]},
                )
                if r.status_code == 200:
                    return
                if r.status_code == 412:  # key exists (the Worker writes non-overwriting)
                    return
            except httpx.HTTPError:
                pass
            await asyncio.sleep(2**attempt)
        failed.append(key)


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir", help="local directory whose files are uploaded")
    ap.add_argument("prefix", help="R2 key prefix (uploaded keys are <prefix>/<relative path>)")
    ap.add_argument("--via-worker", metavar="URL", help="upload through the R2 upload Worker (fast, no rate limit)")
    ap.add_argument("--secret-file", type=Path, default=Path.home() / ".ndb" / "upload-secret",
                    help="file holding the Worker's x-secret (default: ~/.ndb/upload-secret)")
    ap.add_argument("--concurrency", type=int, default=None, help="worker path: parallel uploads (default 32)")
    ap.add_argument("--verify", action="store_true", help="only compare local files with the bucket (keys + sizes)")
    ap.add_argument("--dry-run", action="store_true", help="list what would be uploaded and exit")
    args = ap.parse_args()

    root = Path(args.dir)
    if not root.is_dir():
        sys.exit(f"not a directory: {root}")
    files = local_files(root)
    keys = {p: f"{args.prefix.rstrip('/')}/{p.relative_to(root).as_posix()}" for p in files}
    print(f"{len(files)} eligible files under {root} -> {BUCKET}/{args.prefix.rstrip('/')}/")
    print(f"public base once uploaded: {R2_DEV}{args.prefix.rstrip('/')}/")

    async with httpx.AsyncClient(headers={"Authorization": f"Bearer {token()}"}, timeout=120) as api:
        have = await listing(api, args.prefix.rstrip("/") + "/")
    todo = [p for p in files if keys[p] not in have]
    print(f"{len(have)} already in R2, {len(todo)} to upload")

    if args.dry_run:
        for p in todo[:20]:
            print(" ", keys[p])
        return 0
    if args.verify:
        missing = [keys[p] for p in files if keys[p] not in have]
        wrong = [(keys[p], p.stat().st_size, have[keys[p]]) for p in files if keys[p] in have
                 and p.stat().st_size != have[keys[p]]]
        print(f"verify: {len(files) - len(missing) - len(wrong)}/{len(files)} ok "
              f"({len(missing)} missing, {len(wrong)} size mismatch)")
        for k in missing[:20]:
            print("  MISSING", k)
        for k, local, remote in wrong[:20]:
            print(f"  SIZE {k}: local {local} remote {remote}")
        return 1 if (missing or wrong) else 0

    if not todo:
        return 0
    failed: list[str] = []
    if args.via_worker:
        secret = args.secret_file.read_text().strip()
        sem = asyncio.Semaphore(args.concurrency or 32)
        done = 0
        async with httpx.AsyncClient(timeout=120) as client:

            async def one(p: Path) -> None:
                nonlocal done
                await upload_worker(client, args.via_worker, secret, keys[p], p, sem, failed)
                done += 1
                if done % 500 == 0:
                    print(f"{done}/{len(todo)}", flush=True)

            await asyncio.gather(*(one(p) for p in todo))
    else:
        sem = asyncio.Semaphore(4)
        refresh_lock = asyncio.Lock()
        done = 0
        async with httpx.AsyncClient(headers={"Authorization": f"Bearer {token()}"}, timeout=120) as client:

            async def one(p: Path) -> None:
                nonlocal done
                await upload_api(client, keys[p], p, sem, failed, refresh_lock)
                done += 1
                if done % 500 == 0:
                    print(f"{done}/{len(todo)}", flush=True)

            await asyncio.gather(*(one(p) for p in todo))

    print(f"uploaded {len(todo) - len(failed)}, failed {len(failed)}")
    for k in failed[:20]:
        print("FAILED", k)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

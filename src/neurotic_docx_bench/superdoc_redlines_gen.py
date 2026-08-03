"""Generate tracked-change redlines via yuch85/superdoc-redlines (SuperDoc headless CLI).

https://github.com/yuch85/superdoc-redlines (Apache-2.0) is a Node CLI that applies
block-ID-based edits to a DOCX with track changes through SuperDoc's headless editor,
word-diffing each replaced block for minimal markup. It has no base+next→redline
compare command, so this adapter supplies the mechanical comparison and lets the tool
do everything DOCX-facing:

1. ``extract`` block IR (seqId + text) from base and next DOCX (cached per doc).
2. Align base↔next block-text sequences (``difflib.SequenceMatcher``) into the tool's
   edit ops: ``replace`` (word-diffed by the tool), ``delete``, ``insert``.
3. ``apply`` the edits to the base DOCX with track changes on → redline DOCX.

Formatting/structure fidelity beyond what SuperDoc's editor round-trips is out of
scope for the adapter — scores measure the yuch85 pipeline, not the alignment (which
is deliberately minimal and deterministic).

Usage:
  uv run python -m neurotic_docx_bench.superdoc_redlines_gen --out $RUN_DIR/docx \
    --tool superdoc-redlines [--repo superdoc-redlines] [--jobs 6] [--limit N]
"""

from __future__ import annotations

import argparse
import difflib
import json
import shutil
import subprocess
import tempfile
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .redlines_gen import Pair, output_name, parse_manifest

_BLOCK_TYPES = {"paragraph", "heading", "listItem"}


def _run_cli(repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    cmd = ["node", str(Path(repo) / "superdoc-redline.mjs"), *args]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def extract_blocks(docx_path: Path, ir_path: Path, *, repo: Path) -> list[dict]:
    """``extract`` → block list (seqId, text, type). Raises on CLI failure."""
    r = _run_cli(repo, ["extract", "-i", str(docx_path), "-o", str(ir_path)])
    if r.returncode != 0 or not ir_path.is_file():
        err = (r.stderr or r.stdout or "").strip() or "no output"
        raise RuntimeError(f"superdoc-redlines extract failed: {err[:500]}")
    data = json.loads(ir_path.read_text())
    return [b for b in data.get("blocks") or [] if b.get("seqId")]


def build_edits(base_blocks: list[dict], next_blocks: list[dict], *, author: str) -> dict:
    """Minimal deterministic block alignment → superdoc-redlines edit payload."""
    if not base_blocks and next_blocks:
        raise ValueError(
            "base document has no addressable blocks — nothing to anchor insert edits to",
        )
    base_texts = [b.get("text") or "" for b in base_blocks]
    next_texts = [b.get("text") or "" for b in next_blocks]
    sm = difflib.SequenceMatcher(a=base_texts, b=next_texts, autojunk=False)
    edits: list[dict] = []

    def insert_op(next_block: dict, anchor: str) -> dict:
        btype = next_block.get("type")
        return {
            "afterBlockId": anchor,
            "operation": "insert",
            "text": next_block.get("text") or "",
            "type": btype if btype in _BLOCK_TYPES else "paragraph",
        }

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        if tag == "replace":
            paired = min(i2 - i1, j2 - j1)
            for k in range(paired):
                edits.append({
                    "blockId": base_blocks[i1 + k]["seqId"],
                    "operation": "replace",
                    "newText": next_texts[j1 + k],
                })
            for k in range(i1 + paired, i2):
                edits.append({"blockId": base_blocks[k]["seqId"], "operation": "delete"})
            anchor = base_blocks[i1 + paired - 1]["seqId"] if paired else (
                base_blocks[i1 - 1]["seqId"] if i1 else base_blocks[0]["seqId"]
            )
            for k in range(j1 + paired, j2):
                edits.append(insert_op(next_blocks[k], anchor))
        elif tag == "delete":
            for k in range(i1, i2):
                edits.append({"blockId": base_blocks[k]["seqId"], "operation": "delete"})
        elif tag == "insert":
            # No "insert before first block" op exists; anchoring a leading insert on
            # b001 puts it one block late — acceptable for this text-level adapter.
            anchor = base_blocks[i1 - 1]["seqId"] if i1 else base_blocks[0]["seqId"]
            for k in range(j1, j2):
                edits.append(insert_op(next_blocks[k], anchor))
    return {
        "version": "0.3.0",
        "author": {"name": author, "email": f"{author}@bench.invalid"},
        "edits": edits,
    }


def apply_edits(
    base_path: Path, edits_path: Path, out_path: Path, *, repo: Path, author: str,
) -> None:
    r = _run_cli(repo, [
        "apply",
        "-i", str(base_path),
        "-o", str(out_path),
        "-e", str(edits_path),
        "--author-name", author,
        "--quiet-warnings",
        "--allow-reduction",
        "--skip-invalid",
    ])
    if r.returncode != 0:
        # SuperDoc's apply session may not resolve every extract-time seqId
        # (e.g. AlternateContent / anchored images shift block counts). The CLI
        # still writes its best-effort partial redline — that IS the tool's
        # output; keep it when it is a readable DOCX and only fail otherwise.
        if out_path.is_file() and zipfile.is_zipfile(out_path):
            return
        err = (r.stderr or r.stdout or "").strip() or "no output"
        raise RuntimeError(f"superdoc-redlines apply failed: {err[:500]}")
    if not out_path.is_file():
        raise RuntimeError("superdoc-redlines apply wrote no output")


def generate_one(
    base_path: Path,
    next_path: Path,
    out_path: Path,
    *,
    repo: Path,
    author: str,
    workdir: Path,
    base_blocks: list[dict] | None = None,
    next_blocks: list[dict] | None = None,
) -> None:
    """base.docx + next.docx → tracked-change redline DOCX via the yuch85 CLI."""
    workdir.mkdir(parents=True, exist_ok=True)
    if base_blocks is None:
        base_blocks = extract_blocks(base_path, workdir / "base-ir.json", repo=repo)
    if next_blocks is None:
        next_blocks = extract_blocks(next_path, workdir / "next-ir.json", repo=repo)
    payload = build_edits(base_blocks, next_blocks, author=author)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not payload["edits"]:  # no textual difference → identity (mirrors jubarte-native)
        shutil.copyfile(base_path, out_path)
        return
    edits_path = workdir / "edits.json"
    edits_path.write_text(json.dumps(payload))
    apply_edits(base_path, edits_path, out_path, repo=repo, author=author)


def run_batch(
    *,
    out: Path,
    manifest: Path,
    source_dir: Path,
    statuses: set[str],
    limit: int | None,
    tool: str,
    author: str,
    force: bool,
    repo: Path,
    jobs: int,
) -> tuple[int, list[dict], dict[str, int]]:
    out.mkdir(parents=True, exist_ok=True)
    pairs = parse_manifest(manifest, statuses)
    if limit:
        pairs = pairs[:limit]

    tmp_root = Path(tempfile.mkdtemp(prefix="sdr-"))
    ir_cache: dict[str, list[dict] | Exception] = {}

    def _extract(stem: str) -> None:
        try:
            ir_cache[stem] = extract_blocks(
                source_dir / f"{stem}.docx", tmp_root / f"{stem}-ir.json", repo=repo,
            )
        except Exception as exc:  # recorded per-pair below
            ir_cache[stem] = exc

    stems = sorted({s for p in pairs for s in (p.base, p.next)
                    if (source_dir / f"{s}.docx").is_file()})
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        list(pool.map(_extract, stems))

    ok = 0
    failed: list[dict] = []
    timings: dict[str, int] = {}

    def _one(pair: Pair) -> None:
        nonlocal ok
        doc = f"{pair.base}_{pair.next}"
        name = output_name(pair, tool)
        out_path = out / name
        if not force and out_path.exists():
            ok += 1
            return
        base_path = source_dir / f"{pair.base}.docx"
        next_path = source_dir / f"{pair.next}.docx"
        if not base_path.exists() or not next_path.exists():
            failed.append({"doc": doc, "stage": "missing_source", "error": "source docx not found"})
            return
        base_blocks = ir_cache.get(pair.base)
        next_blocks = ir_cache.get(pair.next)
        for stem, blocks in ((pair.base, base_blocks), (pair.next, next_blocks)):
            if isinstance(blocks, Exception):
                failed.append({"doc": doc, "stage": "generate", "error": f"extract({stem}): {blocks}"})
                return
        try:
            t0 = time.perf_counter_ns()
            generate_one(
                base_path, next_path, out_path,
                repo=repo, author=author, workdir=tmp_root / doc,
                base_blocks=base_blocks, next_blocks=next_blocks,
            )
            timings[name.replace(".docx", "")] = time.perf_counter_ns() - t0
            ok += 1
        except Exception as exc:  # one bad pair must not stop the batch
            failed.append({"doc": doc, "stage": "generate", "error": str(exc)})

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        list(pool.map(_one, pairs))
    shutil.rmtree(tmp_root, ignore_errors=True)
    return ok, failed, timings


def main(argv: list[str] | None = None) -> int:
    import os

    p = argparse.ArgumentParser(
        description="yuch85/superdoc-redlines DOCX redline generator (SuperDoc headless CLI)",
    )
    default_out = (
        os.path.join(os.environ["RUN_DIR"], "docx") if os.environ.get("RUN_DIR") else "out/docx"
    )
    p.add_argument("--out", default=default_out)
    p.add_argument("--manifest", default="corpus/word_based/centralized_mapping.csv")
    p.add_argument("--source-dir", default="corpus/word_based/docx_source")
    p.add_argument("--status", default="ok")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--tool", default="superdoc-redlines")
    p.add_argument("--author", default="superdoc-redlines")
    p.add_argument("--repo", default="superdoc-redlines",
                   help="path to the yuch85/superdoc-redlines clone (npm-installed)")
    p.add_argument("--jobs", type=int, default=12)
    p.add_argument("--force", action="store_true")
    args = p.parse_args(argv)

    repo = Path(args.repo)
    if not (repo / "superdoc-redline.mjs").is_file():
        print(f"[superdoc-redlines] clone not found at {repo} — "
              "git clone https://github.com/yuch85/superdoc-redlines && npm install")
        return 1

    ok, failed, timings = run_batch(
        out=Path(args.out),
        manifest=Path(args.manifest),
        source_dir=Path(args.source_dir),
        statuses=set(args.status.split(",")) if args.status else set(),
        limit=args.limit,
        tool=args.tool,
        author=args.author,
        force=args.force,
        repo=repo,
        jobs=args.jobs,
    )
    out_dir = Path(args.out)
    (out_dir.parent / "generate_failures.json").write_text(json.dumps(failed, indent=2))
    (out_dir.parent / "generate_timings.json").write_text(json.dumps(timings))
    print(f"[superdoc-redlines] wrote {ok} redline(s) → {args.out}")
    if failed:
        print(f"[superdoc-redlines] {len(failed)} pair(s) skipped:")
        for f in failed[:10]:
            print(f"  {f['doc']} [{f['stage']}]: {f['error']}")
    return 0 if ok > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

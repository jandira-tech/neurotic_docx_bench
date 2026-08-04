"""Word-validity batch with dialog cleanup between failures.

Same per-file semantics as `bench word-validate` (render.word.validate_one: open in
Microsoft Word via AppleScript; a repair/warning dialog blocks `open` and counts as
invalid), plus what the CLI loop lacks for large batches: after any failure, Word is
force-quit so a stuck modal cannot cascade false failures onto later files.

Usage:
  uv run python scripts/word_validate_batch.py <docx-dir> --tool NAME --out results.jsonl \
    [--timeout 25] [--limit N]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

from neurotic_docx_bench.render.word import validate_one, word_available


def _kill_word() -> None:
    subprocess.run(["pkill", "-x", "Microsoft Word"], capture_output=True)
    time.sleep(2.0)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("docx_dir")
    ap.add_argument("--tool", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--timeout", type=float, default=25.0)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    if not word_available():
        print("needs macOS + Microsoft Word")
        return 2
    docs = sorted(Path(args.docx_dir).glob("*.docx"))
    if args.limit:
        docs = docs[: args.limit]
    if not docs:
        print(f"no .docx in {args.docx_dir}")
        return 2

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    n_ok = 0
    t_start = time.perf_counter()
    with out.open("w") as fh:
        for i, docx in enumerate(docs, 1):
            t0 = time.perf_counter()
            res = validate_one(docx, timeout=args.timeout)
            ms = round((time.perf_counter() - t0) * 1000, 1)
            row = {
                "tool": args.tool,
                "doc": docx.stem,
                "word_valid": res.ok,
                "validate_ms": ms,
            }
            if not res.ok:
                row["error"] = res.error
                _kill_word()  # clear any stuck dialog before the next file
            else:
                n_ok += 1
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            if i % 25 == 0:
                print(f"  {i}/{len(docs)} ({n_ok} valid)", flush=True)
    _kill_word()
    wall = time.perf_counter() - t_start
    print(
        f"{args.tool}: {n_ok}/{len(docs)} Word-valid "
        f"({len(docs) - n_ok} invalid) in {wall:.0f}s → {out}",
    )
    return 0 if n_ok == len(docs) else 1


if __name__ == "__main__":
    raise SystemExit(main())

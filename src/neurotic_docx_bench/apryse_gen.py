"""Apryse (apryse-sdk) as a DOCX→PDF converter and a DOCX redline generator (#100).

Entry points (``python -m neurotic_docx_bench.apryse_gen …``):

- ``convert SRC DEST`` — ``Convert.OfficeToPDF`` with tracked changes and comments
  displayed (Word's Save-as-PDF markup, the oracle of the docx_to_pdf track). This is
  what ``bench docx-to-pdf --tool apryse`` runs, through ``utils/apryse/apryse-convert``.
- ``compare BASE NEXT OUT`` — ``DOCXCompare.Compare``: BASE with NEXT's edits as
  ``w:ins``/``w:del``. Prints ``{"seconds": …}`` (the compare call alone, no start-up).
- ``batch --manifest M --source-dir S --out DIR`` — the redline generator: one
  ``compare`` child per pair, each under a timeout (a native call cannot be cancelled
  in-process), ``<key>_<tool>.docx`` names, ``generate_failures.json`` and
  ``generate_timings.json`` beside ``DIR``. Exit 1 only when nothing was written.

The key is ``APRYSE_API_KEY`` from the environment, else the repo's ``.env``. A demo key
(``demo:…``) makes Apryse stamp its logo on every page; ``version()`` says so, because
every score made with it carries that stamp.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from importlib import metadata
from pathlib import Path

from neurotic_docx_bench.superdoc_gen import output_names, parse_manifest

REPO_ROOT = Path(__file__).resolve().parents[2]
DOTENV = REPO_ROOT / ".env"
PAIR_TIMEOUT_S = 180.0


def api_key(dotenv: Path | None = None) -> str | None:
    """``APRYSE_API_KEY`` from the environment, else from ``dotenv`` (the repo's ``.env``)."""
    key = os.environ.get("APRYSE_API_KEY")
    if key:
        return key
    path = dotenv or DOTENV
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        name, sep, value = line.strip().removeprefix("export ").partition("=")
        if sep and name.strip() == "APRYSE_API_KEY":
            return value.strip().strip("'\"") or None
    return None


def is_demo() -> bool:
    return (api_key() or "").lower().startswith("demo:")


def version() -> str:
    """``apryse-sdk X (PDFNet Y[, demo key: output watermarked])``."""
    from apryse_sdk import PDFNet

    sdk = metadata.version("apryse-sdk")
    label = f"apryse-sdk {sdk} (PDFNet {PDFNet.GetVersionString()}"
    if is_demo():
        label += ", demo key: output watermarked"
    return label + ")"


def _init() -> None:
    from apryse_sdk import PDFNet

    key = api_key()
    if not key:
        raise SystemExit("APRYSE_API_KEY is not set (environment or .env)")
    PDFNet.Initialize(key)


def convert(src: Path, dest: Path) -> float:
    """DOCX → PDF with markup and comments shown. Returns the conversion's seconds."""
    import apryse_sdk as a

    opts = a.OfficeToPDFOptions()
    opts.SetDisplayChangeTracking(True)
    opts.SetDisplayComments(True)
    t0 = time.perf_counter()
    doc = a.PDFDoc()
    a.Convert.OfficeToPDF(doc, str(src), opts)
    if doc.GetPageCount() < 1:
        raise RuntimeError("Apryse produced a PDF with no pages")
    tmp = dest.with_name(dest.name + ".part")
    doc.Save(str(tmp), a.SDFDoc.e_linearized)
    doc.Close()
    tmp.replace(dest)
    return time.perf_counter() - t0


def compare(base: Path, nxt: Path, out: Path) -> float:
    """BASE + NEXT → OUT with NEXT's edits tracked. Returns the compare's seconds."""
    import apryse_sdk as a

    tmp = out.with_name(out.name + ".part.docx")
    t0 = time.perf_counter()
    a.DOCXCompare.Compare(str(base), str(nxt), str(tmp), a.DOCXCompareOptions())
    seconds = time.perf_counter() - t0
    if not tmp.is_file() or tmp.stat().st_size == 0:
        raise RuntimeError("Apryse wrote no redline")
    tmp.replace(out)
    return seconds


def _run_child(cmd: list[str], timeout_s: float) -> str:
    """Run ``cmd``; return its stdout. Raise TimeoutError past ``timeout_s`` (the child
    is killed), RuntimeError with its stderr tail on a non-zero exit."""
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s, check=False)
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError(f"timeout after {timeout_s:g}s") from exc
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout).strip().splitlines()[-3:]
        raise RuntimeError(f"exit {proc.returncode}: {' | '.join(tail)}")
    return proc.stdout


def _compare_in_child(base: Path, nxt: Path, out: Path, timeout_s: float) -> float:
    cmd = [sys.executable, "-m", "neurotic_docx_bench.apryse_gen", "compare", str(base), str(nxt), str(out)]
    stdout = _run_child(cmd, timeout_s)
    for line in reversed(stdout.strip().splitlines()):
        if line.startswith("{"):
            return float(json.loads(line)["seconds"])
    raise RuntimeError(f"compare child printed no timing: {stdout[-200:]!r}")


def batch(
    *, manifest: Path, source_dir: Path, out: Path, tool: str, jobs: int, timeout_s: float, force: bool,
    limit: int | None,
) -> tuple[int, list[dict], dict[str, int]]:
    out.mkdir(parents=True, exist_ok=True)
    pairs = parse_manifest(manifest, set())
    if limit:
        pairs = pairs[:limit]
    failed: list[dict] = []
    timings: dict[str, int] = {}
    ok = 0

    def one(pair):  # -> (doc, name, seconds | None, failure | None)
        doc = pair.key or f"{pair.base}_{pair.next}"
        name = output_names(pair, tool)[0]
        dest = out / name
        if not force and dest.is_file():
            return doc, name, None, None
        base, nxt = source_dir / f"{pair.base}.docx", source_dir / f"{pair.next}.docx"
        if not base.is_file() or not nxt.is_file():
            return doc, name, None, {"doc": doc, "stage": "missing_source", "error": "source docx not found"}
        try:
            return doc, name, _compare_in_child(base, nxt, dest, timeout_s), None
        except Exception as exc:  # one bad pair must not stop the batch
            return doc, name, None, {"doc": doc, "stage": "generate", "error": str(exc)}

    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        for doc, name, seconds, failure in pool.map(one, pairs):
            if failure:
                failed.append(failure)
                continue
            ok += 1
            if seconds is not None:
                timings[name.removesuffix(".docx")] = int(seconds * 1e9)
    return ok, failed, timings


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Apryse DOCX→PDF converter and redline generator")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("convert")
    c.add_argument("src", type=Path)
    c.add_argument("dest", type=Path)
    r = sub.add_parser("compare")
    r.add_argument("base", type=Path)
    r.add_argument("next", type=Path)
    r.add_argument("out", type=Path)
    sub.add_parser("version")
    b = sub.add_parser("batch")
    b.add_argument("--manifest", type=Path, required=True)
    b.add_argument("--source-dir", type=Path, required=True)
    b.add_argument("--out", type=Path, required=True)
    b.add_argument("--tool", default="apryse")
    b.add_argument("--jobs", type=int, default=8)
    b.add_argument("--timeout", type=float, default=PAIR_TIMEOUT_S)
    b.add_argument("--limit", type=int, default=None)
    b.add_argument("--force", action="store_true")
    args = p.parse_args(argv)

    if args.cmd == "version":
        print(version())
        return 0
    if args.cmd == "convert":
        _init()
        args.dest.unlink(missing_ok=True)
        print(json.dumps({"seconds": convert(args.src, args.dest)}))
        return 0
    if args.cmd == "compare":
        _init()
        print(json.dumps({"seconds": compare(args.base, args.next, args.out)}))
        return 0

    ok, failed, timings = batch(
        manifest=args.manifest, source_dir=args.source_dir, out=args.out, tool=args.tool,
        jobs=args.jobs, timeout_s=args.timeout, force=args.force, limit=args.limit,
    )
    (args.out.parent / "generate_failures.json").write_text(json.dumps(failed, indent=2))
    (args.out.parent / "generate_timings.json").write_text(json.dumps(timings))
    print(f"[apryse] wrote {ok} redline(s) → {args.out}; {len(failed)} failed")
    for f in failed[:10]:
        print(f"  {f['doc']} [{f['stage']}]: {f['error']}")
    return 0 if ok > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

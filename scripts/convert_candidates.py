"""Convert every corpus/word fixture with docxide-pdf or LibreOffice, resumable.

Writes ``<out>/candidate/<state>__<stem>.pdf`` (the stems the scorers match to Word's PDFs).
An existing real PDF is kept, so a rerun converts only what is missing.

    uv run python scripts/convert_candidates.py --engine docxide --out results/docxide_0.17.1_work
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from neurotic_docx_bench import cli
from neurotic_docx_bench import docx_to_pdf as d2p
from neurotic_docx_bench.render import soffice as so


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--engine", choices=("docxide", "soffice"), required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--files-list", type=Path,
                    help="a text file of corpus docx paths (one per line): convert only the "
                         "listed fixtures that lack a render, not every fixture")
    args = ap.parse_args()
    record_path = args.out / "convert_seconds.json"
    previous = json.loads(record_path.read_text()) if record_path.is_file() else {}
    if previous.get("engine") is not None and previous["engine"] != args.engine:
        raise SystemExit(f"conversion record uses engine {previous['engine']}, requested {args.engine}")
    fixtures = cli._corpus_word_selection(
        origin="all", files_list=[], score_only=False, locations=[], config=Path("bench.yaml"), tool=None
    ).fixtures
    if args.files_list:
        wanted = set()
        for line in args.files_list.read_text().splitlines():
            rel = Path(line.strip())
            parts = rel.parts[-3:]
            if len(parts) == 3 and parts[1] == "docx":
                wanted.add(f"{parts[0]}__{parts[2].removesuffix('.docx')}")
        fixtures = [f for f in fixtures if f.stem in wanted]
        unknown = wanted - {f.stem for f in fixtures}
        if unknown:
            print(f"WARNING: {len(unknown)} listed fixtures are not in the corpus selection", flush=True)
    cand = args.out / "candidate"
    cand.mkdir(parents=True, exist_ok=True)
    # A kept render must open in MuPDF too, the check every fresh conversion passes (#90).
    todo = [f for f in fixtures if not d2p._is_pdf(p := cand / f"{f.stem}.pdf") or d2p._unreadable_pdf(p) is not None]
    print(f"{len(fixtures)} fixtures, {len(todo)} to convert with {args.engine}", flush=True)
    soffice = so.find_soffice() if args.engine == "soffice" else None
    binary = d2p.resolve_tool_binary("docxide-pdf") if args.engine == "docxide" else None

    seconds: dict[str, float] = previous.get("seconds", {})
    failures: dict[str, str] = previous.get("failures", {})

    def convert(f: d2p.Fixture, dest: Path) -> str | None:
        if args.engine == "docxide":
            fail = d2p.try_convert_fixture("docxide-pdf", binary, f, dest)
            return None if fail is None else str(fail.get("error"))
        # The same per-document timeout and PDF check as the converters run_eval drives (#89).
        with tempfile.TemporaryDirectory(prefix="conv_") as tmp:
            r = so.convert_one(soffice, f.docx, Path(tmp), force=True, timeout=d2p.CONVERT_TIMEOUT_S)
            if not r.ok or r.pdf is None:
                return r.error or "soffice failed"
            shutil.move(str(r.pdf), dest)
        broken = d2p._unreadable_pdf(dest)
        if broken is not None:
            dest.unlink(missing_ok=True)
        return broken

    def one(f: d2p.Fixture) -> tuple[str, str | None]:
        start = time.perf_counter()
        err = convert(f, cand / f"{f.stem}.pdf")
        seconds[f.stem] = round(time.perf_counter() - start, 3)
        if err:
            failures[f.stem] = err
        else:
            failures.pop(f.stem, None)
        return f.stem, err

    t0, failed = time.monotonic(), 0
    try:
        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            for i, fut in enumerate(as_completed([pool.submit(one, f) for f in todo]), 1):
                stem, err = fut.result()
                failed += err is not None
                if err:
                    print(f"FAILED {stem}: {err}", flush=True)
                if i % 100 == 0 or i == len(todo):
                    el = time.monotonic() - t0
                    print(f"[{i}/{len(todo)}] failed {failed} elapsed {el:.0f}s eta {el / i * (len(todo) - i):.0f}s", flush=True)
    finally:
        record = {"engine": args.engine, "workers": args.jobs, "seconds": dict(sorted(seconds.items())),
                  "failures": dict(sorted(failures.items()))}
        with tempfile.TemporaryDirectory(prefix=".convert_seconds.", dir=args.out) as tmp:
            record_tmp = Path(tmp) / record_path.name
            record_tmp.write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
            os.replace(record_tmp, record_path)
    print(f"done: {len(list(cand.glob('*.pdf')))} PDFs in {cand}, {failed} failed", flush=True)


if __name__ == "__main__":
    main()

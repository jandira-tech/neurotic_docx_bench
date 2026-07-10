#!/usr/bin/env -S uv run python
"""Generate genuinely re-serialized DOCX round-trips for the Python ``superdoc``
tool (bench.yaml run ``superdoc``), over all files in
``corpus/word_based/word_working_roundtrip``.

Route: ``client.open() → save()`` — genuinely re-serialized (word/document.xml
differs from the input), per the re-serialization analysis.

For each input file the script:
  1. Reads the DOCX bytes and computes word/document.xml MD5.
  2. Opens the document with SuperDocClient and saves it (round-trip).
  3. Validates the output is a real DOCX (zip + w:document root).
  4. Computes the new word/document.xml MD5 and checks whether the XML
     was genuinely re-serialized (different MD5) or a no-op (identical).
  5. Writes the output to out/roundtrip/superdoc/<original-filename>.
  6. Records failures in out/roundtrip/superdoc/generate_failures.json.

Usage:
  uv run python scripts/generate-roundtrips-superdoc.py
  uv run python scripts/generate-roundtrips-superdoc.py --limit 5 --force
  uv run python scripts/generate-roundtrips-superdoc.py --source-dir corpus/word_based/word_working_roundtrip
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path

from superdoc import SuperDocClient

# ── Helpers ──────────────────────────────────────────────────────────────────


def find_docx_files(directory: Path) -> list[Path]:
    """Find all .docx files (excluding ~$ Word lock files) in a directory."""
    return sorted(
        f for f in directory.iterdir()
        if f.suffix == ".docx" and not f.name.startswith("~$")
    )


def doc_xml_md5(data: bytes) -> str:
    """MD5 of the word/document.xml entry inside a DOCX (bytes)."""
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        return hashlib.md5(z.read("word/document.xml")).hexdigest()


def is_valid_docx(data: bytes) -> bool:
    """Quick validity check: is this a plausible DOCX? (zip + w:document root)."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            xml = z.read("word/document.xml").decode("utf-8", errors="replace")
            return "<w:document" in xml
    except Exception:
        return False


# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate round-trips for the Python superdoc tool",
    )
    parser.add_argument(
        "--source-dir",
        default="corpus/word_based/word_working_roundtrip",
        help="Directory containing .docx files to round-trip",
    )
    parser.add_argument(
        "--out",
        default="out/roundtrip",
        help="Base output directory (files go to <out>/superdoc/)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process only the first N files (0 = all)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-generate even if output already exists",
    )
    args = parser.parse_args()

    # A scoped bench invocation exports $BENCH_TOOLS (comma-separated run names);
    # skip entirely when the Python superdoc run isn't part of it. Exit 100 is the
    # "nothing to do" sentinel the CLI recognises to suppress its rule/header.
    bench_tools = [t.strip() for t in os.environ.get("BENCH_TOOLS", "").split(",") if t.strip()]
    if bench_tools and "superdoc" not in bench_tools:
        return 100

    source_dir = Path(args.source_dir)
    out_dir = Path(args.out) / "superdoc"
    out_dir.mkdir(parents=True, exist_ok=True)

    files = find_docx_files(source_dir)
    if not files:
        print(f"No .docx files found in {source_dir}", file=sys.stderr)
        return 1

    process_files = files[: args.limit] if args.limit else files
    print(f"Source: {source_dir}  ({len(files)} docx files, processing {len(process_files)})")
    print(f"Output: {out_dir}/\n")

    failures: list[dict] = []
    ok = 0
    reserialized = 0
    identical = 0

    print("▶ superdoc  (route: open → save)")

    client = SuperDocClient(user={"name": "bench", "email": "bench@example.com"})

    for i, file in enumerate(process_files):
        name = file.name
        out_path = out_dir / name

        if not args.force and out_path.exists():
            ok += 1
            continue

        try:
            input_bytes = file.read_bytes()
            orig_md5 = doc_xml_md5(input_bytes)

            with tempfile.TemporaryDirectory() as tmp:
                tmp_path = Path(tmp)
                ip = tmp_path / "in.docx"
                op = tmp_path / "out.docx"
                ip.write_bytes(input_bytes)
                session = client.open({"sessionId": f"rt{i}", "doc": str(ip)})
                session.save({"out": str(op), "force": True})
                session.close({})
                output = op.read_bytes()

            if not is_valid_docx(output):
                raise ValueError("invalid output DOCX (missing word/document.xml or w:document root)")

            out_path.write_bytes(output)
            ok += 1

            # Best-effort re-serialization check
            try:
                new_md5 = doc_xml_md5(output)
                if new_md5 != orig_md5:
                    reserialized += 1
                else:
                    identical += 1
            except Exception:
                pass  # Can't determine — not counted
        except Exception as e:
            failures.append({"doc": name, "stage": "roundtrip", "error": str(e)[:200]})
            out_path.unlink(missing_ok=True)

        # Progress
        if (i + 1) % 20 == 0 or i + 1 == len(process_files):
            print(f"  {i + 1}/{len(process_files)} processed")

    # Clean up client
    # SuperDocClient has no close method

    (out_dir / "generate_failures.json").write_text(json.dumps(failures, indent=2))

    print(
        f"  ✅ {ok} ok, ❌ {len(failures)} failed, "
        f"re-serialized: {reserialized}, identical: {identical}",
    )
    if failures:
        print(f"  → {out_dir / 'generate_failures.json'}")

    return 0 if ok > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env -S uv run python
"""DOCX → DOCX round-trip capability test for the Python `superdoc` tool.

Attempts a direct open → save round-trip with one sample document.
If that fails, falls back to soffice docx→html→docx.

Usage:
  uv run python scripts/docx-roundtrip-superdoc.py [path/to/sample.docx]
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from superdoc import SuperDocClient

SAMPLE = (
    sys.argv[1]
    if len(sys.argv) > 1
    else "corpus/word_based/docx_source/1_5_line_spacing_id_paraid_overflow.docx"
)
OUT_DIR = Path("out/roundtrip-test")
OUT_DIR.mkdir(parents=True, exist_ok=True)

TOOL = "superdoc"


def soffice_convert(src: Path, out_format: str, out_dir: Path) -> Path | None:
    """Soffice --headless --convert-to <fmt> --outdir <dir> <src>; returns output path."""
    out_dir.mkdir(parents=True, exist_ok=True)
    # remove stale output
    expected = out_dir / (src.stem + "." + out_format)
    expected.unlink(missing_ok=True)
    try:
        subprocess.run(
            ["soffice", "--headless", "--convert-to", out_format, "--outdir", str(out_dir), str(src)],
            capture_output=True, timeout=60, check=True,
        )
    except Exception:
        return None
    return expected if expected.exists() else None


def main() -> int:
    sample = Path(SAMPLE).read_bytes()
    print(f"\nSample: {SAMPLE}  ({len(sample)} bytes)\n")

    # ── Primary: open → save (pure round-trip) ────────────────────────────────
    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            bp = tmp / "b.docx"
            op = tmp / "o.docx"
            bp.write_bytes(sample)
            client = SuperDocClient(user={"name": "bench", "email": "b@b.b"})
            s = client.open({"sessionId": "rt", "doc": str(bp)})
            s.save({"out": str(op), "force": True})
            s.close({})
            out = op.read_bytes()
            out_path = OUT_DIR / f"{TOOL}.docx"
            out_path.write_bytes(out)
            print(f"✅ {TOOL:<28} {'docx→docx':<16} {len(out):>6}B  valid → {out_path}")
            return 0
    except Exception as e:
        print(f"❌ {TOOL:<28} {'docx→docx':<16} {str(e)[:150]}")

    # ── Fallback: soffice docx→html→docx ──────────────────────────────────────
    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            bp = tmp / "b.docx"
            bp.write_bytes(sample)
            # docx → html
            html = soffice_convert(bp, "html", tmp)
            if not html:
                print(f"❌ {TOOL:<28} {'docx→html→docx':<16} soffice html conversion failed")
                return 1
            # html → docx
            docx_out = soffice_convert(html, "docx", tmp)
            if not docx_out:
                print(f"❌ {TOOL:<28} {'docx→html→docx':<16} soffice docx conversion failed")
                return 1
            out = docx_out.read_bytes()
            out_path = OUT_DIR / f"{TOOL}_via_html.docx"
            out_path.write_bytes(out)
            print(f"✅ {TOOL:<28} {'docx→html→docx':<16} {len(out):>6}B (via soffice) → {out_path}")
            return 0
    except Exception as e:
        print(f"❌ {TOOL:<28} {'docx→html→docx':<16} {str(e)[:150]}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

"""#67: logger_coverage.py reads the PDFs scripts/word_pdf.py writes, named ``<stem>_byword.pdf``."""

from __future__ import annotations

import csv
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "live-bench" / "harvest" / "logger_coverage.py"


def test_a_byword_pdf_is_an_opens_ok_verdict(tmp_path: Path) -> None:
    chunk = tmp_path / "c00"
    (chunk / "in").mkdir(parents=True)
    (chunk / "pdf").mkdir()
    (chunk / "in" / "jubarte__01a11a49_0001.docx").write_bytes(b"PK")
    (chunk / "pdf" / "jubarte__01a11a49_0001_byword.pdf").write_bytes(b"%PDF-1.7")
    (chunk / "start").write_text(datetime.now().strftime("%H:%M:%S"))
    log = tmp_path / "screen.log"
    log.write_text("")
    subprocess.run([sys.executable, str(SCRIPT), str(log), str(tmp_path)], check=True, capture_output=True)
    rows = list(csv.DictReader((tmp_path / "coverage.csv").open()))
    assert [(r["file"], r["word"]) for r in rows] == [("jubarte__01a11a49_0001.docx", "opens_ok")]

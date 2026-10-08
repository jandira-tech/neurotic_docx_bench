# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""en_pdf_identity.py A_DIR B_DIR REDLINE_DIR PDF_DIR : does each Word PDF <a>__vs__<b>.pdf show file A and file B?

Reuses neurotic_docx_bench/scripts/redline_identity.py (body_text, coverage, MIN_COVERAGE): the same
verbatim-window coverage check_redline_identity.py applies to the redline docx, here against the PDF's text.
A markup PDF shows deletions and insertions together, so A and B are each looked up in the whole PDF text,
and so is the redline's own plain view (its deletions plus insertions in document order). Each side is
judged on its own; nothing is averaged. Exit 1 when any PDF fails."""
import sys, pathlib, statistics
sys.path.insert(0, "/Users/arthrod/temp/T/neurotic_docx_bench/scripts")
from redline_identity import body_text, coverage, MIN_COVERAGE, _norm
import pymupdf

a_dir, b_dir, rl_dir, pdf_dir = (pathlib.Path(p) for p in sys.argv[1:5])
rows, bad, missing = [], 0, 0
for docx in sorted(rl_dir.glob("*.docx")):
    a_stem, b_stem = docx.stem.split("__vs__", 1)
    pdf = pdf_dir / f"{docx.stem}.pdf"
    if not pdf.is_file():
        missing += 1; print(f"MISSING {docx.stem[:12]}…"); continue
    with pymupdf.open(pdf) as d:
        text = _norm(" ".join(page.get_text() for page in d))
    cov_a = coverage(body_text(a_dir / f"{a_stem}.docx", "plain"), text)
    cov_b = coverage(body_text(b_dir / f"{b_stem}.docx", "plain"), text)
    cov_rl = coverage(body_text(docx, "plain"), text)
    rows.append((docx.stem, cov_a, cov_b, cov_rl))
    if min(cov_a, cov_b) < MIN_COVERAGE:
        bad += 1; print(f"LOW  {a_stem[:12]} vs {b_stem[:12]} A={cov_a:.2f} B={cov_b:.2f} redline={cov_rl:.2f}")
for i, name in ((1, "A"), (2, "B"), (3, "redline")):
    v = [r[i] for r in rows]
    if v: print(f"{name}: min={min(v):.2f} median={statistics.median(v):.2f} <0.9: {sum(x < 0.9 for x in v)} <0.5: {sum(x < 0.5 for x in v)}")
print(f"checked={len(rows)} low={bad} missing={missing}")
sys.exit(1 if bad or missing else 0)

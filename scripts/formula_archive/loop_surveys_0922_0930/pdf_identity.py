# SPDX-License-Identifier: AGPL-3.0-only
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""pdf_identity.py DOCX_DIR PDF_DIR... : reject PDFs that are not the docx their name claims.

Modelled on neurotic_docx_bench/scripts/check_redline_identity.py. Word rewrites
fields, numbering and quotes, and PDF extraction scrambles order, so text never
matches exactly. Each docx and PDF becomes a set of 8-character shingles
(whitespace removed). A PDF passes when its own docx is the best match among
all sources and covers at least MIN of that docx's shingles. A PDF saved under
the wrong name has its best match on some other docx.
"""

import re
import subprocess
import unicodedata
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, "/Users/arthrod/temp/T/neurotic_docx_bench/scripts")
from redline_identity import body_text  # noqa: E402

K, MIN = 8, 0.5
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def shingles(text: str) -> set[str]:
    # NFKC folds Arabic presentation forms and vertical CJK punctuation back to
    # the letters the docx holds; bidi marks and tatweel are layout, not text
    t = unicodedata.normalize("NFKC", text)
    t = re.sub(r"[\s\u200b-\u200f\u202a-\u202e\u2066-\u2069\u0640]+", "", t)
    return {t[i : i + K] for i in range(max(len(t) - K + 1, 0))}


def docx_text(path: Path) -> str:
    parts = [body_text(path)]
    with zipfile.ZipFile(path) as z:
        for n in z.namelist():
            if re.match(r"word/(header|footer|footnotes|endnotes)\d*\.xml$", n):
                parts.append("".join(e.text or "" for e in ET.fromstring(z.read(n)).iter(f"{W}t")))
    return " ".join(parts)


def pdf_text(path: Path) -> str:
    # poppler returns RTL runs in logical order; PyMuPDF gives visual order,
    # which reverses Arabic and Thaana and hides a correct file
    return subprocess.run(["pdftotext", str(path), "-"], capture_output=True, text=True).stdout


def main() -> None:
    src, *pdf_dirs = map(Path, sys.argv[1:])
    docs = {p.stem: shingles(docx_text(p)) for p in sorted(src.glob("*.docx"))}
    # an inverted index keeps the 500 x 500 comparison cheap
    index: dict[str, list[str]] = {}
    for stem, sh in docs.items():
        for s in sh:
            index.setdefault(s, []).append(stem)
    bad_total = 0
    for d in pdf_dirs:
        bad = empty = checked = 0
        for pdf in sorted(d.glob("*.pdf")):
            own = docs.get(pdf.stem)
            if own is None:
                print(f"BAD  {d.name}/{pdf.stem[:12]}: no docx of that name")
                bad += 1
                continue
            if not own:
                empty += 1
                continue
            checked += 1
            ps = shingles(pdf_text(pdf))
            hits: dict[str, int] = {}
            for s in ps:
                for stem in index.get(s, ()):
                    hits[stem] = hits.get(stem, 0) + 1
            cover = {stem: n / len(docs[stem]) for stem, n in hits.items() if len(docs[stem]) >= 20}
            own_cov = hits.get(pdf.stem, 0) / len(own)
            best = max(cover, key=cover.get, default=pdf.stem)
            if best != pdf.stem and cover[best] > own_cov + 0.05 or own_cov < MIN:
                bad += 1
                print(f"BAD  {d.name}/{pdf.stem[:12]} own={own_cov:.2f} best={best[:12]}@{cover.get(best, 0):.2f}")
        print(f"{d.name}: checked={checked} no-text-docx={empty} bad={bad}")
        bad_total += bad
    sys.exit(1 if bad_total else 0)


if __name__ == "__main__":
    main()

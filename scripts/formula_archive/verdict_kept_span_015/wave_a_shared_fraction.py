#!/usr/bin/env -S uv run --script
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# /// script
# requires-python = ">=3.14"
# dependencies = ["typer>=0.12"]
# ///
"""Build wave A: shared-fraction probes, and freeze the prediction first.

One variable in each document: the fraction of the shorter paragraph that
is one consecutive shared run, from 0 to 1 in steps of 0.01. Three
documents keep everything else fixed and change which side is longer.
The prediction file is written before anything is sent to the endpoint.

    wave_a_shared_fraction.py --rule results/paragraph_rule/hypothesis.json --out results/paragraph_rule/wave_a
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from xml.sax.saxutils import escape
import zipfile

import typer

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from predict_paragraph_verdict import load_rule, predict_pairs

app = typer.Typer(add_completion=False, help=__doc__)

SHORTER = 200
LONGER = 300

_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>
"""

_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
"""

_WORD_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>
"""

_STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
  </w:style>
</w:styles>
"""


def write_paragraph_docx(path: Path, paragraphs: list[str]) -> None:
    body = []
    for text in paragraphs:
        body.append(
            "<w:p><w:r><w:t xml:space=\"preserve\">"
            + escape(text)
            + "</w:t></w:r></w:p>"
        )
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{''.join(body)}<w:sectPr/></w:body></w:document>"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as package:
        package.writestr("[Content_Types].xml", _CONTENT_TYPES)
        package.writestr("_rels/.rels", _RELS)
        package.writestr("word/_rels/document.xml.rels", _WORD_RELS)
        package.writestr("word/styles.xml", _STYLES)
        package.writestr("word/document.xml", document)


def _pair(fraction_i: int, before_len: int, after_len: int) -> tuple[str, str, int]:
    shorter = min(before_len, after_len)
    shared = (fraction_i * shorter + 50) // 100
    def build(length: int, left_char: str, right_char: str) -> str:
        flank = length - shared
        left = flank // 2
        right = flank - left
        return (left_char * left) + ("S" * shared) + (right_char * right)
    return build(before_len, "A", "B"), build(after_len, "C", "D"), shared


def build_pairs() -> dict[str, list[dict]]:
    docs = {
        "equal": (SHORTER, SHORTER),
        "before-longer": (LONGER, SHORTER),
        "after-longer": (SHORTER, LONGER),
    }
    out: dict[str, list[dict]] = {}
    for doc, (before_len, after_len) in docs.items():
        rows = []
        for fraction_i in range(0, 101):
            before, after, shared = _pair(fraction_i, before_len, after_len)
            rows.append(
                {
                    "doc": doc,
                    "id": f"{doc}-{fraction_i:03d}",
                    "before": before,
                    "after": after,
                    "fraction_i": fraction_i,
                    "shared": shared,
                }
            )
        out[doc] = rows
    return out


@app.command()
def main(
    rule_path: Path = typer.Option(..., "--rule", help="Hypothesis written before this run."),
    out: Path = typer.Option(..., "--out", help="Directory for the docx pair and the prediction."),
) -> None:
    """Write three probe pairs and the frozen prediction. Do not call the endpoint."""
    rule = load_rule(rule_path)
    groups = build_pairs()
    flat = [row for doc in ("equal", "before-longer", "after-longer") for row in groups[doc]]
    predicted = predict_pairs(flat, rule)
    out.mkdir(parents=True, exist_ok=True)
    prediction = out / "prediction.jsonl"
    prediction.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in predicted))
    for doc, rows in groups.items():
        write_paragraph_docx(out / f"{doc}-original.docx", [row["before"] for row in rows])
        write_paragraph_docx(out / f"{doc}-revised.docx", [row["after"] for row in rows])
    typer.echo(f"wrote {prediction} paragraphs={len(flat)}")


if __name__ == "__main__":
    app()

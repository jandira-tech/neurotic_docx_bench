#!/usr/bin/env python3
"""Adversarial probe on Stage L1's BOTH_HOLD bucket — does it mean what the plan says?

The L1 gate reads one number: the share of the cluster where both functional
invariants hold. The plan attaches an inference to that number — *"the markup is
correct and the SCORER disagrees"* — and stops the whole programme on it.

The inference does not follow from the instrument. ``functional_lens`` compares
**text**: it accepts and rejects the candidate and checks the resulting body text
against next and base. Everything that decides how a redline *renders* is outside
that comparison — which paragraph a change sits in, whether an edit is marked
in-place or as a delete-plus-insert of the whole paragraph, and formatting-change
markup (``w:rPrChange``/``w:pPrChange``). A candidate can satisfy both invariants
and still be a visibly different redline from Word's.

So this probe compares each BOTH_HOLD candidate against **Word's own oracle
redline DOCX** for the same pair, on the axes the lens cannot see:

- ``volume`` — inserted/deleted characters, candidate vs oracle. Tests the plan's
  hypothesis that lossless *under-marks*. Under-marking means a ratio below 1.
- ``in_place`` — paragraphs carrying BOTH a ``w:ins`` and a ``w:del``, i.e. the
  Word-style intra-paragraph edit. A candidate that replaces whole paragraphs
  instead scores zero here while the oracle does not.

Neither number is a score. They exist to answer one question: when the lens says
BOTH_HOLD, is the candidate's markup the *same redline* Word produced?

Usage:
    uv run python scripts/l1_markup_probe.py [--bucket both_hold]
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

_REPO = Path(__file__).resolve().parents[1]

ORACLE_DIRS = (
    "corpus/word_based/docx_redlines_word",
    "corpus/word_based/docx_redlines_randomized",
    "corpus/word_redlines_superdoc/docx_redlines_word",
)
ORACLE_SUFFIXES = ("_redline.docx", "_word_redline.docx")
"""Both capture-variant spellings; ``oracle_pair_key`` normalises ``_word`` away."""


@dataclass(frozen=True)
class MarkupShape:
    ins_chars: int
    del_chars: int
    n_paragraphs: int
    n_in_place: int
    """Paragraphs carrying both an insertion and a deletion — the Word-style
    in-place edit, and the thing a paragraph-granular replace never produces."""


def markup_shape(docx: Path) -> MarkupShape:
    with zipfile.ZipFile(docx) as zf:
        root = ET.fromstring(zf.read("word/document.xml"))
    ns = root.tag[1 : root.tag.index("}")]
    w = lambda tag: f"{{{ns}}}{tag}"  # noqa: E731
    body = root.find(w("body"))
    if body is None:
        raise ValueError(f"{docx}: no w:body")
    ins_chars = sum(
        len(t.text or "") for e in root.iter(w("ins")) for t in e.iter(w("t"))
    )
    del_chars = sum(
        len(t.text or "") for e in root.iter(w("del")) for t in e.iter(w("delText"))
    )
    paragraphs = list(body.iter(w("p")))
    in_place = sum(
        1
        for p in paragraphs
        if any(True for _ in p.iter(w("ins"))) and any(True for _ in p.iter(w("del")))
    )
    return MarkupShape(ins_chars, del_chars, len(paragraphs), in_place)


def find_oracle(key: str) -> Path | None:
    for d in ORACLE_DIRS:
        for suffix in ORACLE_SUFFIXES:
            p = _REPO / d / f"{key}{suffix}"
            if p.is_file():
                return p
    return None


def _ratio(candidate: int, oracle: int) -> float | None:
    """None when the oracle marks nothing — a ratio against zero is not a number,
    and silently calling it 1.0 would report agreement that was never measured."""
    return candidate / oracle if oracle else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", type=Path, default=_REPO / "results/l1_partition/jubarte-final-lossless.json")
    ap.add_argument(
        "--docx",
        type=Path,
        default=_REPO / "runs/l1_partition__jubarte-final-lossless/docx",
        help="regenerated candidates (run_l1_partition.py's workdir)",
    )
    ap.add_argument("--tool", default="jubarte-final-lossless")
    ap.add_argument("--bucket", default="both_hold")
    args = ap.parse_args(argv)

    report = json.loads(args.report.read_text(encoding="utf-8"))
    keys = report["partition"]["members"][args.bucket]

    ins_ratios: list[float] = []
    del_ratios: list[float] = []
    rows: list[tuple[str, MarkupShape, MarkupShape]] = []
    missing = 0
    for key in keys:
        cand = args.docx / f"{key}_{args.tool}_redline.docx"
        oracle = find_oracle(key)
        if not cand.is_file() or oracle is None:
            missing += 1
            continue
        try:
            c, o = markup_shape(cand), markup_shape(oracle)
        except (ValueError, zipfile.BadZipFile, ET.ParseError):
            missing += 1
            continue
        rows.append((key, c, o))
        if (r := _ratio(c.ins_chars, o.ins_chars)) is not None:
            ins_ratios.append(r)
        if (r := _ratio(c.del_chars, o.del_chars)) is not None:
            del_ratios.append(r)

    if not rows:
        print(f"no comparable documents in bucket {args.bucket!r}", file=sys.stderr)
        return 1

    n = len(rows)
    print(f"bucket {args.bucket!r}: {n} documents compared against the Word oracle "
          f"({missing} unmatched)\n")

    print("VOLUME — does the candidate mark less than Word?")
    print(f"  inserted chars, candidate/oracle: median {statistics.median(ins_ratios):.3f} (n={len(ins_ratios)})")
    print(f"  deleted  chars, candidate/oracle: median {statistics.median(del_ratios):.3f} (n={len(del_ratios)})")
    within = sum(
        1
        for _, c, o in rows
        if (ri := _ratio(c.ins_chars, o.ins_chars)) is not None
        and (rd := _ratio(c.del_chars, o.del_chars)) is not None
        and 0.8 <= ri <= 1.25
        and 0.8 <= rd <= 1.25
    )
    silent = sum(1 for _, c, _ in rows if c.ins_chars == 0 and c.del_chars == 0)
    print(f"  within 0.8–1.25x of the oracle on BOTH: {within}/{n}")
    print(f"  candidates emitting NO markup at all:   {silent}/{n}")

    print("\nSHAPE — is it the same redline?")
    print(f"  in-place (ins+del) paragraphs, candidate median "
          f"{statistics.median([c.n_in_place for _, c, _ in rows]):.1f} vs oracle median "
          f"{statistics.median([o.n_in_place for _, _, o in rows]):.1f}")
    fewer = sum(1 for _, c, o in rows if c.n_in_place < o.n_in_place)
    none_at_all = sum(1 for _, c, o in rows if c.n_in_place == 0 and o.n_in_place > 0)
    more_paras = sum(1 for _, c, o in rows if c.n_paragraphs > o.n_paragraphs)
    print(f"  candidate has FEWER in-place paragraphs than the oracle: {fewer}/{n}")
    print(f"  candidate has NONE where the oracle has some:            {none_at_all}/{n}")
    print(f"  candidate has more paragraphs than the oracle:           {more_paras}/{n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

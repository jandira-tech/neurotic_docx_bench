#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Synthetic single-paragraph probe pairs at controlled similarity, for
Word's Compare: does it word-diff the paragraph or replace it whole?

Each probe is one long paragraph between two short label paragraphs (the
shape of a sectioned document), in A and in B. B keeps a chosen fraction of
A's words in equal runs of a chosen length, evenly spaced, and rewrites the
rest with words from a DISJOINT vocabulary, so the kept fraction is the
exact word-LCS and the run length is the exact longest shared run.

    long_paragraph_probes.py OUT --words 400 --keep 0.1,0.2,0.3 --run 2,4,8,16
    long_paragraph_probes.py OUT --words 100,400,800 --keep 0.25 --run 8 --no-labels

Writes OUT/A/<name>.docx, OUT/B/<name>.docx and OUT/manifest.csv
(name, words, keep, run, labels, lines, a_words, b_words, kept_words,
runs). Minimal Word-valid packages, no personal data, deterministic.
"""

from __future__ import annotations

import argparse
import csv
import random
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

VOCAB_A = (
    "the agreement shall provide that each party will deliver notice within days of the "
    "effective date and the supplier must maintain records for every order placed under this "
    "schedule including invoices receipts and correspondence while the customer retains the "
    "right to audit those records on reasonable notice during business hours at its own expense "
    "any dispute arising from this clause is referred first to the account managers then to "
    "senior officers and only after thirty days to mediation in the city named above"
).split()
VOCAB_B = (
    "licensor grants licensee a limited revocable permission to install configure operate "
    "and monitor the software on approved hardware located inside the designated facility "
    "subject to payment of annual fees adjusted yearly by the published index plus two percent "
    "provided however that no copies beyond those required for backup are made and that "
    "technical support requests follow the escalation ladder described in exhibit four with "
    "response targets measured from acknowledgement rather than submission by the help desk"
).split()


PUNCT = True

CONS, VOWELS = "bcdfgklmnprstvz", "aeiou"


def pseudo_vocab(seed: int, size: int, chars: int | None) -> list[str]:
    """Pronounceable pseudo-words from one seed; two seeds give disjoint sets
    (checked). `chars` fixes every word's length, else 2–5 syllables."""
    rng = random.Random(seed)
    out: set[str] = set()
    while len(out) < size:
        if chars:
            w = "".join((CONS if i % 2 == 0 else VOWELS)[rng.randrange(len(CONS if i % 2 == 0 else VOWELS))] for i in range(chars))
        else:
            w = "".join(rng.choice(CONS) + rng.choice(VOWELS) for _ in range(rng.randint(1, 3)))
        out.add(w)
    return sorted(out)


def prose(vocab: list[str], n: int, rng: random.Random) -> list[str]:
    """n words of sentence-shaped text: 9–17 words, a period, capital next
    (plain lowercase words when PUNCT is off)."""
    out: list[str] = []
    while len(out) < n:
        k = rng.randint(9, 17)
        sent = [rng.choice(vocab) for _ in range(k)]
        if PUNCT:
            sent[0] = sent[0].capitalize()
            sent[-1] += "."
        out.extend(sent)
    return out[:n]


def revise(a: list[str], keep: float, run: int, rng: random.Random) -> tuple[list[str], int, int]:
    """B keeps round(keep·len) words of A in runs of `run`, evenly spaced; the
    rest is fresh VOCAB_B prose of the same length per gap."""
    n = len(a)
    kept = round(keep * n)
    runs = max(kept // run, 1) if kept else 0
    if runs == 0:
        return prose(VOCAB_B, n, rng), 0, 0
    gap_total = n - runs * run
    gaps = [gap_total // (runs + 1)] * (runs + 1)
    for i in range(gap_total - sum(gaps)):
        gaps[i % (runs + 1)] += 1
    b: list[str] = []
    pos = 0
    for r in range(runs):
        g = gaps[r]
        b.extend(prose(VOCAB_B, g, rng))
        pos += g
        b.extend(a[pos:pos + run])
        pos += run
    b.extend(prose(VOCAB_B, gaps[-1], rng))
    assert len(b) == n, (len(b), n)
    return b, runs * run, runs


def para(text: str, lines: int = 0) -> str:
    if lines:
        ws = text.split(" ")
        step = max(len(ws) // (lines + 1), 1)
        chunks = [" ".join(ws[i:i + step]) for i in range(0, len(ws), step)]
        runs = "<w:r><w:br/></w:r>".join(f"<w:r><w:t xml:space=\"preserve\">{escape(c)}</w:t></w:r>" for c in chunks)
        return f"<w:p>{runs}</w:p>"
    return f"<w:p><w:r><w:t xml:space=\"preserve\">{escape(text)}</w:t></w:r></w:p>"


def docx(path: Path, paras: list[str]) -> None:
    body = "".join(paras)
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}<w:sectPr><w:pgSz w:w=\"12240\" w:h=\"15840\"/>"
        '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/>'
        "</w:sectPr></w:body></w:document>"
    )
    types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        "</Relationships>"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", document)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out")
    ap.add_argument("--words", default="400", help="comma list of paragraph lengths")
    ap.add_argument("--keep", default="0.10,0.15,0.20,0.25,0.30,0.40", help="comma list of kept fractions")
    ap.add_argument("--run", default="2,4,8,16", help="comma list of kept-run lengths (words)")
    ap.add_argument("--lines", type=int, default=0, help="soft line breaks (w:br) per long paragraph")
    ap.add_argument("--no-labels", action="store_true", help="the paragraph alone, no label paragraphs around it")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--vocab", choices=["english", "disjoint"], default="english", help="english: two legal-prose word lists sharing stopwords; disjoint: pseudo-words, no token in common")
    ap.add_argument("--word-chars", type=int, default=0, help="with --vocab disjoint: fix every word at N characters")
    ap.add_argument("--no-punct", action="store_true", help="no sentence periods or capitals (no shared sign tokens)")
    ap.add_argument("--a-chars", type=int, default=0, help="with --vocab disjoint: A's words (and so the kept words) are N characters")
    ap.add_argument("--b-chars", type=int, default=0, help="with --vocab disjoint: B's rewritten words are N characters")
    args = ap.parse_args()
    global VOCAB_A, VOCAB_B, PUNCT
    PUNCT = not args.no_punct
    if args.vocab == "disjoint":
        VOCAB_A = pseudo_vocab(101, 300, args.a_chars or args.word_chars or None)
        VOCAB_B = [w for w in pseudo_vocab(202, 400, args.b_chars or args.word_chars or None) if w not in set(VOCAB_A)][:300]
        assert not set(VOCAB_A) & set(VOCAB_B)
    tag = ("" if args.vocab == "english" else "_dj") + (f"_c{args.word_chars}" if args.word_chars else "") + (f"_a{args.a_chars}b{args.b_chars}" if args.a_chars or args.b_chars else "") + ("_np" if args.no_punct else "")
    out = Path(args.out)
    rows = []
    for n in (int(x) for x in args.words.split(",")):
        for keep in (float(x) for x in args.keep.split(",")):
            for run in (int(x) for x in args.run.split(",")):
                rng = random.Random(args.seed * 1000003 + n * 1009 + int(keep * 1000) * 7 + run)
                a = prose(VOCAB_A, n, rng)
                b, kept_words, runs = revise(a, keep, run, rng)
                name = f"w{n}_k{int(keep * 100):02d}_r{run:02d}" + tag + ("_nolab" if args.no_labels else "") + (f"_br{args.lines}" if args.lines else "")
                labels = not args.no_labels
                pa = ([para("Section one"), para("Clause")] if labels else []) + [para(" ".join(a), args.lines)] + ([para("End of section")] if labels else [])
                pb = ([para("Section one"), para("Clause")] if labels else []) + [para(" ".join(b), args.lines)] + ([para("End of section")] if labels else [])
                docx(out / "A" / f"{name}.docx", pa)
                docx(out / "B" / f"{name}.docx", pb)
                rows.append({"name": name, "words": n, "keep": keep, "run": run, "vocab": args.vocab, "word_chars": args.word_chars, "punct": PUNCT, "labels": labels, "lines": args.lines, "a_words": len(a), "b_words": len(b), "kept_words": kept_words, "runs": runs})
    with (out / "manifest.csv").open("w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)
    print(f"{len(rows)} probe pairs under {out}")


if __name__ == "__main__":
    main()

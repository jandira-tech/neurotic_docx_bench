#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Anatomy of a tracked-change docx: exact revision positions, paragraph
verdicts, and the similarity features behind each verdict.

Stdlib only, so it runs against any tool's redline (Word, jubarte, Litera,
PowerTools …). Four commands:

    redline_anatomy.py segments REDLINE.docx [--json out.json]
        Every paragraph in document order (body, table cells, text boxes),
        its segments (eq / ins / del / moveTo / moveFrom), and for each
        revision its exact character and word offsets in the ORIGINAL and
        the REVISED text streams, paragraph-local and document-global.

    redline_anatomy.py verdicts A.docx B.docx REDLINE.docx [--json out.json]
        Rebuilds the original and the revision from the redline (respecting
        inserted and deleted paragraph marks), checks both against A and B
        character by character, and classifies every paragraph:
        unchanged · word-level · replaced (whole paragraph inserted next to
        a whole paragraph deleted) · inserted · deleted · mark-only.

    redline_anatomy.py features A.docx B.docx REDLINE.docx [--csv rows.csv]
        For every A↔B paragraph pair the redline relates (word-level or
        replaced), the candidate rule inputs: lengths, true word LCS, longest
        shared run, shared n-grams, run coverage, Jaccard/Dice/cosine,
        sentence and line matches, greedy-diff island counts, position and
        anchor context. One row per pair, verdict attached, appendable.

    redline_anatomy.py fit rows.csv
        Which single feature, threshold, or two-feature rule reproduces the
        verdicts (word-level vs replaced), with margins.

    redline_anatomy.py predict A.docx B.docx [--csv rows.csv]
        Predict Word's verdict for every paragraph pair with the law fitted
        on 313 synthetic single-paragraph probes (2026-10-03, Word 16 for
        Mac; see neurotic_docx_bench probes/WORD_RULE.md):

            kept_chars / max(chars_A, chars_B)
                ≥ 0.102 + 0.044·(runs / 100) + 0.0058·(max_chars / 1000)

        kept_chars = characters of the words an LCS alignment keeps, runs =
        its matched runs. 96.8% on the clean probes, 6/6 on the real pairs
        it was checked against, but only 71% on probes whose rewritten text
        shares stopwords with the original: there Word's own alignment keeps
        fewer matches than an LCS, and that alignment is not reproduced yet.
        Treat a margin under ±0.02 as undecided.

Text model (identical for A, B and the redline, so offsets line up):
`w:t`/`w:delText` text; `w:tab` → \\t; `w:br` → \\n (page break → \\f);
`w:cr` → \\n; `w:noBreakHyphen` → U+2011; `w:softHyphen` → U+00AD;
`w:sym`, drawings, pictures, objects, note references → U+FFFC; field
instructions and `w:fldChar` contribute nothing (results do); only
`mc:Choice` of an AlternateContent; math `m:t` as text.

Words follow Word 16 Compare's tokenization as reconstructed in jubarte
(`src/comparer/units.rs` `word_class`): a word is a maximal run of one
character class — letters (with digits and the apostrophes), signs, or one
of the scripts Word sets apart — each ideograph, fullwidth form and
whitespace character a unit of its own. Word offsets count non-whitespace
units.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import difflib
import json
import math
import re
import statistics
import sys
import unicodedata
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"


def w(tag: str) -> str:
    return f"{{{W_NS}}}{tag}"


def m(tag: str) -> str:
    return f"{{{M_NS}}}{tag}"


OBJECT = "￼"
RUN_TEXT = {w("t"), w("delText"), m("t")}
RUN_SPECIAL = {
    w("tab"): "\t",
    w("cr"): "\n",
    w("noBreakHyphen"): "‑",
    w("softHyphen"): "­",
    w("sym"): OBJECT,
    w("drawing"): OBJECT,
    w("pict"): OBJECT,
    w("object"): OBJECT,
    w("footnoteReference"): OBJECT,
    w("endnoteReference"): OBJECT,
    w("ptab"): "\t",
}
RUN_SKIP = {w("rPr"), w("instrText"), w("delInstrText"), w("fldChar"), w("lastRenderedPageBreak"), w("footnoteRef"), w("endnoteRef"), w("separator"), w("continuationSeparator")}
CONTAINERS = {w("hyperlink"), w("smartTag"), w("sdt"), w("sdtContent"), w("customXml"), w("dir"), w("bdo"), w("fldSimple"), m("oMath"), m("oMathPara"), m("r")}
REV_WRAPPERS = {w("ins"): "ins", w("del"): "del", w("moveTo"): "moveTo", w("moveFrom"): "moveFrom"}

# ── Word's word classes (port of jubarte units.rs word_class) ──────────────────


def _word_class(c: str) -> str:
    o = ord(c)
    if o in (0x27, 0x2019, 0xAA, 0xB5, 0xBA):
        return "L"
    if o < 0x80 and not c.isalnum() and not c.isspace():
        return "S"  # ASCII punctuation
    if 0xA0 <= o <= 0xBF or o in (0xD7, 0xF7):
        return "S"
    ranges = [
        ((0x0500, 0x052F), "1"), ((0x07C0, 0x07FF), "2"), ((0x0E00, 0x0E7F), "3"), ((0x0E80, 0x0EFF), "4"),
        ((0x10A0, 0x10FF), "5"), ((0x1C90, 0x1CBF), "5"), ((0x2D00, 0x2D2F), "5"),
        ((0x1100, 0x11FF), "6"), ((0x3130, 0x318F), "6"), ((0xA960, 0xA97F), "6"), ((0xAC00, 0xD7FF), "6"),
        ((0x1200, 0x139F), "7"), ((0x2D80, 0x2DDF), "7"), ((0xAB00, 0xAB2F), "7"),
        ((0x13A0, 0x13FF), "8"), ((0xAB70, 0xABBF), "8"), ((0x1400, 0x167F), "9"), ((0x18B0, 0x18FF), "9"),
        ((0x1780, 0x17FF), "a"), ((0x19E0, 0x19FF), "a"), ((0x1D00, 0x1DBF), "b"),
        ((0x2010, 0x2027), "S"), ((0x2030, 0x205E), "S"), ((0x20A0, 0x20CF), "S"), ((0x2150, 0x218F), "S"),
        ((0x2460, 0x24FF), "c"), ((0x2190, 0x245F), "S"), ((0x2500, 0x2BFF), "S"), ((0x2E00, 0x2E7F), "S"),
        ((0x2C00, 0x2C5F), "d"), ((0x2C60, 0x2C7F), "e"), ((0xA720, 0xA7FF), "f"),
        ((0x3001, 0x3004), "S"), ((0x3008, 0x3020), "S"), ((0x3030, 0x3030), "S"), ((0x3036, 0x303A), "S"), ((0x303D, 0x303F), "S"),
        ((0x30FB, 0x30FC), "S"), ((0xFE10, 0xFE1F), "S"), ((0xFE30, 0xFE6F), "S"),
        ((0x3005, 0x3007), "g"), ((0x3021, 0x302F), "g"), ((0x3031, 0x3035), "g"), ((0x303B, 0x303C), "g"),
        ((0x3040, 0x309F), "h"), ((0x30A0, 0x30FF), "i"), ((0x31F0, 0x31FF), "i"),
    ]
    if (0x2070 <= o <= 0x209F or 0x2100 <= o <= 0x214F) and not c.isalpha():
        return "S"
    for (lo, hi), cls in ranges:
        if lo <= o <= hi:
            return cls
    return "L"


def _is_cjk(c: str) -> bool:
    o = ord(c)
    return 0x4E00 <= o <= 0x9FFF or 0x3400 <= o <= 0x4DBF or 0x20000 <= o <= 0x2A6DF or 0xF900 <= o <= 0xFAFF


def _is_fullwidth(c: str) -> bool:
    return 0xFF01 <= ord(c) <= 0xFF60


@dataclass
class Unit:
    text: str
    start: int  # char offset in its stream
    end: int
    kind: str  # "w" word | "s" whitespace


def tokenize(text: str) -> list[Unit]:
    """Word-16-style units with char offsets; whitespace chars are units too."""
    units: list[Unit] = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c.isspace() or c == OBJECT:
            units.append(Unit(c, i, i + 1, "s" if c.isspace() else "w"))
            i += 1
            continue
        if _is_cjk(c) or _is_fullwidth(c):
            units.append(Unit(c, i, i + 1, "w"))
            i += 1
            continue
        cls = _word_class(c)
        j = i + 1
        while j < n:
            d = text[j]
            if d.isspace() or d == OBJECT or _is_cjk(d) or _is_fullwidth(d) or _word_class(d) != cls:
                break
            j += 1
        units.append(Unit(text[i:j], i, j, "w"))
        i = j
    return units


def words(text: str) -> list[str]:
    return [u.text for u in tokenize(text) if u.kind == "w"]


# ── Segment extraction ─────────────────────────────────────────────────────────


@dataclass
class Segment:
    kind: str  # eq ins del moveTo moveFrom
    text: str
    rev_id: str | None = None
    author: str | None = None
    date: str | None = None


@dataclass
class Paragraph:
    path: str
    segments: list[Segment]
    mark: str  # "kept" | "ins" | "del"  (the paragraph mark's own revision)
    ppr_change: bool
    rpr_changes: int
    style: str | None

    def text(self, side: str) -> str:
        if side == "orig":
            return "".join(s.text for s in self.segments if s.kind in ("eq", "del", "moveFrom"))
        return "".join(s.text for s in self.segments if s.kind in ("eq", "ins", "moveTo"))


def _rev_attrs(el: ET.Element) -> tuple[str | None, str | None, str | None]:
    return el.get(w("id")), el.get(w("author")), el.get(w("date"))


def _walk_run(run: ET.Element, kind: str, attrs, out: list[Segment], rpr_changes: list[int]) -> None:
    for ch in run:
        if ch.tag == w("rPr"):
            if ch.find(w("rPrChange")) is not None:
                rpr_changes[0] += 1
            continue
        if ch.tag in RUN_TEXT:
            out.append(Segment(kind, ch.text or "", *attrs))
        elif ch.tag == w("br"):
            out.append(Segment(kind, "\f" if ch.get(w("type")) == "page" else "\n", *attrs))
        elif ch.tag in RUN_SPECIAL:
            out.append(Segment(kind, RUN_SPECIAL[ch.tag], *attrs))
        elif ch.tag in RUN_SKIP:
            continue
        elif ch.tag == f"{{{MC_NS}}}AlternateContent":
            choice = ch.find(f"{{{MC_NS}}}Choice")
            if choice is not None:
                out.append(Segment(kind, OBJECT, *attrs))
        elif ch.tag in (w("drawing"), w("pict"), w("object")):
            out.append(Segment(kind, OBJECT, *attrs))
        # anything else inside a run contributes no text


def _walk_inline(el: ET.Element, kind: str, attrs, out: list[Segment], rpr_changes: list[int], nested: list) -> None:
    for ch in el:
        tag = ch.tag
        if tag in REV_WRAPPERS:
            _walk_inline(ch, REV_WRAPPERS[tag], _rev_attrs(ch), out, rpr_changes, nested)
        elif tag == w("r") or tag == m("r"):
            _walk_run(ch, kind, attrs, out, rpr_changes)
            # text boxes live inside runs
            for tx in ch.iter(w("txbxContent")):
                nested.append(tx)
        elif tag in CONTAINERS:
            _walk_inline(ch, kind, attrs, out, rpr_changes, nested)
        elif tag == f"{{{MC_NS}}}AlternateContent":
            choice = ch.find(f"{{{MC_NS}}}Choice")
            if choice is not None:
                _walk_inline(choice, kind, attrs, out, rpr_changes, nested)
        elif tag in (w("pPr"), w("bookmarkStart"), w("bookmarkEnd"), w("proofErr"), w("commentRangeStart"), w("commentRangeEnd")):
            continue
        else:
            _walk_inline(ch, kind, attrs, out, rpr_changes, nested)


def _merge(segs: list[Segment]) -> list[Segment]:
    out: list[Segment] = []
    for s in segs:
        if out and out[-1].kind == s.kind and out[-1].rev_id == s.rev_id:
            out[-1].text += s.text
        elif s.text or not out:
            out.append(Segment(s.kind, s.text, s.rev_id, s.author, s.date))
        else:
            out.append(Segment(s.kind, s.text, s.rev_id, s.author, s.date))
    return [s for s in out if s.text]


def _paragraph(p: ET.Element, path: str, nested: list) -> Paragraph:
    segs: list[Segment] = []
    rpr_changes = [0]
    _walk_inline(p, "eq", (None, None, None), segs, rpr_changes, nested)
    mark = "kept"
    ppr_change = False
    style = None
    ppr = p.find(w("pPr"))
    if ppr is not None:
        st = ppr.find(w("pStyle"))
        style = st.get(w("val")) if st is not None else None
        ppr_change = ppr.find(w("pPrChange")) is not None
        rpr = ppr.find(w("rPr"))
        if rpr is not None:
            if rpr.find(w("ins")) is not None:
                mark = "ins"
            elif rpr.find(w("del")) is not None:
                mark = "del"
    return Paragraph(path, _merge(segs), mark, ppr_change, rpr_changes[0], style)


def _walk_block(container: ET.Element, prefix: str, out: list[Paragraph]) -> None:
    pi = ti = 0
    for ch in container:
        tag = ch.tag
        if tag == w("p"):
            nested: list = []
            out.append(_paragraph(ch, f"{prefix}p[{pi}]", nested))
            for k, tx in enumerate(nested):
                _walk_block(tx, f"{prefix}p[{pi}]/txbx[{k}]/", out)
            pi += 1
        elif tag == w("tbl"):
            ri = 0
            for tr in ch.findall(w("tr")):
                ci = 0
                for tc in tr.findall(w("tc")):
                    _walk_block(tc, f"{prefix}tbl[{ti}]/tr[{ri}]/tc[{ci}]/", out)
                    ci += 1
                ri += 1
            ti += 1
        elif tag in (w("sdt"), w("sdtContent"), w("customXml")) or tag in REV_WRAPPERS:
            _walk_block(ch, prefix, out)
        elif tag == w("sectPr"):
            continue


def paragraphs(path: Path) -> list[Paragraph]:
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    body = root.find(w("body"))
    out: list[Paragraph] = []
    _walk_block(body, "", out)
    return out


# ── Positions ──────────────────────────────────────────────────────────────────


@dataclass
class Revision:
    path: str
    kind: str
    text: str
    rev_id: str | None
    author: str | None
    orig_char: tuple[int, int] | None  # [start, end) in the original stream, para-local
    rev_char: tuple[int, int] | None  # [start, end) in the revised stream, para-local
    orig_char_doc: tuple[int, int] | None
    rev_char_doc: tuple[int, int] | None
    orig_word: tuple[int, int] | None  # word indices (non-whitespace units), para-local
    rev_word: tuple[int, int] | None
    words: int


def _word_index_at(units: list[Unit], char: int) -> int:
    """Number of word units that END at or before `char`."""
    return sum(1 for u in units if u.kind == "w" and u.end <= char)


def positions(paras: list[Paragraph]) -> list[Revision]:
    out: list[Revision] = []
    doc_o = doc_r = 0
    for p in paras:
        o_units = tokenize(p.text("orig"))
        r_units = tokenize(p.text("rev"))
        po = pr = 0
        for s in p.segments:
            n = len(s.text)
            if s.kind == "eq":
                po += n
                pr += n
                continue
            on_orig = s.kind in ("del", "moveFrom")
            on_rev = s.kind in ("ins", "moveTo")
            units = o_units if on_orig else r_units
            cur = po if on_orig else pr
            wi = (_word_index_at(units, cur), _word_index_at(units, cur + n))
            out.append(
                Revision(
                    p.path, s.kind, s.text, s.rev_id, s.author,
                    (po, po + n) if on_orig else None,
                    (pr, pr + n) if on_rev else None,
                    (doc_o + po, doc_o + po + n) if on_orig else None,
                    (doc_r + pr, doc_r + pr + n) if on_rev else None,
                    wi if on_orig else None,
                    wi if on_rev else None,
                    len(words(s.text)),
                )
            )
            if on_orig:
                po += n
            else:
                pr += n
        if p.mark != "kept":
            out.append(Revision(p.path, f"mark-{p.mark}", "¶", None, None, (po, po), (pr, pr), (doc_o + po, doc_o + po), (doc_r + pr, doc_r + pr), (len(words(p.text("orig"))),) * 2, (len(words(p.text("rev"))),) * 2, 0))
        doc_o += po + 1  # the paragraph mark counts one char in each stream
        doc_r += pr + 1
    return out


# ── Reconstruction and verdicts ────────────────────────────────────────────────


def _story(path: str) -> str:
    return path.rsplit("p[", 1)[0]


def rebuild(paras: list[Paragraph], side: str) -> list[tuple[str, list[int]]]:
    """Paragraph texts of one side, joining across marks absent on that side.
    Returns (text, [redline paragraph indices that fed it])."""
    out: list[tuple[str, list[int]]] = []
    cur, members, story = "", [], None
    for i, p in enumerate(paras):
        st = _story(p.path)
        if story is not None and st != story and members:
            out.append((cur, members))
            cur, members = "", []
        story = st
        cur += p.text(side)
        members.append(i)
        absent = (side == "orig" and p.mark == "ins") or (side == "rev" and p.mark == "del")
        if not absent:
            out.append((cur, members))
            cur, members = "", []
    if members:
        out.append((cur, members))
    return out


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFKC", t)
    t = t.replace("‘", "'").replace("’", "'").replace("“", '"').replace("”", '"')
    t = t.replace(" ", " ")
    return re.sub(r"[ \t]+", " ", t).strip()


def identity(rebuilt: list[tuple[str, list[int]]], source: list[Paragraph]) -> dict:
    src = [p.text("rev") for p in source]  # a plain docx has only eq segments
    got = [t for t, _ in rebuilt]
    exact = got == src
    mism = []
    if not exact:
        for i, (a, b) in enumerate(zip(got, src)):
            if a != b:
                k = next((j for j, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
                mism.append({"para": i, "char": k, "rebuilt": a[max(0, k - 20):k + 20], "source": b[max(0, k - 20):k + 20], "normalized_equal": _norm(a) == _norm(b)})
                if len(mism) >= 10:
                    break
    return {"exact": exact, "paragraphs_rebuilt": len(got), "paragraphs_source": len(src), "normalized_equal": [_norm(t) for t in got] == [_norm(t) for t in src], "mismatches": mism}


@dataclass
class Verdict:
    index: int
    path: str
    verdict: str  # unchanged word-level replaced inserted deleted mark-only
    a_index: int | None
    b_index: int | None
    a_words: int
    b_words: int
    ins: int
    dele: int
    islands: int
    one_word_islands: int
    partner: int | None = None  # for replaced: the redline paragraph it pairs with
    block: str | None = None  # "m×n" replaced block it belongs to


def verdicts(paras: list[Paragraph]) -> list[Verdict]:
    orig = rebuild(paras, "orig")
    rev = rebuild(paras, "rev")
    a_of = {i: k for k, (_, ms) in enumerate(orig) for i in ms}
    b_of = {i: k for k, (_, ms) in enumerate(rev) for i in ms}
    out: list[Verdict] = []
    for i, p in enumerate(paras):
        kinds = {s.kind for s in p.segments if s.text.strip()}
        has_eq = "eq" in kinds
        has_ins = bool(kinds & {"ins", "moveTo"})
        has_del = bool(kinds & {"del", "moveFrom"})
        ins = sum(1 for s in p.segments if s.kind in ("ins", "moveTo"))
        dele = sum(1 for s in p.segments if s.kind in ("del", "moveFrom"))
        isl = [len(words(s.text)) for j, s in enumerate(p.segments) if s.kind == "eq" and 0 < j < len(p.segments) - 1]
        aw, bw = len(words(p.text("orig"))), len(words(p.text("rev")))
        if has_eq and (has_ins or has_del):
            v = "word-level"
        elif has_ins and has_del:
            v = "replaced"
        elif has_ins:
            v = "inserted"
        elif has_del:
            v = "deleted"
        elif p.mark != "kept" or p.ppr_change or p.rpr_changes:
            v = "mark-only"
        else:
            v = "unchanged"
        out.append(Verdict(i, p.path, v, a_of.get(i) if (aw or v in ("deleted",)) else None, b_of.get(i) if (bw or v == "inserted") else None, aw, bw, ins, dele, len(isl), sum(1 for x in isl if x == 1)))
    # whole replacements: a run of inserted paragraphs adjacent to a run of deleted ones (either order)
    i = 0
    while i < len(out):
        if out[i].verdict in ("inserted", "deleted"):
            j = i
            while j < len(out) and out[j].verdict == out[i].verdict:
                j += 1
            k = j
            other = "deleted" if out[i].verdict == "inserted" else "inserted"
            while k < len(out) and out[k].verdict == other:
                k += 1
            if k > j:
                first, second = out[i:j], out[j:k]
                ins_run, del_run = (first, second) if out[i].verdict == "inserted" else (second, first)
                block = f"{len(ins_run)}×{len(del_run)}"
                for n, d in enumerate(del_run):
                    d.block = block
                    d.verdict = "replaced"
                    if n < len(ins_run):
                        d.partner = ins_run[n].index
                        d.b_index = ins_run[n].b_index
                for n, s in enumerate(ins_run):
                    s.block = block
                    s.verdict = "replaced"
                    if n < len(del_run):
                        s.partner = del_run[n].index
                        s.a_index = del_run[n].a_index
                i = k
                continue
            i = j
            continue
        i += 1
    return out


# ── Features ───────────────────────────────────────────────────────────────────


def lcs_len(a: list[str], b: list[str]) -> int:
    if not a or not b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    prev = [0] * (len(b) + 1)
    for x in a:
        cur = [0]
        app = cur.append
        for j, y in enumerate(b):
            app(prev[j] + 1 if x == y else (prev[j + 1] if prev[j + 1] > cur[j] else cur[j]))
        prev = cur
    return prev[-1]


def longest_run(a: list[str], b: list[str]) -> int:
    best = 0
    prev = [0] * (len(b) + 1)
    for x in a:
        cur = [0] * (len(b) + 1)
        for j, y in enumerate(b):
            if x == y:
                cur[j + 1] = prev[j] + 1
                if cur[j + 1] > best:
                    best = cur[j + 1]
        prev = cur
    return best


def shared_ngrams(a: list[str], b: list[str], n: int) -> tuple[int, int]:
    ga = Counter(tuple(a[i:i + n]) for i in range(len(a) - n + 1))
    gb = Counter(tuple(b[i:i + n]) for i in range(len(b) - n + 1))
    inter = ga & gb
    return len(inter), sum(inter.values())


SENT_SPLIT = re.compile(r"(?<=[.?!])\s+|[\n\f]+")


def sentences(text: str) -> list[str]:
    return [s.strip() for s in SENT_SPLIT.split(text) if s.strip()]


def sentence_matches(sa: list[str], sb: list[str], thresh: float) -> int:
    j0, n = 0, 0
    for s in sa:
        ws = words(s.lower())
        best = (0.0, 0)
        for k, t in enumerate(sb[j0:j0 + 8]):
            r = difflib.SequenceMatcher(None, ws, words(t.lower()), autojunk=False).ratio()
            if r > best[0]:
                best = (r, k)
        if best[0] >= thresh:
            n += 1
            j0 += best[1] + 1
    return n


def pair_features(ta: str, tb: str) -> dict:
    a, b = words(ta), words(tb)  # case-sensitive, like Word (see predict_pair)
    ca, cb = Counter(a), Counter(b)
    sa_, sb_ = set(a), set(b)
    la, lb = len(a), len(b)
    longer, shorter = max(la, lb, 1), max(min(la, lb), 1)
    lcs = lcs_len(a, b)
    run = longest_run(a, b)
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    blocks = [bl for bl in sm.get_matching_blocks() if bl.size]
    cov = lambda k: sum(bl.size for bl in blocks if bl.size >= k) / longer
    multiset = sum((ca & cb).values())
    cos = sum(ca[t] * cb[t] for t in ca) / (math.sqrt(sum(v * v for v in ca.values())) * math.sqrt(sum(v * v for v in cb.values())) or 1)
    sent_a, sent_b = sentences(ta), sentences(tb)
    lines_a, lines_b = [l for l in re.split(r"[\n\f]", ta) if l.strip()], [l for l in re.split(r"[\n\f]", tb) if l.strip()]
    chars = difflib.SequenceMatcher(None, ta, tb, autojunk=False)
    f = {
        "a_words": la, "b_words": lb, "a_chars": len(ta), "b_chars": len(tb),
        "len_ratio": shorter / longer,
        "lcs_words": lcs, "lcs_over_longer": lcs / longer, "lcs_over_shorter": lcs / shorter, "lcs_over_mean": 2 * lcs / (la + lb or 1),
        "longest_run": run, "longest_run_over_longer": run / longer, "longest_run_over_units": run / (2 * longer),
        "cov_ge1": cov(1), "cov_ge2": cov(2), "cov_ge3": cov(3), "cov_ge5": cov(5), "cov_ge8": cov(8),
        "greedy_blocks": len(blocks), "greedy_1w_blocks": sum(1 for bl in blocks if bl.size == 1),
        "greedy_revisions_est": 2 * (len(blocks) + 1),
        "jaccard": len(sa_ & sb_) / (len(sa_ | sb_) or 1), "dice": 2 * len(sa_ & sb_) / ((len(sa_) + len(sb_)) or 1),
        "shared_over_shorter_vocab": len(sa_ & sb_) / (min(len(sa_), len(sb_)) or 1),
        "multiset_over_longer": multiset / longer, "cosine_tf": cos,
        "char_ratio": chars.ratio(),
        "sent_a": len(sent_a), "sent_b": len(sent_b),
        "sent_identical": sum(1 for s in sent_a if s in sent_b),
        "sent_sim50": sentence_matches(sent_a, sent_b, 0.5), "sent_sim60": sentence_matches(sent_a, sent_b, 0.6), "sent_sim75": sentence_matches(sent_a, sent_b, 0.75),
        "lines_a": len(lines_a), "lines_b": len(lines_b), "lines_identical": sum(1 for l in lines_a if l in lines_b),
    }
    for n in (2, 3, 4, 5, 8):
        d, t = shared_ngrams(a, b, n)
        f[f"ngram{n}_distinct"] = d
        f[f"ngram{n}_total_over_longer"] = t / longer
    # alignment-score family: matched words minus a penalty per matched run
    # (g = 1 is exactly the shared-bigram count), over the greedy blocks
    matched = sum(bl.size for bl in blocks)
    for g in (0.5, 1, 2, 3):
        f[f"matches_minus_{g}runs_over_longer"] = max(matched - g * len(blocks), 0) / longer
    f["matches_minus_runs_over_longer"] = f["matches_minus_1runs_over_longer"]
    f["runs_over_longer"] = len(blocks) / longer
    # character-level greedy run coverage (Word's "character level" view)
    cblocks = [bl for bl in chars.get_matching_blocks() if bl.size]
    clonger = max(len(ta), len(tb), 1)
    for k in (1, 3, 6, 10, 15, 25):
        f[f"char_cov_ge{k}"] = sum(bl.size for bl in cblocks if bl.size >= k) / clonger
    f["char_matches_minus_runs"] = max(sum(bl.size for bl in cblocks) - len(cblocks), 0) / clonger
    f["sent_identical_frac"] = f["sent_identical"] / (max(len(sent_a), 1))
    f["sent_sim60_frac"] = f["sent_sim60"] / (max(len(sent_a), 1))
    return f


def features(a_path: Path, b_path: Path, r_path: Path, tool: str | None = None) -> list[dict]:
    pa, pb, pr = paragraphs(a_path), paragraphs(b_path), paragraphs(r_path)
    vs = verdicts(pr)
    long_idx = [v.index for v in vs if v.verdict != "unchanged"]
    rows = []
    n_body = len(vs)
    for v in vs:
        if v.verdict not in ("word-level", "replaced"):
            continue
        if v.verdict == "replaced" and (v.a_index is None or v.b_index is None or v.a_words == 0):
            continue  # the inserted half of a pair is reported through its deleted partner
        if v.a_index is None or v.b_index is None:
            continue
        ta, tb = pa[v.a_index].text("rev") if v.a_index < len(pa) else "", pb[v.b_index].text("rev") if v.b_index < len(pb) else ""
        f = pair_features(ta, tb)
        prev_anchor = next((u for u in reversed(vs[:v.index]) if u.verdict == "unchanged" and u.a_words), None)
        next_anchor = next((u for u in vs[v.index + 1:] if u.verdict == "unchanged" and u.a_words), None)
        f.update({
            "tool": tool or r_path.stem, "redline": r_path.name, "para": v.index, "path": v.path, "a_index": v.a_index, "b_index": v.b_index,
            "verdict": v.verdict, "block": v.block or "", "ins": v.ins, "del": v.dele, "islands": v.islands, "one_word_islands": v.one_word_islands,
            # input-side position (from A), safe for fitting
            "a_paras": len(pa), "a_position_frac": v.a_index / max(len(pa) - 1, 1),
            "a_words_before": sum(len(words(q.text("rev"))) for q in pa[:v.a_index]),
            # redline-side context: describes the OUTPUT, never fit on it
            "r_doc_paras": n_body, "r_position_frac": v.index / max(n_body - 1, 1),
            "r_changed_rank": long_idx.index(v.index) if v.index in long_idx else -1, "r_changed_total": len(long_idx),
            "r_anchor_before": prev_anchor is not None, "r_anchor_after": next_anchor is not None,
            "r_dist_anchor_before": v.index - prev_anchor.index if prev_anchor else -1, "r_dist_anchor_after": next_anchor.index - v.index if next_anchor else -1,
        })
        rows.append(f)
    return rows


# ── Fit ────────────────────────────────────────────────────────────────────────


def fit(rows: list[dict]) -> None:
    rows = [r for r in rows if r["verdict"] in ("word-level", "replaced")]
    if not rows:
        print("no word-level/replaced rows")
        return
    y = [r["verdict"] == "word-level" for r in rows]
    # only input-side features may explain a verdict; r_* and the revision
    # counts describe the redline itself and would leak the answer
    numeric = [k for k in rows[0] if isinstance(_num(rows[0][k]), float) and not k.startswith("r_") and k not in ("para", "a_index", "b_index", "ins", "del", "islands", "one_word_islands")]
    print(f"{len(rows)} pairs: {sum(y)} word-level, {len(y) - sum(y)} replaced\n")
    results = []
    for k in numeric:
        xs = [_num(r[k]) for r in rows]
        best = None
        pts = sorted(set(xs))
        for i in range(len(pts) - 1):
            t = (pts[i] + pts[i + 1]) / 2
            for sign in (1, -1):
                pred = [(x > t) if sign == 1 else (x < t) for x in xs]
                acc = sum(p == q for p, q in zip(pred, y)) / len(y)
                if best is None or acc > best[0]:
                    margin = pts[i + 1] - pts[i]
                    best = (acc, t, sign, margin)
        if best:
            results.append((best[0], k, best[1], best[2], best[3]))
    results.sort(reverse=True)
    print("single-feature stumps (word-level when feature > t, or < t for sign -1):")
    for acc, k, t, sign, margin in results[:25]:
        print(f"  {acc:5.1%}  {k:28} {'>' if sign == 1 else '<'} {t:.4g}   gap {margin:.3g}")
    perfect = [r for r in results if r[0] == 1.0]
    print(f"\n{len(perfect)} feature(s) separate perfectly" + (": " + ", ".join(r[1] for r in perfect) if perfect else ""))
    if not perfect:
        print("two-feature AND rules (both thresholds), best:")
        top = [r[1] for r in results[:12]]
        best2 = []
        for i, k1 in enumerate(top):
            for k2 in top[i + 1:]:
                x1 = [_num(r[k1]) for r in rows]
                x2 = [_num(r[k2]) for r in rows]
                for t1 in sorted(set(x1)):
                    for t2 in sorted(set(x2)):
                        for s1 in (1, -1):
                            for s2 in (1, -1):
                                pred = [((a > t1) if s1 == 1 else (a < t1)) and ((b > t2) if s2 == 1 else (b < t2)) for a, b in zip(x1, x2)]
                                acc = sum(p == q for p, q in zip(pred, y)) / len(y)
                                best2.append((acc, k1, s1, t1, k2, s2, t2))
        best2.sort(reverse=True)
        for acc, k1, s1, t1, k2, s2, t2 in best2[:8]:
            print(f"  {acc:5.1%}  {k1} {'>' if s1 == 1 else '<'} {t1:.4g}  AND  {k2} {'>' if s2 == 1 else '<'} {t2:.4g}")


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# ── Predict (fitted law) ───────────────────────────────────────────────────────

THRESHOLD = 0.12  # kept characters (no spaces) over the longer side's characters; constant 200–4800 words
UNDECIDED = 0.01  # margin inside which the alignment proxy's error decides


def lcs_pairs(a: list[str], b: list[str]) -> set[tuple[int, int]]:
    """One longest common subsequence as (i, j) pairs (dynamic programme, ties to the earlier A index)."""
    n, m = len(a), len(b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        ai = a[i]; row = dp[i]; nxt = dp[i + 1]
        for j in range(m - 1, -1, -1):
            row[j] = nxt[j + 1] + 1 if ai == b[j] else (nxt[j] if nxt[j] >= row[j + 1] else row[j + 1])
    out = set(); i = j = 0
    while i < n and j < m:
        if a[i] == b[j]:
            out.add((i, j)); i += 1; j += 1
        elif dp[i + 1][j] >= dp[i][j + 1]:
            i += 1
        else:
            j += 1
    return out


def heckel_pairs(a: list[str], b: list[str], recurse: bool = True, lo1: int = 0, lo2: int = 0, out: set | None = None) -> set[tuple[int, int]]:
    """Heckel 1978 with recursion into the gaps: link tokens unique to both sides,
    extend each link to adjacent equal tokens both ways, keep the longest
    increasing subsequence, then do the same inside every gap. Of the aligners
    tried, the closest to Word's own matches (precision ≈0.85–1.0, recall ≈0.9–1.0
    on 2026-10-03 probes); plain LCS over-matches shared stopwords by 15–50 %."""
    if out is None:
        out = set()
    ca, cb = Counter(a), Counter(b)
    pos_b = {w: j for j, w in enumerate(b) if cb[w] == 1}
    la: list[int | None] = [None] * len(a)
    lb: list[int | None] = [None] * len(b)
    for i, w in enumerate(a):
        if ca[w] == 1 and w in pos_b:
            la[i] = pos_b[w]; lb[pos_b[w]] = i
    anchors = [i for i, j in enumerate(la) if j is not None]
    for i in anchors:
        j = la[i]; k = 1
        while i + k < len(a) and j + k < len(b) and la[i + k] is None and lb[j + k] is None and a[i + k] == b[j + k]:
            la[i + k] = j + k; lb[j + k] = i + k; k += 1
    for i in reversed(anchors):
        j = la[i]; k = 1
        while i - k >= 0 and j - k >= 0 and la[i - k] is None and lb[j - k] is None and a[i - k] == b[j - k]:
            la[i - k] = j - k; lb[j - k] = i - k; k += 1
    pairs = [(i, j) for i, j in enumerate(la) if j is not None]
    tails: list[int] = []; idx: list[int] = []; back: list[int | None] = [None] * len(pairs)
    for n, (_, j) in enumerate(pairs):
        p = bisect.bisect_left(tails, j)
        if p == len(tails):
            tails.append(j); idx.append(n)
        else:
            tails[p] = j; idx[p] = n
        back[n] = idx[p - 1] if p else None
    mono: list[tuple[int, int]] = []
    n = idx[-1] if idx else None
    while n is not None:
        mono.append(pairs[n]); n = back[n]
    mono.reverse()
    for i, j in mono:
        out.add((lo1 + i, lo2 + j))
    if recurse and mono:
        bounds = [(-1, -1)] + mono + [(len(a), len(b))]
        for (i0, j0), (i1, j1) in zip(bounds, bounds[1:]):
            if i1 - i0 > 1 and j1 - j0 > 1:
                heckel_pairs(a[i0 + 1:i1], b[j0 + 1:j1], True, lo1 + i0 + 1, lo2 + j0 + 1, out)
    return out


def predict_pair(ta: str, tb: str) -> dict:
    """Word's whole-paragraph-vs-word-level verdict for one paragraph pair.

    Rule (probes 2026-10-03, waves 1–8): Word word-diffs the pair when the
    characters of the words its alignment keeps, over the characters of the
    longer side (spaces included in the denominator only), reach THRESHOLD;
    otherwise it deletes and inserts the whole paragraph. No length term, no
    run-count term, no sentence step, no context. Case-sensitive: a word whose
    case changed is an edit. The alignment is Word's own and is approximated
    here by recursive Heckel; the margin says how much that approximation
    can be trusted."""
    a = words(ta)
    b = words(tb)
    s = heckel_pairs(a, b)
    l = lcs_pairs(a, b)
    max_chars = max(len(ta), len(tb), 1)
    kept_chars = sum(len(a[i]) for i, _ in s)
    runs = sum(1 for i, j in s if (i - 1, j - 1) not in s)
    frac = kept_chars / max_chars
    lcs_frac = sum(len(a[i]) for i, _ in l) / max_chars
    return {"a_words": len(a), "b_words": len(b), "max_chars": max_chars, "kept_chars": kept_chars, "kept_frac": frac, "runs": runs,
            "lcs_kept_frac": lcs_frac, "floor": THRESHOLD, "margin": frac - THRESHOLD, "predicted": "word-level" if frac >= THRESHOLD else "replaced"}


def pair_paragraphs(pa: list[Paragraph], pb: list[Paragraph]) -> list[tuple[int, int]]:
    """Pair A and B paragraphs: identical text first (as anchors), then the
    best LCS-ratio candidate within ±3 positions for the rest."""
    ta = [p.text("rev") for p in pa]
    tb = [p.text("rev") for p in pb]
    sm = difflib.SequenceMatcher(None, ta, tb, autojunk=False)
    pairs = []
    ai = bi = 0
    for bl in sm.get_matching_blocks():
        # unmatched stretch ta[ai:bl.a] vs tb[bi:bl.b]
        used = set()
        for i in range(ai, bl.a):
            if not ta[i].strip():
                continue
            best = None
            for j in range(bi, bl.b):
                if j in used or not tb[j].strip() or abs((i - ai) - (j - bi)) > 3:
                    continue
                r = difflib.SequenceMatcher(None, words(ta[i].lower()), words(tb[j].lower()), autojunk=False).ratio()
                if best is None or r > best[0]:
                    best = (r, j)
            if best:
                used.add(best[1]); pairs.append((i, best[1]))
        ai, bi = bl.a + bl.size, bl.b + bl.size
    return pairs


# ── CLI ────────────────────────────────────────────────────────────────────────


def cmd_segments(args) -> None:
    paras = paragraphs(Path(args.redline))
    revs = positions(paras)
    if args.json:
        Path(args.json).write_text(json.dumps({"paragraphs": [asdict(p) for p in paras], "revisions": [asdict(r) for r in revs]}, indent=1, ensure_ascii=False))
    for r in revs:
        o = f"orig[{r.orig_char[0]}:{r.orig_char[1]}] w{r.orig_word}" if r.orig_char else ""
        v = f"rev[{r.rev_char[0]}:{r.rev_char[1]}] w{r.rev_word}" if r.rev_char else ""
        t = r.text.replace("\n", "⏎").replace("\t", "⇥")
        print(f"{r.path:18} {r.kind:9} {o:28} {v:28} {r.words:4}w  {t[:60]!r}")
    print(f"\n{len(paras)} paragraphs, {len(revs)} revisions", file=sys.stderr)


def cmd_verdicts(args) -> None:
    pa, pb, pr = paragraphs(Path(args.a)), paragraphs(Path(args.b)), paragraphs(Path(args.redline))
    ia, ib = identity(rebuild(pr, "orig"), pa), identity(rebuild(pr, "rev"), pb)
    vs = verdicts(pr)
    print(f"original rebuilt == A: exact={ia['exact']} normalized={ia['normalized_equal']} ({ia['paragraphs_rebuilt']} vs {ia['paragraphs_source']} paragraphs)")
    print(f"revision rebuilt == B: exact={ib['exact']} normalized={ib['normalized_equal']} ({ib['paragraphs_rebuilt']} vs {ib['paragraphs_source']} paragraphs)")
    for side, info in (("A", ia), ("B", ib)):
        for mm in info["mismatches"]:
            print(f"  {side} para {mm['para']} char {mm['char']}: rebuilt {mm['rebuilt']!r} vs source {mm['source']!r}" + (" (equal after normalization)" if mm["normalized_equal"] else ""))
    print()
    counts = Counter(v.verdict for v in vs)
    print("  ".join(f"{k}={n}" for k, n in sorted(counts.items())))
    for v in vs:
        if v.verdict == "unchanged" and not args.all:
            continue
        ab = f"A{v.a_index if v.a_index is not None else '-'}→B{v.b_index if v.b_index is not None else '-'}"
        extra = f" partner=p{v.partner} block={v.block}" if v.partner is not None else ""
        print(f"  p{v.index:<4} {v.path:16} {v.verdict:10} {ab:10} A={v.a_words:4}w B={v.b_words:4}w ins={v.ins:3} del={v.dele:3} islands={v.islands:3} 1w={v.one_word_islands:3}{extra}")
    if args.json:
        Path(args.json).write_text(json.dumps({"identity_a": ia, "identity_b": ib, "verdicts": [asdict(v) for v in vs]}, indent=1, ensure_ascii=False))


def cmd_features(args) -> None:
    rows = features(Path(args.a), Path(args.b), Path(args.redline), args.tool)
    keys = ["tool", "redline", "para", "path", "a_index", "b_index", "verdict", "block", "ins", "del", "islands", "one_word_islands"]
    keys += [k for k in (rows[0] if rows else {}) if k not in keys]
    if args.csv:
        p = Path(args.csv)
        new = not p.exists() or p.stat().st_size == 0
        with p.open("a", newline="") as fh:
            wr = csv.DictWriter(fh, fieldnames=keys)
            if new:
                wr.writeheader()
            wr.writerows(rows)
    for r in rows:
        print(f"p{r['para']:<3} {r['verdict']:10} A={r['a_words']:4}w B={r['b_words']:4}w lcs/longer={r['lcs_over_longer']:.3f} run={r['longest_run']:3} cov≥3={r['cov_ge3']:.3f} jac={r['jaccard']:.3f} sent_id={r['sent_identical']:2} sim60={r['sent_sim60']:2} greedy={r['greedy_blocks']:3} m-r={r['matches_minus_runs_over_longer']:.3f} pos={r['a_position_frac']:.2f}")


def cmd_predict(args) -> None:
    pa, pb = paragraphs(Path(args.a)), paragraphs(Path(args.b))
    rows = []
    for i, j in pair_paragraphs(pa, pb):
        r = predict_pair(pa[i].text("rev"), pb[j].text("rev"))
        r.update({"a_index": i, "b_index": j, "a_path": pa[i].path, "b_path": pb[j].path})
        rows.append(r)
        flag = "" if abs(r["margin"]) >= UNDECIDED else f"  (undecided: margin < {UNDECIDED})"
        print(f"A{i}→B{j} {r['predicted']:10} kept={r['kept_frac']:.3f} (lcs {r['lcs_kept_frac']:.3f}) threshold={r['floor']:.2f} margin={r['margin']:+.3f} runs={r['runs']} chars={r['max_chars']} words={r['a_words']}/{r['b_words']}{flag}")
    if args.csv and rows:
        p = Path(args.csv)
        new = not p.exists() or p.stat().st_size == 0
        with p.open("a", newline="") as fh:
            wr = csv.DictWriter(fh, fieldnames=list(rows[0]))
            if new:
                wr.writeheader()
            wr.writerows(rows)


def cmd_fit(args) -> None:
    rows: list[dict] = []
    for f in args.csv:
        with open(f, newline="") as fh:
            rows.extend(csv.DictReader(fh))
    fit(rows)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("segments"); s.add_argument("redline"); s.add_argument("--json"); s.set_defaults(fn=cmd_segments)
    v = sub.add_parser("verdicts"); v.add_argument("a"); v.add_argument("b"); v.add_argument("redline"); v.add_argument("--json"); v.add_argument("--all", action="store_true"); v.set_defaults(fn=cmd_verdicts)
    f = sub.add_parser("features"); f.add_argument("a"); f.add_argument("b"); f.add_argument("redline"); f.add_argument("--csv"); f.add_argument("--tool"); f.set_defaults(fn=cmd_features)
    t = sub.add_parser("fit"); t.add_argument("csv", nargs="+"); t.set_defaults(fn=cmd_fit)
    p = sub.add_parser("predict"); p.add_argument("a"); p.add_argument("b"); p.add_argument("--csv"); p.set_defaults(fn=cmd_predict)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()

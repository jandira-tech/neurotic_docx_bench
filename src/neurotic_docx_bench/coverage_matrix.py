"""Feature-coverage matrix over the corpus (PR10).

Tags every corpus pair with (a) the OOXML *features* present in its two source
documents (tables, footnotes, images, CJK text, …) and (b) the *revision*
constructs present in its oracle redline (w:ins, w:del, moveFrom/moveTo, …).
The output answers "which strata does the corpus actually exercise?" — the
``zero_coverage`` list names every known tag with no pair behind it — and,
joined with bench JSONL scores, "how does each vendor do per stratum?".

Pure stdlib (zipfile + xml.etree): tagging reads the package XML directly, no
render pipeline involved.
"""

from __future__ import annotations

import csv
import json
import statistics
import zipfile
from pathlib import Path
from xml.etree import ElementTree

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_MC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"
_M = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"

KNOWN_FEATURES = frozenset({
    "table",
    "nested_table",
    "footnote",
    "endnote",
    "numbering",
    "multi_section",
    "header",
    "footer",
    "image",
    "textbox",
    "content_control",
    "alternate_content",
    "field",
    "math",
    "hyperlink",
    "cjk",
    "rtl",
})

KNOWN_REVISIONS = frozenset({
    "rev_ins",
    "rev_del",
    "rev_rPrChange",
    "rev_pPrChange",
    "rev_tblChange",
    "rev_tblPrChange",
    "rev_tblGridChange",
    "rev_trPrChange",
    "rev_tcPrChange",
    "rev_moveFrom",
    "rev_moveTo",
    "rev_sectPrChange",
    "rev_numberingChange",
})

# Direct element → feature tag (structure-independent features).
_FEATURE_ELEMENTS = {
    _W + "tbl": "table",
    _W + "numPr": "numbering",
    _W + "drawing": "image",
    _W + "pict": "image",
    _W + "txbxContent": "textbox",
    _W + "sdt": "content_control",
    _MC + "AlternateContent": "alternate_content",
    _W + "fldSimple": "field",
    _W + "instrText": "field",
    _M + "oMath": "math",
    _W + "hyperlink": "hyperlink",
    _W + "bidi": "rtl",
    _W + "rtl": "rtl",
}

_REV_ELEMENTS = {
    _W + "ins": "rev_ins",
    _W + "del": "rev_del",
    _W + "rPrChange": "rev_rPrChange",
    _W + "pPrChange": "rev_pPrChange",
    _W + "tblPrChange": "rev_tblPrChange",
    _W + "tblGridChange": "rev_tblGridChange",
    _W + "trPrChange": "rev_trPrChange",
    _W + "tcPrChange": "rev_tcPrChange",
    _W + "moveFrom": "rev_moveFrom",
    _W + "moveTo": "rev_moveTo",
    _W + "sectPrChange": "rev_sectPrChange",
    _W + "numberingChange": "rev_numberingChange",
}

_TBL_CHANGE_TAGS = frozenset({"rev_tblPrChange", "rev_tblGridChange", "rev_trPrChange", "rev_tcPrChange"})

# w:footnote/w:endnote separator stubs are plumbing, not authored notes.
_SEPARATOR_TYPES = frozenset({"separator", "continuationSeparator"})

_CJK_RANGES = (
    (0x3400, 0x4DBF),  # CJK Unified Ideographs Extension A
    (0x4E00, 0x9FFF),  # CJK Unified Ideographs
    (0xF900, 0xFAFF),  # CJK Compatibility Ideographs
    (0x20000, 0x2A6DF),  # Extension B
    (0x2A700, 0x2EBEF),  # Extensions C–F
)

_RTL_RANGES = (
    (0x0590, 0x05FF),  # Hebrew
    (0x0600, 0x06FF),  # Arabic
    (0x0750, 0x077F),  # Arabic Supplement
    (0x08A0, 0x08FF),  # Arabic Extended-A
    (0xFB1D, 0xFDFF),  # Hebrew/Arabic presentation forms A
    (0xFE70, 0xFEFF),  # Arabic presentation forms B
)


def _has_char_in(text: str, ranges: tuple[tuple[int, int], ...]) -> bool:
    return any(any(lo <= ord(ch) <= hi for lo, hi in ranges) for ch in text)


def _story_parts(names: list[str], *, include_notes: bool) -> list[str]:
    """Package parts carrying document content: the main story, headers/footers,
    and (for source tagging) footnotes/endnotes."""
    parts = []
    for name in sorted(names):
        base = name.rsplit("/", 1)[-1]
        if name == "word/document.xml":
            parts.append(name)
        elif include_notes and name in ("word/footnotes.xml", "word/endnotes.xml"):
            parts.append(name)
        elif name.startswith("word/header") and name.endswith(".xml"):
            parts.append(name)
        elif name.startswith("word/footer") and name.endswith(".xml"):
            parts.append(name)
    return parts


def tag_source_docx(path: Path) -> set[str]:
    """Feature tags present anywhere in a source document's story parts."""
    tags: set[str] = set()
    sectpr_count = 0
    with zipfile.ZipFile(path) as zf:
        for name in _story_parts(zf.namelist(), include_notes=True):
            root = ElementTree.fromstring(zf.read(name))
            for el in root.iter():
                feature = _FEATURE_ELEMENTS.get(el.tag)
                if feature is not None:
                    tags.add(feature)
                elif el.tag == _W + "sectPr":
                    sectpr_count += 1
                elif el.tag in (_W + "footnote", _W + "endnote"):
                    if el.get(_W + "type") not in _SEPARATOR_TYPES:
                        tags.add("footnote" if el.tag == _W + "footnote" else "endnote")
            if "table" in tags and "nested_table" not in tags:
                for tbl in root.iter(_W + "tbl"):
                    inner = iter(tbl.iter(_W + "tbl"))
                    next(inner)  # the table itself
                    if next(inner, None) is not None:
                        tags.add("nested_table")
                        break
            text = "".join(root.itertext())
            if _has_char_in(text, _CJK_RANGES):
                tags.add("cjk")
            if _has_char_in(text, _RTL_RANGES):
                tags.add("rtl")
            base = name.rsplit("/", 1)[-1]
            if base.startswith("header") and text.strip():
                tags.add("header")
            elif base.startswith("footer") and text.strip():
                tags.add("footer")
    if sectpr_count > 1:
        tags.add("multi_section")
    return tags


def tag_oracle_revisions(path: Path) -> set[str]:
    """Revision tags present in a redline's main story (+ headers/footers)."""
    tags: set[str] = set()
    with zipfile.ZipFile(path) as zf:
        for name in _story_parts(zf.namelist(), include_notes=False):
            root = ElementTree.fromstring(zf.read(name))
            for el in root.iter():
                rev = _REV_ELEMENTS.get(el.tag)
                if rev is not None:
                    tags.add(rev)
    if tags & _TBL_CHANGE_TAGS:
        tags.add("rev_tblChange")
    return tags


def _resolve(filename: str, dirs: list[Path]) -> Path | None:
    for d in dirs:
        candidate = d / filename
        if candidate.is_file():
            return candidate
    return None


def _resolve_redline(row: dict[str, str], redline_dirs: list[Path]) -> Path:
    """The pair's oracle redline; ``redline_docx_word`` wins when both are listed."""
    names = [
        (row.get(col) or "").strip()
        for col in ("redline_docx_word", "redline_docx")
    ]
    names = [n for n in names if n and not n.startswith("MISSING")]
    if not names:
        raise FileNotFoundError("no redline docx listed in mapping row")
    for name in names:
        found = _resolve(name, redline_dirs)
        if found is not None:
            return found
    raise FileNotFoundError(f"redline not found in {[str(d) for d in redline_dirs]}: {names}")


def build_coverage(
    mapping_csvs: list[Path],
    source_dirs: list[Path],
    redline_docx_dirs: list[Path],
) -> dict:
    """Tag every mapping pair; a broken pair lands in ``errors``, never crashes.

    Feature tags are the union over the pair's two sources; revision tags come
    from its oracle redline.
    """
    pairs: dict[str, dict[str, list[str]]] = {}
    errors: dict[str, str] = {}
    for csv_path in mapping_csvs:
        with csv_path.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                stem = (row.get("pair_stem") or "").strip()
                if not stem:
                    continue
                src_names = [
                    (row.get(col) or "").strip()
                    for col in ("docx_source_base", "docx_source_next")
                ]
                if any(n.startswith("MISSING") for n in src_names):
                    continue
                try:
                    features: set[str] = set()
                    for name in src_names:
                        source = _resolve(name, source_dirs)
                        if source is None:
                            raise FileNotFoundError(
                                f"source not found in {[str(d) for d in source_dirs]}: {name}",
                            )
                        features |= tag_source_docx(source)
                    revisions = tag_oracle_revisions(_resolve_redline(row, redline_docx_dirs))
                except Exception as exc:  # noqa: BLE001 — any broken docx is a data point, not a crash
                    errors[stem] = f"{type(exc).__name__}: {exc}"
                    continue
                pairs[stem] = {"features": sorted(features), "revisions": sorted(revisions)}
    tag_counts = dict.fromkeys(sorted(KNOWN_FEATURES) + sorted(KNOWN_REVISIONS), 0)
    for info in pairs.values():
        for tag in info["features"] + info["revisions"]:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    return {
        "pairs": pairs,
        "tag_counts": tag_counts,
        "zero_coverage": sorted(t for t in KNOWN_FEATURES | KNOWN_REVISIONS if tag_counts.get(t, 0) == 0),
        "errors": errors,
    }


def latest_scores_by_vendor(jsonl_path: Path) -> dict[str, dict[str, float]]:
    """Each vendor's per-doc scores from its LATEST ``script_redlines`` line."""
    by_vendor: dict[str, dict[str, float]] = {}
    with jsonl_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("benchmark") != "script_redlines":
                continue
            vendor = record.get("vendor")
            scores = record.get("scores")
            if isinstance(vendor, str) and isinstance(scores, dict):
                by_vendor[vendor] = {k: float(v) for k, v in scores.items()}
    return by_vendor


def _ordered_tags(tag_counts: dict[str, int]) -> list[str]:
    features = sorted(t for t in tag_counts if t in KNOWN_FEATURES)
    revisions = sorted(t for t in tag_counts if t not in KNOWN_FEATURES)
    return features + revisions


def render_markdown(
    coverage: dict,
    scores_by_vendor: dict[str, dict[str, float]] | None = None,
) -> str:
    lines = [
        "# Corpus coverage matrix",
        "",
        f"{len(coverage['pairs'])} pairs tagged, {len(coverage.get('errors', {}))} errors.",
        "",
        "## Tag coverage",
        "",
        "| Tag | Kind | Pairs |",
        "| --- | --- | ---: |",
    ]
    tag_counts = coverage["tag_counts"]
    for tag in _ordered_tags(tag_counts):
        kind = "feature" if tag in KNOWN_FEATURES else "revision"
        count = tag_counts[tag]
        lines.append(f"| `{tag}` | {kind} | {'**0**' if count == 0 else count} |")
    lines += ["", "## Zero coverage", ""]
    zero = coverage.get("zero_coverage", [])
    if zero:
        lines += [f"- `{tag}`" for tag in zero]
    else:
        lines.append("(none — every known tag has at least one pair)")
    if scores_by_vendor:
        vendors = sorted(scores_by_vendor)
        lines += [
            "",
            "## Median score per tag per vendor",
            "",
            "Scores join pairs to each vendor's latest `script_redlines` line by pair stem;",
            "`n` is how many of the tag's pairs that vendor scored.",
            "",
            "| Tag | " + " | ".join(vendors) + " |",
            "| --- |" + " ---: |" * len(vendors),
        ]
        stems_by_tag: dict[str, list[str]] = {}
        for stem, info in coverage["pairs"].items():
            for tag in info["features"] + info["revisions"]:
                stems_by_tag.setdefault(tag, []).append(stem)
        for tag in _ordered_tags(tag_counts):
            cells = []
            for vendor in vendors:
                scores = scores_by_vendor[vendor]
                values = [scores[s] for s in stems_by_tag.get(tag, []) if s in scores]
                cells.append(f"{statistics.median(values):.1f} (n={len(values)})" if values else "—")
            lines.append(f"| `{tag}` | " + " | ".join(cells) + " |")
    lines.append("")
    return "\n".join(lines)

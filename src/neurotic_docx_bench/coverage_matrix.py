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
import math
import statistics
import zipfile
from pathlib import Path
from xml.etree import ElementTree

# Both OOXML namespace families: Transitional (schemas.openxmlformats.org) and
# Strict (purl.oclc.org) — the corpus contains documents in each. Every element
# test probes both; mc: is identical in the two families.
_W_NSES = (
    "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}",
    "{http://purl.oclc.org/ooxml/wordprocessingml/main}",
)
_M_NSES = (
    "{http://schemas.openxmlformats.org/officeDocument/2006/math}",
    "{http://purl.oclc.org/ooxml/officeDocument/math}",
)
_MC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"

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
_FEATURE_LOCALS = {
    "tbl": "table",
    "numPr": "numbering",
    "drawing": "image",
    "pict": "image",
    "txbxContent": "textbox",
    "sdt": "content_control",
    "fldSimple": "field",
    "instrText": "field",
    "hyperlink": "hyperlink",
}
_FEATURE_ELEMENTS = {w + local: tag for w in _W_NSES for local, tag in _FEATURE_LOCALS.items()}
_FEATURE_ELEMENTS[_MC + "AlternateContent"] = "alternate_content"
_FEATURE_ELEMENTS.update({m + "oMath": "math" for m in _M_NSES})

_REV_LOCALS = {
    "ins": "rev_ins",
    "del": "rev_del",
    "rPrChange": "rev_rPrChange",
    "pPrChange": "rev_pPrChange",
    "tblPrChange": "rev_tblPrChange",
    "tblGridChange": "rev_tblGridChange",
    "trPrChange": "rev_trPrChange",
    "tcPrChange": "rev_tcPrChange",
    "moveFrom": "rev_moveFrom",
    "moveTo": "rev_moveTo",
    "sectPrChange": "rev_sectPrChange",
    "numberingChange": "rev_numberingChange",
}
_REV_ELEMENTS = {w + local: tag for w in _W_NSES for local, tag in _REV_LOCALS.items()}

_TBL_TAGS = frozenset(w + "tbl" for w in _W_NSES)
_SECTPR_TAGS = frozenset(w + "sectPr" for w in _W_NSES)
_FOOTNOTE_TAGS = frozenset(w + "footnote" for w in _W_NSES)
_ENDNOTE_TAGS = frozenset(w + "endnote" for w in _W_NSES)
# w:bidi / w:rtl are on/off properties — presence alone does not mean RTL.
_RTL_PROP_TAGS = frozenset(w + local for w in _W_NSES for local in ("bidi", "rtl"))
_TYPE_ATTRS = tuple(w + "type" for w in _W_NSES)
_VAL_ATTRS = tuple(w + "val" for w in _W_NSES)

_TBL_CHANGE_TAGS = frozenset({"rev_tblPrChange", "rev_tblGridChange", "rev_trPrChange", "rev_tcPrChange"})

# w:footnote/w:endnote separator stubs are plumbing, not authored notes.
_SEPARATOR_TYPES = frozenset({"separator", "continuationSeparator", "continuationNotice"})

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


def _attr(el: ElementTree.Element, attrs: tuple[str, ...]) -> str | None:
    """First present attribute value, probing each namespace family's name."""
    for attr in attrs:
        val = el.get(attr)
        if val is not None:
            return val
    return None


def _onoff_enabled(el: ElementTree.Element) -> bool:
    """OOXML on/off convention: w:val absent, 1, true, or on means ON;
    0, false, or off means explicitly OFF."""
    val = _attr(el, _VAL_ATTRS)
    return val is None or val.strip().lower() not in ("0", "false", "off")


def _story_parts(names: list[str], *, include_notes: bool) -> list[str]:
    """Package parts carrying document content: the main story, headers/footers,
    and (for source tagging) footnotes/endnotes."""
    parts = []
    for name in sorted(names):
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
                elif el.tag in _RTL_PROP_TAGS:
                    if _onoff_enabled(el):
                        tags.add("rtl")
                elif el.tag in _SECTPR_TAGS:
                    sectpr_count += 1
                elif el.tag in _FOOTNOTE_TAGS or el.tag in _ENDNOTE_TAGS:
                    if _attr(el, _TYPE_ATTRS) not in _SEPARATOR_TYPES:
                        tags.add("footnote" if el.tag in _FOOTNOTE_TAGS else "endnote")
            if "table" in tags and "nested_table" not in tags:
                for tbl in root.iter():
                    if tbl.tag not in _TBL_TAGS:
                        continue
                    inner = (el for el in tbl.iter() if el.tag in _TBL_TAGS)
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
    """Revision tags present in a redline's main story (+ headers/footers).

    Footnote/endnote parts are not scanned — revision markup living only inside
    notes is invisible to this tagger."""
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


def _tag_redline_revisions(row: dict[str, str], redline_dirs: list[Path]) -> set[str]:
    """Revision tags from the pair's oracle redline; ``redline_docx_word`` wins
    when both are listed, but a preferred file that is absent OR fails to tag
    (corrupt zip, malformed XML) falls back to the next candidate. Raises only
    when every candidate fails, naming each one's failure."""
    names = [
        (row.get(col) or "").strip()
        for col in ("redline_docx_word", "redline_docx")
    ]
    names = [n for n in names if n and not n.startswith("MISSING")]
    if not names:
        raise FileNotFoundError("no redline docx listed in mapping row")
    failures = []
    for name in names:
        found = _resolve(name, redline_dirs)
        if found is None:
            failures.append(f"{name}: not found in {[str(d) for d in redline_dirs]}")
            continue
        try:
            return tag_oracle_revisions(found)
        except Exception as exc:  # noqa: BLE001 — try the next candidate before giving up
            failures.append(f"{name}: {type(exc).__name__}: {exc}")
    raise RuntimeError("all redline candidates failed — " + "; ".join(failures))


def build_coverage(
    mapping_csvs: list[Path],
    source_dirs: list[Path],
    redline_docx_dirs: list[Path],
) -> dict:
    """Tag every mapping pair; a broken pair lands in ``errors``, never crashes.

    Feature tags are the union over the pair's two sources; revision tags come
    from its oracle redline. Rows whose source column says MISSING are not
    errors but still accounted for, in ``skipped``.
    """
    pairs: dict[str, dict[str, list[str]]] = {}
    errors: dict[str, str] = {}
    skipped: dict[str, str] = {}
    total_rows = 0
    for csv_path in mapping_csvs:
        with csv_path.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                stem = (row.get("pair_stem") or "").strip()
                if not stem:
                    continue
                total_rows += 1
                src_names = [
                    (row.get(col) or "").strip()
                    for col in ("docx_source_base", "docx_source_next")
                ]
                missing = [n for n in src_names if n.startswith("MISSING")]
                if missing:
                    skipped[stem] = f"MISSING source: {', '.join(missing)}"
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
                    revisions = _tag_redline_revisions(row, redline_docx_dirs)
                except Exception as exc:  # noqa: BLE001 — any broken docx is a data point, not a crash
                    errors[stem] = f"{type(exc).__name__}: {exc}"
                    continue
                pairs[stem] = {"features": sorted(features), "revisions": sorted(revisions)}
    assert len(pairs) + len(errors) + len(skipped) == total_rows, (
        f"accounting broken: {len(pairs)} tagged + {len(errors)} errors + "
        f"{len(skipped)} skipped != {total_rows} mapping rows (duplicate pair stems?)"
    )
    tag_counts = dict.fromkeys(sorted(KNOWN_FEATURES) + sorted(KNOWN_REVISIONS), 0)
    for info in pairs.values():
        for tag in info["features"] + info["revisions"]:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    return {
        "pairs": pairs,
        "tag_counts": tag_counts,
        "zero_coverage": sorted(t for t in KNOWN_FEATURES | KNOWN_REVISIONS if tag_counts.get(t, 0) == 0),
        "errors": errors,
        "skipped": skipped,
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
                clean: dict[str, float] = {}
                for k, v in scores.items():
                    try:
                        num = float(v)
                    except (TypeError, ValueError):
                        continue
                    if math.isfinite(num):
                        clean[str(k)] = num
                # Always assign so a later all-invalid line clears a stale vendor map.
                by_vendor[vendor] = clean
    return by_vendor


def unjoined_score_keys(coverage: dict, scores_by_vendor: dict[str, dict[str, float]]) -> dict[str, list[str]]:
    """Per vendor, the score keys that match no tagged pair stem.

    These keys (e.g. ``<stem>_word`` variants, case mismatches) are excluded
    from every per-tag ``n`` — surfacing them keeps the join honest. No fuzzy
    matching: suffix-stripping collides on real corpora. Score keys are
    lowercased for the join (pipeline canonicalization)."""
    pairs_lower = {str(s).lower() for s in coverage["pairs"]}
    return {
        vendor: sorted(k for k in scores if str(k).lower() not in pairs_lower)
        for vendor, scores in scores_by_vendor.items()
    }


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
        f"{len(coverage['pairs'])} pairs tagged, {len(coverage.get('errors', {}))} errors, "
        f"{len(coverage.get('skipped', {}))} skipped (MISSING source in mapping).",
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
        # Score keys are pipeline-canonicalized (lowercase); stems keep mapping casing.
        # Local copy — never mutate the caller's scores_by_vendor.
        lower_scores_by_vendor = {
            vendor: {str(k).lower(): v for k, v in scores_by_vendor[vendor].items()}
            for vendor in vendors
        }
        for tag in _ordered_tags(tag_counts):
            cells = []
            for vendor in vendors:
                scores = lower_scores_by_vendor[vendor]
                values = [
                    scores[s.lower()]
                    for s in stems_by_tag.get(tag, [])
                    if s.lower() in scores
                ]
                cells.append(f"{statistics.median(values):.1f} (n={len(values)})" if values else "—")
            lines.append(f"| `{tag}` | " + " | ".join(cells) + " |")
        unjoined = {
            v: keys
            for v, keys in unjoined_score_keys(coverage, lower_scores_by_vendor).items()
            if keys
        }
        if unjoined:
            lines.append("")
            for vendor in sorted(unjoined):
                keys = unjoined[vendor]
                sample = ", ".join(f"`{k}`" for k in keys[:3])
                lines.append(
                    f"- `{vendor}`: {len(keys)} of {len(scores_by_vendor[vendor])} score keys "
                    f"matched no tagged pair and are excluded from `n` (e.g. {sample}).",
                )
    lines.append("")
    return "\n".join(lines)

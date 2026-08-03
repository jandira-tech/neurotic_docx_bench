"""Functional accept/reject invariant (PLAN robustness stack, PR7).

The pixel lens cannot tell a real tracked change from paint: a candidate that
emits final text styled red-with-strikethrough (no ``w:ins``/``w:del``) renders
near-identically to a true redline. The functional lens closes that hole with the
defining property of a redline: **accept(candidate) must equal the next document,
reject(candidate) must equal the base document** — judged by the bench's own
neutral machinery (``accept_changes`` / docx-revisions), never the tool's own
accept, which would mask the tool's own defects.

Equality is two-level because ``accept_changes`` has a documented limitation
(accepting a deleted paragraph mark removes the marker but does not merge the
paragraphs — accept_changes.py). ``*_strict`` compares paragraph lists verbatim;
the headline ``*_ok`` compares whitespace-collapsed joined text, tolerant of that
paragraph-split residue.
"""

from __future__ import annotations

import csv
import zipfile
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

from neurotic_docx_bench import accept_changes

_MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"
_FALLBACK = f"{{{_MC_NS}}}Fallback"


@dataclass(frozen=True)
class FunctionalVerdict:
    """``None`` fields mean the check could not run (see ``error``), not a fail.

    ``blind`` = base and next carry IDENTICAL text (formatting-only pair), so the
    text lens has zero discriminating power on this doc — the flags are still
    computed but carry no signal, and aggregate counts exclude blind docs.
    """

    accept_ok: bool | None
    reject_ok: bool | None
    accept_strict: bool | None
    reject_strict: bool | None
    error: str | None = None
    blind: bool = False


def extract_body_text(docx: Path | str) -> list[str]:
    """Visible body text per paragraph: ``w:p`` → concatenated ``w:t`` runs
    (``w:delText`` is deleted content and never counts), empty paragraphs dropped.

    Only TOP-LEVEL paragraphs count: a text box (``w:txbxContent``) nests its own
    ``w:p`` inside a run of an outer ``w:p``, and iterating every ``w:p`` would
    count the boxed text twice (once as descendant of the outer paragraph, once as
    its own). The nested paragraph's text belongs to its outer paragraph.

    The ``w`` namespace is taken from the document root, not hardcoded — Strict
    OOXML uses a different one, and hardcoding transitional silently extracted []
    for strict corpus docs. ``mc:AlternateContent`` carries the same content in
    Choice AND Fallback; Word renders exactly one, so Fallback is skipped.
    A document with no body raises (callers turn that into an error verdict).
    """
    with zipfile.ZipFile(docx) as zf:
        root = ElementTree.fromstring(zf.read("word/document.xml"))
    tag = root.tag
    if not (tag.startswith("{") and tag.endswith("}document")):
        raise ValueError(f"not a WordprocessingML document root: {tag!r}")
    ns = tag[1 : tag.index("}")]
    p_tag, t_tag = f"{{{ns}}}p", f"{{{ns}}}t"
    body = root.find(f"{{{ns}}}body")
    if body is None:
        raise ValueError("document has no w:body")
    parent = {child: par for par in body.iter() for child in par}

    def has_ancestor(el: ElementTree.Element, ancestor_tag: str) -> bool:
        anc = parent.get(el)
        while anc is not None:
            if anc.tag == ancestor_tag:
                return True
            anc = parent.get(anc)
        return False

    paragraphs = []
    for p in body.iter(p_tag):
        if has_ancestor(p, p_tag) or has_ancestor(p, _FALLBACK):
            continue
        text = "".join(
            t.text or "" for t in p.iter(t_tag) if not has_ancestor(t, _FALLBACK)
        )
        if text.strip():
            paragraphs.append(text)
    return paragraphs


def texts_equal(a: list[str], b: list[str]) -> tuple[bool, bool]:
    """``(strict_ok, text_ok)`` — paragraph lists verbatim vs whitespace-collapsed
    joined text (tolerant of the accept_changes paragraph-merge limitation)."""
    strict = a == b
    text = " ".join(" ".join(a).split()) == " ".join(" ".join(b).split())
    return strict, text


def check_functional(
    candidate: Path | str,
    base: Path | str,
    next_: Path | str,
    workdir: Path | str,
) -> FunctionalVerdict:
    """Accept and reject ``candidate`` with the neutral machinery and compare the
    extracted text against ``next_`` and ``base`` respectively."""
    workdir = Path(workdir)
    try:
        accepted = accept_changes.accept_all(candidate, workdir / "accepted.docx")
        rejected = accept_changes.reject_all(candidate, workdir / "rejected.docx")
        accepted_text = extract_body_text(accepted)
        rejected_text = extract_body_text(rejected)
        next_text = extract_body_text(next_)
        base_text = extract_body_text(base)
    except Exception as exc:  # noqa: BLE001 — any machinery crash is one verdict
        return FunctionalVerdict(None, None, None, None, error=f"{type(exc).__name__}: {exc}")
    if not base_text and not next_text:
        # A vacuously-true invariant (empty ≡ empty) would reward an empty
        # candidate; no text on either side means the lens cannot judge this pair.
        return FunctionalVerdict(
            None, None, None, None, error="both sources extract no body text (lens not applicable)",
        )
    _, blind = texts_equal(base_text, next_text)
    accept_strict, accept_ok = texts_equal(accepted_text, next_text)
    reject_strict, reject_ok = texts_equal(rejected_text, base_text)
    return FunctionalVerdict(accept_ok, reject_ok, accept_strict, reject_strict, None, blind=blind)


CheckTask = tuple[str, Path, Path, Path, Path]
"""``(key, candidate_docx, base_docx, next_docx, workdir)``."""


def _check_one(task: CheckTask) -> tuple[str, FunctionalVerdict]:
    """Worker for :func:`check_folder` — module-level so ProcessPoolExecutor can
    pickle it (same pattern as ``accept_changes._process_one``)."""
    key, candidate, base, next_, workdir = task
    return key, check_functional(candidate, base, next_, workdir)


def check_folder(tasks: list[CheckTask], jobs: int = 12) -> dict[str, FunctionalVerdict]:
    """Run :func:`check_functional` over ``tasks``, in a process pool when jobs > 1."""
    if jobs <= 1 or len(tasks) <= 1:
        return dict(_check_one(t) for t in tasks)
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        return dict(pool.map(_check_one, tasks))


def resolve_source_docx(
    mapping_csvs: list[Path], source_dirs: list[Path]
) -> dict[str, tuple[Path, Path]]:
    """``{pair_stem.lower(): (base_docx, next_docx)}`` for every mapping row whose
    BOTH source documents exist in one of ``source_dirs`` (same key space as
    ``score_v2.resolve_base_pdfs``)."""

    def find(stem: str) -> Path | None:
        for d in source_dirs:
            p = Path(d) / f"{stem}.docx"
            if p.is_file():
                return p
        return None

    resolved: dict[str, tuple[Path, Path]] = {}
    for csv_path in mapping_csvs:
        if not Path(csv_path).is_file():
            continue
        with Path(csv_path).open(encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                pair_stem = (row.get("pair_stem") or "").strip()
                base = (row.get("base") or "").strip()
                next_ = (row.get("next") or "").strip()
                if not pair_stem or not base or not next_:
                    continue
                base_path, next_path = find(base), find(next_)
                if base_path and next_path:
                    resolved[pair_stem.lower()] = (base_path, next_path)
    return resolved

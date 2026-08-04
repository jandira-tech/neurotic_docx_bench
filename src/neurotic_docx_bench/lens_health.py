"""Lens-disagreement bench-health metric (PR8).

Three lenses can judge a script_redlines doc:

- **pixel** — the pagefair overall score (raw overall as fallback);
- **functional** — the PR7 accept/reject invariant (``functional_accept_ok`` AND
  ``functional_reject_ok``; blind docs carry no signal);
- **WV-1** — the PR9 ``bench word-validate --json`` records, merged into per_doc
  as ``wv1_outcome`` when ``results/wv1/<vendor>.json`` exists.

Disagreement per doc: pixel says near-perfect (≥90) but the redline is
functionally inert or Word cannot open it — or pixel says broken (<50) but the
redline functions. Either way the BENCH is measuring the wrong thing on that
doc; the rate is a bench-health alarm, never a tool-ranking input. Docs where
no second lens is present are excluded from the denominator.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

PIXEL_HIGH = 90.0
PIXEL_LOW = 50.0


def _pixel_score(doc: Mapping[str, object]) -> float | None:
    for key in ("overall_score_pagefair", "overall_score"):
        v = doc.get(key)
        if isinstance(v, (int, float)):
            return float(v)
    return None


def _functional_ok(doc: Mapping[str, object]) -> bool | None:
    """True/False = invariant verdict; None = lens absent, crashed, partial, or
    blind (a partial verdict means the check could not run — never a fail)."""
    if doc.get("functional_blind") is True:
        return None
    a = doc.get("functional_accept_ok")
    r = doc.get("functional_reject_ok")
    if a is None or r is None:
        return None
    return bool(a) and bool(r)


def doc_disagreement(doc: Mapping[str, object]) -> bool | None:
    """Per-doc lens conflict; None when not computable.

    A doc enters the denominator only when some rule COULD flag it: a functional
    verdict is two-way, and ``wv1 == "invalid"`` is a positive finding. A
    ``wv1 == "valid"``-only doc has no rule that could ever flag it (Word
    opening a file says nothing about redline correctness), so counting it
    would mechanically dilute the rate as WV-1 coverage grows — excluded.
    ``unjudgeable`` judges nothing.
    """
    pixel = _pixel_score(doc)
    if pixel is None:
        return None
    functional = _functional_ok(doc)
    wv1 = doc.get("wv1_outcome")
    if functional is None and wv1 != "invalid":
        return None
    if functional is not None:
        if pixel >= PIXEL_HIGH and not functional:
            return True
        if pixel < PIXEL_LOW and functional:
            return True
    if wv1 == "invalid":
        if pixel >= PIXEL_HIGH:
            return True
        # Two judging lenses in flat contradiction, whatever the pixel band:
        # the invariant holds but Word cannot even open the file.
        if functional is True:
            return True
    return False


def summarize(
    per_doc: Mapping[str, Mapping[str, object]] | None,
) -> tuple[int | None, float | None]:
    """``(n_lens_disagree, lens_disagree_rate)`` over computable docs;
    ``(None, None)`` when no doc is computable."""
    flags = [
        flag
        for doc in (per_doc or {}).values()
        if isinstance(doc, Mapping) and (flag := doc_disagreement(doc)) is not None
    ]
    if not flags:
        return None, None
    n = sum(flags)
    return n, round(n / len(flags), 4)


def load_wv1_outcomes(path: Path) -> dict[str, str]:
    """``{stem.lower(): outcome}`` from a PR9 ``word-validate --json`` file;
    empty on absent/corrupt (the lens is optional)."""
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text())
        results = data.get("results", {})
    except (json.JSONDecodeError, OSError, AttributeError):
        return {}
    outcomes: dict[str, str] = {}
    if isinstance(results, dict):
        for stem, record in results.items():
            if isinstance(record, dict) and isinstance(record.get("outcome"), str):
                outcomes[str(stem).lower()] = record["outcome"]
    return outcomes

"""The per-page pixel scores of a scored document (issue #144).

The scorer computes one score per matched page: ``score_document`` puts them
in the scored row's ``pages`` list, in document order.  The set-scoped
reports kept only the document aggregate and the aggregate page metrics, so
the release case shards (#143) had no per-page scores to show — jubarte.pro
shows them today.

This module reads that list out of a scored row.  It computes nothing new and
changes no score, so the content cache's fingerprint stays where it is (a
cached row already carries ``pages``) and a cache hit keeps its per-page
scores.  It lives outside the fingerprinted scoring modules on purpose: a
change there would miss every cached score and re-score the corpus for a
report field that only reads what is already stored.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

__all__ = ["per_page_scores"]


def per_page_scores(row: Mapping[str, object]) -> list[float]:
    """The scores of the pages the scorer matched, in document order.

    ``score_document`` scores ``min(oracle, candidate)`` pages, so the list
    holds the matched pages only: a page the tool never produced has no value
    here.  (The pagefair aggregate folds such a page in at zero; the list does
    not invent a score for it, and a consumer that shows a page it has no
    score for shows nothing for it.)

    The values are the scorer's own, unrounded — the same treatment the
    document score gets in the reports; a view rounds when it draws them.

    A row without pages (a failed conversion, a legacy row) has no per-page
    scores at all.
    """
    pages = row.get("pages")
    if not isinstance(pages, Sequence) or isinstance(pages, (str, bytes)):
        return []
    scores: list[float] = []
    for page in pages:
        value = page.get("score") if isinstance(page, Mapping) else page
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        scores.append(float(value))
    return scores

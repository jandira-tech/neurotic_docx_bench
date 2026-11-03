"""The per-page pixel scores a scored row carries (issue #144).

The scorer computes one score per matched page (``score_document``'s
``pages``).  The set-scoped reports kept only the document aggregate and the
aggregate page metrics, so the release case shards (#143) had no per-page
scores to show.  These tests pin the extraction the two report writers use.
"""

from __future__ import annotations

from neurotic_docx_bench.page_scores import per_page_scores


def test_the_matched_pages_scores_come_back_in_document_order() -> None:
    row = {"pages": [{"page": 1, "score": 91.5}, {"page": 2, "score": 88.25}]}
    assert per_page_scores(row) == [91.5, 88.25]


def test_a_row_without_pages_has_no_per_page_scores() -> None:
    assert per_page_scores({}) == []
    assert per_page_scores({"pages": None}) == []
    assert per_page_scores({"pages": []}) == []


def test_a_page_without_a_score_is_not_invented() -> None:
    assert per_page_scores({"pages": [{"page": 1}, {"page": 2, "score": 50.0}]}) == [50.0]


def test_a_plain_list_of_scores_is_read_as_the_pages_in_order() -> None:
    assert per_page_scores({"pages": [10.0, 20.0]}) == [10.0, 20.0]


def test_the_values_are_the_scorers_own_not_rounded() -> None:
    """The report keeps what the scorer computed; the view rounds when it draws it."""
    score = 66.15405838253962
    assert per_page_scores({"pages": [{"page": 1, "score": score}]}) == [score]

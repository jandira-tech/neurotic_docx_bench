"""emit.gallery — worst-first candidate-vs-oracle HTML gallery per run."""

from __future__ import annotations

import base64

from neurotic_docx_bench.emit import gallery

# 1×1 transparent PNG — enough for path/markup assertions.
_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=",
)


def _score_tree(root, key, cand_pages=1, oracle_pages=1):
    for side, n in (("candidate", cand_pages), ("oracle", oracle_pages)):
        d = root / "score" / key / side
        d.mkdir(parents=True, exist_ok=True)
        for i in range(1, n + 1):
            (d / f"page_{i:04d}.png").write_bytes(_PNG)


def test_gallery_orders_worst_first_and_links_rasters(tmp_path):
    _score_tree(tmp_path, "good_doc")
    _score_tree(tmp_path, "bad_doc")
    scores = {"good_doc": 98.5, "bad_doc": 41.2}

    out = gallery.write_gallery(tmp_path, scores, title="t — vs oracle")
    assert out == tmp_path / "report.html"
    text = out.read_text()

    # worst first: bad_doc's section precedes good_doc's
    assert text.index('id="bad_doc"') < text.index('id="good_doc"')
    # both sides referenced relative to run_dir
    assert 'src="score/bad_doc/candidate/page_0001.png"' in text
    assert 'src="score/bad_doc/oracle/page_0001.png"' in text
    # index table lists every doc with formatted score
    assert "41.20" in text and "98.50" in text


def test_gallery_none_scores_sort_first_and_render_na(tmp_path):
    _score_tree(tmp_path, "scored")
    (tmp_path / "score" / "unscored").mkdir(parents=True)
    scores = {"scored": 77.0, "unscored": None}

    text = gallery.render_gallery(scores, tmp_path / "score", title="t")

    assert text.index('id="unscored"') < text.index('id="scored"')
    assert "n/a" in text
    assert "no rasters persisted" in text  # unscored has no candidate/oracle dirs


def test_gallery_page_count_mismatch_marks_missing(tmp_path):
    _score_tree(tmp_path, "doc", cand_pages=1, oracle_pages=2)

    text = gallery.render_gallery({"doc": 50.0}, tmp_path / "score", title="t")

    assert 'src="score/doc/oracle/page_0002.png"' in text
    assert "missing page" in text  # candidate has no page 2


def test_gallery_limit_caps_sections_not_index(tmp_path):
    for k in ("a_doc", "b_doc", "c_doc"):
        _score_tree(tmp_path, k)
    scores = {"a_doc": 10.0, "b_doc": 20.0, "c_doc": 30.0}

    text = gallery.render_gallery(scores, tmp_path / "score", title="t", limit=1)

    assert '<section id="a_doc">' in text
    assert '<section id="b_doc">' not in text
    # index still lists all three
    assert '#b_doc"' in text and '#c_doc"' in text

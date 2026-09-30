"""Spec for viewer_features: the anchored patch that adds the mode drop-down, the case
filters and the random first case to the engine-comparison viewer.

Run: uv run --with pytest pytest _build/test_viewer_features.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import viewer_features as vf  # noqa: E402

SITE = HERE.parent


def _built(rel: str) -> str:
    return (SITE / rel).read_text()


@pytest.fixture(scope="module")
def pages() -> dict[str, str]:
    # The published pages carry the template text verbatim around the data, so they hold
    # every anchor exactly once (unless already patched).
    return {rel: _built(rel) for rel in ("index.html", "redlines/index.html")}


def test_every_anchor_occurs_once_in_both_published_pages(pages):
    for rel, html in pages.items():
        if vf.MARKER in html:
            continue
        for old, _ in vf.swaps("convert"):
            assert html.count(old) == 1, (rel, old[:60])


@pytest.mark.parametrize(("mode", "here", "other"), [("convert", "./", "redlines/"), ("redline", "./", "../")])
def test_the_mode_dropdown_selects_this_page_and_links_the_other(mode, here, other):
    html = vf.mode_select(mode)
    assert 'id="mode"' in html and 'autocomplete="off"' in html
    selected = re.search(r'<option value="([^"]*)" selected>', html)
    assert selected and selected.group(1) == here
    assert f'<option value="{other}">' in html
    assert "Convert DOCX" in html and "Compare (redline) two documents" in html


def test_patch_is_idempotent_and_refuses_a_missing_anchor(pages):
    html = pages["index.html"]
    once = vf.patch(html, "convert")
    assert vf.MARKER in once and vf.patch(once, "convert") == once
    with pytest.raises(SystemExit, match="anchor"):
        vf.patch("<html>no viewer here</html>", "convert")


def test_a_linked_case_wins_over_the_random_pick(pages):
    js = vf.patch(pages["index.html"], "convert")
    assert "const linked = applyHash();" in js and "if (!linked) pickRandom();" in js


def test_typing_in_a_filter_never_triggers_a_shortcut(pages):
    js = vf.patch(pages["index.html"], "convert")
    assert "e.target.tagName === 'SELECT'" in js and "'number'" in js


def test_the_filters_are_in_the_side_panel_and_in_visible_cases(pages):
    js = vf.patch(pages["redlines/index.html"], "redline")
    for el in ("fxGroup", "fxPages", "fxEng", "fxMetric", "fxMax", "fxDiffer", "fxn", "fxRand", "fxClear"):
        assert f'id="{el}"' in js
    body = js[js.index("function visibleCases()"):]
    body = body[: body.index("\n}\n")]
    assert "passesFx(c)" in body


def test_the_opening_case_is_scrolled_into_the_list(pages):
    js = vf.patch(pages["index.html"], "convert")
    tail = js[js.rindex("render();"):]
    assert tail.startswith("render();\nshowSel();") and "function showSel()" in js


def test_the_legend_folds_into_an_accordion_with_the_key_hints(pages):
    for rel, mode in (("index.html", "convert"), ("redlines/index.html", "redline")):
        js = vf.patch(pages[rel], mode)
        assert "function accordionLegend()" in js
        legend = js.index("$('#legend').innerHTML")
        assert js.index("accordionLegend();", legend) > legend
        assert '<span id="keys" style="color:var(--muted)">' in js  # moved into the accordion at runtime


def test_prev_next_random_buttons_step_through_the_filtered_list(pages):
    js = vf.patch(pages["index.html"], "convert")
    for el in ("navPrev", "navRand", "navNext", "navPos"):
        assert f'id="{el}"' in js
    assert "function step(d)" in js and "(at + d + vis.length) % vis.length" in js


def test_the_side_panel_can_be_hidden(pages):
    js = vf.patch(pages["redlines/index.html"], "redline")
    assert 'id="sideToggle"' in js and "body.noside" in js
    assert "e.key === 's'" in js and "classList.toggle('noside', !!state.noside)" in js


def test_a_filter_change_scrolls_the_selected_case_into_view(pages):
    js = vf.patch(pages["index.html"], "convert")
    body = js[js.index("function fxChanged()"):]
    assert "render(); showSel();" in body[: body.index("\n}\n")]


def test_each_page_keeps_its_own_saved_state(pages):
    red = vf.patch(pages["redlines/index.html"], "redline")
    conv = vf.patch(pages["index.html"], "convert")
    assert "localStorage.getItem('ec.redline.'+k)" in red and "localStorage.setItem('ec.redline.'+k" in red
    assert "localStorage.getItem('ec.'+k)" in conv  # the convert page keeps its visitors' state


def test_saved_filters_that_hide_every_case_are_dropped_on_load(pages):
    js = vf.patch(pages["index.html"], "convert")
    body = js[js.index("function setupFx()"):]
    body = body[: body.index("\n}\n")]
    assert "if (!visibleCases().length)" in body

"""Spec for viewer_theme: the jubarte.pro look over the GitHub Pages viewer.

Run: uv run --with pytest pytest _build/test_viewer_theme.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import viewer_features as vf  # noqa: E402
import viewer_theme as vt  # noqa: E402

SITE = HERE.parent
PAGES = {"index.html": "convert", "redlines/index.html": "redline", "speed/index.html": "speed"}


def _themed(rel: str) -> str:
    html = (SITE / rel).read_text()
    mode = PAGES[rel]
    return vt.theme(html, mode) if mode == "speed" else vf.patch(html, mode)


def test_every_published_page_takes_the_theme_once():
    for rel in PAGES:
        once = _themed(rel)
        assert once.count(vt.MARKER) == 1, rel
        assert vt.theme(once, PAGES[rel]) == once, rel  # idempotent


def test_the_theme_swaps_the_editor_palette_for_jubartes():
    for rel in PAGES:
        html = _themed(rel)
        css = html[html.index(vt.MARKER):html.index("</style>")]
        assert "--bg:var(--paper)" in css and "--fg:var(--ink)" in css, rel
        assert '"Manrope"' in css and '"JetBrains Mono"' in css, rel
    viewer = _themed("index.html")
    assert "'#4ea1ff', '#c586c0'" not in viewer  # the legend dots follow too
    assert "'#1e5580', '#3d7eae'" in viewer


def test_each_page_names_itself_and_links_home():
    for rel, mode in PAGES.items():
        html = _themed(rel)
        header = re.search(r'<header id="brand">.*?</header>', html, re.S).group(0)
        assert 'href="https://jubarte.pro/"' in header, rel
        assert vt.TITLES[mode] in header, rel
        assert header.count("<svg") == 1, rel


def test_the_fonts_the_pages_ask_for_are_published_with_their_licences():
    for rel, mode in PAGES.items():
        html = _themed(rel)
        for url in re.findall(r'src:url\("([^"]+)"\)', html[html.index(vt.MARKER):]):
            assert (SITE / rel).parent.joinpath(url).resolve().is_file(), (rel, url)
    fonts = SITE / "_static" / "fonts"
    assert (fonts / "LICENSE-manrope.txt").is_file()
    assert (fonts / "LICENSE-jetbrains-mono.txt").is_file()


def test_the_speed_link_resolves_from_both_viewers():
    for rel in ("index.html", "redlines/index.html"):
        html = _themed(rel)
        href = re.search(r'<a href="([^"]*speed/)">Speed</a>', html).group(1)
        assert (SITE / rel).parent.joinpath(href, "index.html").resolve().is_file(), rel

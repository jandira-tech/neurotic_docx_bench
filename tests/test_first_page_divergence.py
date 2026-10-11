"""scripts/first_page_divergence.py: a page only one PDF has is a divergence."""

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'first_page_divergence.py'
spec = importlib.util.spec_from_file_location('first_page_divergence', SCRIPT)
fpd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fpd)


def test_an_extra_page_after_matching_pages_is_the_divergence():
    word = ['one two', 'three four']
    assert fpd.first_divergence(word, [*word, 'five six']) == 2
    assert fpd.first_divergence([*word, 'five'], word) == 2


def test_matching_pdfs_have_no_divergence_and_a_changed_page_is_found():
    assert fpd.first_divergence(['a b', 'c d'], ['a b', 'c d']) is None
    assert fpd.first_divergence(['a b', 'c d', 'e'], ['a b', 'x d']) == 1

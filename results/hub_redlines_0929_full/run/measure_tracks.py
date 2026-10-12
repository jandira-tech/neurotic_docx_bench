"""Score this run's accepted and rejected tracks with the 0928 scorer, unchanged.

    BENCH_DEVICE=mps uv run python results/redlines_0929_full/measure_tracks.py accepted jubarte-rust docxodus superdoc
    BENCH_DEVICE=mps uv run python results/redlines_0929_full/measure_tracks.py rejected jubarte-rust docxodus superdoc

``results/redlines_0928/measure.py`` with its folder (``HERE``) pointed here: each tool's
redline of the 100 compares in ``accept_selection.csv`` / ``reject_selection.csv`` (copies of
the 0928 selections), staged as ``<tool>/{accepted,rejected}/src/<compare id>.docx``, with
every change accepted / rejected by Word (``scripts/word_pdf_focus.py --accept-all`` /
``--reject-all``) into ``<tool>/{accepted,rejected}/by_word``, against Word's own compare
accepted / rejected the same way (corpus sets ``accepted_tracking_0928`` /
``rejected_tracking_0928``). Writes ``scores_<track>_<tool>.json`` here.
"""

import importlib.util
from pathlib import Path

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location('measure_0928', HERE.parent / 'redlines_0928' / 'measure.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
m.HERE = HERE

if __name__ == '__main__':
    m.main()

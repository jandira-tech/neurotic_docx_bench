# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
"""The four page-metrics values of any PDF against Word's, with the priority folder's own scorer
(scripts/priority.py: its mutool 150 DPI `draw` and docxide-pdf `page-metrics` binary).

pair(ref, pdf) -> {jaccard, ssim, text_boundary, max_break_drift}; the first three 0-100, drift
signed words (None when page-metrics finds no text). A missing PDF scores 0 / None.
scored(pairs, cache) scores {key: (ref, pdf)} once per cache file (runs/m4_*.json)."""
import json, pathlib, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, "/Users/arthrod/temp/T/jubarte-redlines/_to_improve_docx_to_pdf_priority/scripts")
import priority as pr  # noqa: E402

FAILED = {"jaccard": 0.0, "ssim": 0.0, "text_boundary": 0.0, "max_break_drift": None}


def pair(ref, pdf):
    ref, pdf = pathlib.Path(ref), pathlib.Path(pdf)
    if not pdf.is_file():
        return dict(FAILED)
    with tempfile.TemporaryDirectory(prefix="m4_") as tmp:
        tmp = pathlib.Path(tmp)
        pr.draw(ref, tmp / "reference")
        pr.draw(pdf, tmp / "candidate")
        r = subprocess.run([str(pr.METRICS_BIN), str(ref), str(pdf), str(tmp / "reference"), str(tmp / "candidate")],
                           capture_output=True, text=True)
    try:
        m = json.loads(r.stdout)
    except ValueError:
        return dict(FAILED)
    return {k: (None if m.get(k) is None else m[k] if k == "max_break_drift" else round(m[k] * 100, 1))
            for k in pr.METRICS}


def scored(pairs, cache):
    cache = pathlib.Path(cache)
    if cache.exists():
        got = json.load(open(cache))
        if set(got) >= set(pairs):
            return got
    keys = list(pairs)
    with ThreadPoolExecutor(8) as ex:
        got = dict(zip(keys, ex.map(lambda k: pair(*pairs[k]), keys)))
    json.dump(got, open(cache, "w"), indent=0)
    return got

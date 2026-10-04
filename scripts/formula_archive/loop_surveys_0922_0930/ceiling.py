# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
"""ceiling.py RUN : where a tip run's pixel score goes, file by file.

Re-scores runs/tip_RUN/pdf against its oracle with the tip scorer and splits the
loss: pagination (pagefair vs same-page-count overall), author colour (every page's
color_sim taken as 1) and the rest (layout/glyph ink). Writes runs/tip_RUN/ceiling.json.
Run with the bench venv: ../neurotic_docx_bench/.venv/bin/python ceiling.py w12"""
import json, pathlib, shutil, statistics as st, sys

sys.path.insert(0, "/Users/arthrod/temp/T/neurotic_docx_bench/src")
from neurotic_docx_bench import docx_to_pdf as d2p  # noqa: E402

L = pathlib.Path(__file__).parent


def combine(pages, scores):
    w = [max(p["ink_area"], 1) for p in pages]
    avg = sum(s * x for s, x in zip(scores, w)) / sum(w)
    return 0.7 * avg + 0.3 * min(scores)


def main():
    run = L / "runs" / f"tip_{sys.argv[1]}"
    work = pathlib.Path("/tmp/acc/ceil_work")
    full = d2p.score_folder_pair(run / "oracle", run / "pdf", work, dpi=144, jobs=10)
    shutil.rmtree(work, ignore_errors=True)
    rows = {}
    for k, r in full.items():
        pages = r.get("pages") or []
        if not pages:
            rows[k] = {"pixel": 0.0, "same_pages": 0.0, "no_colour": 0.0, "pages_ok": False}
            continue
        rows[k] = {
            "pixel": float(r["overall_score_pagefair"]),
            "same_pages": float(r["overall_score"]),
            "no_colour": combine(pages, [p["score"] + 15.0 * (1.0 - p["color_sim"]) for p in pages]),
            "colour_sim": st.mean(p["color_sim"] for p in pages),
            "page_mean": st.mean(p["score"] for p in pages),
            "pages_ok": r.get("page_count_oracle") == r.get("page_count_candidate"),
            "pages": [{f: p[f] for f in ("page", "score", "ink_f1", "edge_iou", "color_sim", "delta_e")}
                      for p in pages],
        }
    json.dump(rows, open(run / "ceiling.json", "w"), indent=0)
    for f in ("pixel", "same_pages", "no_colour", "page_mean"):
        xs = [x.get(f, 0.0) for x in rows.values()]
        print(f"{f:10s} mean {st.mean(xs):6.2f} median {st.median(xs):6.2f}")
    print("colour_sim mean %.3f" % st.mean(x.get("colour_sim", 0.0) for x in rows.values()))
    print("page count differs:", sum(not x["pages_ok"] for x in rows.values()), "of", len(rows))


if __name__ == "__main__":
    main()

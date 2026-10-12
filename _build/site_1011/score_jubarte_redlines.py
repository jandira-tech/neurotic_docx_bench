"""Score jubarte's redlines against Word's compare now (scores only, no images): process.py redlines redoes it later.

    uv run --with pillow python score_jubarte_redlines.py
"""
import csv, json, statistics as st, tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from process import BUILD, RUN, H, draw, metrics


def one(cid):
    ref, pdf = RUN / "word_compare/out" / f"{cid}__vs__{cid}.pdf", RUN / "word_render/jubarte" / f"{cid}.pdf"
    if not ref.is_file():
        return None
    if not pdf.is_file():
        return cid, None, 0, 0
    with tempfile.TemporaryDirectory(prefix="s_", dir=BUILD) as t:
        t = Path(t)
        a, b = draw(ref, t / "r"), draw(pdf, t / "j")
        return cid, metrics(ref, pdf, t / "r", t / "j") if b else {}, a, b


ids = [r["id"] for r in csv.DictReader(open(H / "sample_redlines.csv"))]
with ThreadPoolExecutor(3) as ex:
    rows = [r for r in ex.map(one, ids) if r]
(BUILD / "jubarte_redline_scores.json").write_text(json.dumps(rows))
v = [st.mean(s.values()) for _, s, _, _ in rows if s]
print(f"{len(rows)} pairs with a Word redline; jubarte scored {len(v)}, no output {sum(s is None for _, s, _, _ in rows)}")
print(f"mean {st.mean(v):.1f}, median {st.median(v):.1f}, 90+ {sum(x >= 90 for x in v)}, <50 {sum(x < 50 for x in v)}, "
      f"same page count {sum(a == b for _, s, a, b in rows if s is not None)}")
for k in ("jaccard", "ssim", "text_boundary"):
    print(k, round(st.mean(s[k] for _, s, _, _ in rows if s and k in s), 1))

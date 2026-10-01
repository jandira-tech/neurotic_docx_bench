"""Build the redlines section (redlines_site/, published as /redlines/ next to the DOCX->PDF site).

Two tracks, every PDF rendered by Microsoft Word for Mac:

- redlines: each tool's compare of a corpus pair (base -> next) against Word's own compare
  of the same pair (neurotic-docx-bench results/<REDLINES_RUN>, default redlines_0929_full:
  2611 pairs of corpus/word; redlines_0928 is the 1164-pair run of jubarte 0.9.3). A run
  with gen_pairs.csv names each tool's redline after its pair's first compare key, and a
  compare Word made again (FRESH, measure.py --fresh) replaces that compare's oracle.
- accepted: the 100 pairs of accept_selection.csv, with every tracked change of the redline
  accepted by Word; each tool's redline accepted that way against Word's compare accepted
  that way (corpus/word pool accepted_tracking_0928).
- rejected: the 100 pairs of reject_selection.csv (none from the accept set), every change
  rejected by Word, against Word's compare rejected that way (corpus set rejected_tracking_0928).

The viewer shows a seeded sample (both states, half of it from pairs every tool produced)
with docxide-pdf's page-metrics at 150 DPI over every page; the first 3 pages are shown as
100 DPI 16-colour WebP. The bench's own scores for every pair (results/redlines_0928/
measure.py) are summarised on the page and copied to _build/redlines/.

A run whose tool outputs were pruned after the upload to the results dataset
(``hub_upload.py --prune``) reads them from ``outputs/<REDLINES_RUN>/`` of HUB_REPO: case
selection checks the dataset's file list, and only the PDFs of the chosen cases are downloaded.

    uv run --with pillow --with huggingface_hub python build_redlines_site.py
"""

from __future__ import annotations

import csv
import json
import os
import random
import re
import shutil
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import add_jubarte as aj
import build_site as bs

HERE = aj.HERE
OUT = HERE / "redlines_site"
BENCH = HERE.parent / "neurotic_docx_bench"
RUN = os.environ.get("REDLINES_RUN", "redlines_0929_full")
R = BENCH / "results" / RUN
CORPUS = BENCH / "corpus" / "word"
FRESH = Path.home() / "temp" / "T" / "compare_regen" / "out"  # Word compares made again (0929 only)
# jubarte 0.10.1, the release, rerun on the pairs the published page shows (results/redlines_1001_j0101,
# release CLI through generate-native-redlines.ts, PDFs and accept / reject by Word); its files keep
# the jubarte column's key so saved viewer state carries over. Unset to show the run's own jubarte.
J0101 = BENCH / "results" / "redlines_1001_j0101"
JUBARTE_0101 = os.environ.get("JUBARTE_0101", "1") == "1" and (J0101 / "jubarte-0101").is_dir()
# Rebuild the published selection (its redlines/cases.json) instead of drawing a new sample.
KEEP_CASES = os.environ.get("KEEP_CASES")
HUB_REPO = "arthrod/neurotic_docx_bench"  # neurotic_docx_bench.hub.RESULTS_REPO (a dataset)
TOOLS = {"redlines_0928": ["jubarte-rust", "docxodus", "superdoc"],
         "redlines_0929_full": ["jubarte-rust", "jubarte-093", "docxodus", "superdoc"]}[RUN]
STATES = ["with_comments_tracking", "tracking_without_comments"]
SEED = 20260928
REDLINE_N = 30  # per state
ACCEPTED_N = 20  # per state
JOBS = 8
ENGINES = [["reference", "Word"], ["jubarte-rust", "jubarte"], ["jubarte-093", "jubarte 0.9.3"],
           ["docxodus", "docxodus"], ["superdoc", "SuperDoc"]]
ENGINES = [e for e in ENGINES if e[0] == "reference" or e[0] in TOOLS]
VERSIONS = {
    "redlines_0928": {
        "reference": "Word 16.114 compare",
        "jubarte-rust": "0.9.3 @673aff7",
        "docxodus": "12.6.4",
        "superdoc": "superdoc-sdk 2.15.0",
    },
    "redlines_0929_full": {
        "reference": "Word 16.114 compare",
        "jubarte-rust": "0.10.1 (release)" if JUBARTE_0101 else "0.10.0 @86b6b5d3",
        "jubarte-093": "0.9.3 (release)",
        "docxodus": "12.6.5",
        "superdoc": "superdoc-sdk 2.16.0",
    },
}[RUN]


_hub_files: set[str] | None = None


def tool_file(t: str, *parts: str) -> Path:
    """``<run>/<tool>/<parts…>`` with the tool's own file suffix; jubarte-rust may come from J0101."""
    if t == "jubarte-rust" and JUBARTE_0101:
        return J0101.joinpath("jubarte-0101", *parts[:-1], parts[-1].replace("{t}", "jubarte-0101"))
    return R.joinpath(t, *parts[:-1], parts[-1].replace("{t}", t))


def hub_files() -> set[str]:
    """Paths under ``outputs/<RUN>/`` of HUB_REPO, relative to it (listed once)."""
    global _hub_files
    if _hub_files is None:
        from huggingface_hub import HfApi
        prefix = f"outputs/{RUN}/"
        _hub_files = {f.removeprefix(prefix) for f in HfApi().list_repo_files(HUB_REPO, repo_type="dataset")
                      if f.startswith(prefix)}
    return _hub_files


def available(p: Path) -> bool:
    """A file of this run that exists here or in the run's upload to HUB_REPO."""
    if p.is_file():
        return True
    try:
        return str(p.relative_to(R)) in hub_files()
    except ValueError:
        return False


def fetch(p: Path) -> Path:
    """``p`` itself when it exists, else its copy from HUB_REPO (downloaded into the HF cache)."""
    if p.is_file():
        return p
    from huggingface_hub import hf_hub_download
    return Path(hf_hub_download(HUB_REPO, f"outputs/{RUN}/{p.relative_to(R)}", repo_type="dataset"))


def redline_pdfs(row: dict) -> dict[str, Path]:
    key = row["key"]
    fresh = FRESH / f'{row["id"]}__vs__{row["id"]}.pdf'
    out = {"reference": fresh if RUN != "redlines_0928" and fresh.is_file() else R / "oracle_pdf" / f"{key}.pdf"}
    out |= {t: tool_file(t, "pdf_by_word", f"{key}_{{t}}.pdf") for t in TOOLS}
    return {k: p for k, p in out.items() if available(p)}


def accepted_pdfs(cmp_id: str, word: dict[str, Path]) -> dict[str, Path]:
    out = {"reference": word[cmp_id]}
    out |= {t: tool_file(t, "accepted", "by_word", f"{cmp_id}_accepted_tracking_{{t}}.pdf") for t in TOOLS}
    return {k: p for k, p in out.items() if available(p)}


def rejected_pdfs(cmp_id: str, word: dict[str, Path]) -> dict[str, Path]:
    out = {"reference": word[cmp_id]}
    out |= {t: tool_file(t, "rejected", "by_word", f"{cmp_id}_rejected_tracking_{{t}}.pdf") for t in TOOLS}
    return {k: p for k, p in out.items() if available(p)}


def pick(rows: list[dict], n: int, full, rng: random.Random) -> list[dict]:
    """``n`` rows: half from those every tool produced (``full``), the rest from the others."""
    both = sorted((r for r in rows if full(r)), key=lambda r: r["key"])
    rest = sorted((r for r in rows if not full(r)), key=lambda r: r["key"])
    a = rng.sample(both, min(len(both), n // 2))
    return a + rng.sample(rest, min(len(rest), n - len(a)))


def pdf_pages(pdf: Path, dest: Path) -> list[str]:
    bs.OUT = OUT
    return bs.pdf_pages(pdf, dest)


def page_count(pdf: Path) -> int:
    info = subprocess.run(["mutool", "info", str(pdf)], capture_output=True, text=True).stdout
    m = re.search(r"Pages:\s*(\d+)", info)
    return int(m.group(1)) if m else 0


def case(group: str, name: str, pdfs: dict[str, Path]) -> dict:
    pdfs = {k: fetch(p) for k, p in pdfs.items()}
    base = OUT / group / name
    with tempfile.TemporaryDirectory(prefix="rl_", dir=HERE / "work") as tmp:
        ref_dir = Path(tmp) / "reference"
        aj.pngs(pdfs["reference"], ref_dir)
        scores, pages, counts = {}, {}, {}
        for key, pdf in pdfs.items():
            counts[key] = page_count(pdf)
            pages[key] = pdf_pages(pdf, base / key)
            if key != "reference":
                d = Path(tmp) / key
                aj.pngs(pdf, d)
                scores[key] = aj.metrics(pdfs["reference"], pdf, ref_dir, d)
                shutil.rmtree(d)
    return {"group": group, "case": name, "pages": pages, "page_counts": counts, "scores": scores,
            "times": {}, "reference_app": bs.pdf_creator(pdfs["reference"])}


def summary_line(track: str) -> str:
    parts = []
    for t in TOOLS:
        f = R / f"scores_{track}_{t}.json"
        if track == "redlines" and not f.exists():
            f = R / f"scores_{t}.json"  # the 0929 measure.py writes redline scores unprefixed
        if not f.exists():
            continue
        s = json.loads(f.read_text())["summary"]
        o = s["overall"]
        label = "jubarte 0.10.0 (bench run)" if t == "jubarte-rust" and JUBARTE_0101 else dict(ENGINES)[t]
        parts.append(f"{label} {s['scored']}/{s['pairs']}"
                     + (f", mean {o['mean']:.1f}, median {o['median']:.1f}, {o['at_least_90']} at 90+" if o["n"] else ""))
    return "; ".join(parts)


def main() -> None:
    t0 = time.time()
    rng = random.Random(SEED)
    # gen_pairs.csv: one row per pair, keyed by the compare the tools' redlines are named after
    pool_csv = R / "gen_pairs.csv" if (R / "gen_pairs.csv").exists() else R / "pool_pairs.csv"
    pool = list(csv.DictReader(open(pool_csv)))

    jobs = []
    for state in STATES:
        rows = [r for r in pool if r["state"] == state]
        for r in pick(rows, REDLINE_N, lambda r: len(redline_pdfs(r)) == len(TOOLS) + 1, rng):
            jobs.append((f"redlines/{state}", r["id"], redline_pdfs(r)))

    word = {row["key"].split("_")[1]: CORPUS / row["pdf"]
            for row in csv.DictReader(open(CORPUS / "pools" / "accepted_tracking_0928_renders.csv"))}
    selection = list(csv.DictReader(open(R / "accept_selection.csv")))
    for state in STATES:
        rows = [r for r in selection if r["state"] == state]
        for r in pick(rows, ACCEPTED_N, lambda r: len(accepted_pdfs(r["id"], word)) == len(TOOLS) + 1, rng):
            jobs.append((f"accepted/{state}", r["id"], accepted_pdfs(r["id"], word)))

    # Word's compares rejected by Word: the corpus set rejected_tracking_0928 (it left grok_run/wr0928).
    rej_word = {row["key"].split("_")[1]: CORPUS / row["pdf"]
                for row in csv.DictReader(open(CORPUS / "pools" / "rejected_tracking_0928_renders.csv"))}
    rej_groups = []
    if rej_word and (R / "reject_selection.csv").exists():
        rsel = [r for r in csv.DictReader(open(R / "reject_selection.csv")) if r["id"] in rej_word]
        for state in STATES:
            rows = [r for r in rsel if r["state"] == state]
            if rows:
                rej_groups.append(f"rejected/{state}")
            for r in pick(rows, ACCEPTED_N, lambda r: len(rejected_pdfs(r["id"], rej_word)) == len(TOOLS) + 1, rng):
                jobs.append((f"rejected/{state}", r["id"], rejected_pdfs(r["id"], rej_word)))

    if KEEP_CASES:
        by_id = {r["id"]: r for r in pool}
        jobs = []
        for c in json.loads(Path(KEEP_CASES).read_text()):
            track = c["group"].split("/")[0]
            pdfs = (redline_pdfs(by_id[c["case"]]) if track == "redlines"
                    else accepted_pdfs(c["case"], word) if track == "accepted"
                    else rejected_pdfs(c["case"], rej_word))
            jobs.append((c["group"], c["case"], pdfs))
        print(f"kept the {len(jobs)} published cases ({KEEP_CASES})", flush=True)

    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir()
    (HERE / "work").mkdir(exist_ok=True)
    with ThreadPoolExecutor(max_workers=JOBS) as ex:
        cases = list(ex.map(lambda j: case(*j), jobs))
    print(f"{len(cases)} cases encoded ({time.time() - t0:.0f} s)", flush=True)

    jver = "0.10.1" if JUBARTE_0101 else "0.10.0"
    note = ("<span><b>What this is</b>: redlines by jubarte" + (f" ({jver} and the 0.9.3 release)" if "jubarte-093" in TOOLS else "") + ", docxodus and SuperDoc against Microsoft Word&#8217;s own "
            "compare, every PDF rendered by Word for Mac, scored with docxide-pdf&#8217;s page-metrics at 150 DPI over "
            "every page. <b>redlines</b>: the tool&#8217;s compare of a corpus pair vs Word&#8217;s compare of it. "
            "<b>accepted</b>: the same redlines with every tracked change accepted by Word, vs Word&#8217;s compare "
            "accepted the same way. Shown: a seeded sample, half of it from pairs every tool produced; first 3 "
            f"pages at 100 DPI. Bench scores over every pair ({len(pool)} redline pairs, 100 accepted, 100 rejected): redlines: "
            + summary_line("redlines") + ". accepted: " + summary_line("accepted") + (". rejected (every change rejected by Word, vs Word&#8217;s compare rejected "
            "the same way): " + summary_line("rejected") if rej_groups else "") + ". SuperDoc (latest SDK) "
            "refuses most pairs, so its column is often empty. Scores: _build/redlines/.</span>"
            + ("<span><b>jubarte 0.10.1</b>: the release CLI reran the pairs shown here (redlines, then "
               "Word&#8217;s PDF, accept-all and reject-all of them, as for every tool); the bench-wide "
               "scores above are its 0.10.0 run.</span>" if JUBARTE_0101 else ""))
    note = note.replace("'", "&#8217;")
    aj.ec.HTML_TEMPLATE = bs.patched_template(note).replace(
        "<title>jubarte DOCX to PDF vs Microsoft Word: engine comparison</title>",
        "<title>Redlines vs Microsoft Word: jubarte, docxodus, SuperDoc</title>").replace(
        "<kbd>1</kbd>-<kbd>8</kbd> engines", f"<kbd>1</kbd>-<kbd>{len(ENGINES)}</kbd> engines")
    aj.ec.ENGINES = ENGINES
    aj.ec.GROUPS = [f"redlines/{s}" for s in STATES] + [f"accepted/{s}" for s in STATES] + rej_groups
    aj.ec.write_html(cases, VERSIONS, OUT / "index.html")
    (OUT / "cases.json").write_text(json.dumps(cases, indent=1))
    size = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file())
    n_img = sum(1 for _ in OUT.rglob("*.webp"))
    print(f"site {OUT}: {len(cases)} cases, {n_img} images, {size / 2**20:.1f} MiB ({time.time() - t0:.0f} s)")


if __name__ == "__main__":
    main()

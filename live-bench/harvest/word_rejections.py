"""Per-fixture Word verdicts from the jubarte-live-bench D1 dump.

Every bench_results row holds one fixture (`source`) and the fixture before it
in the chain (`previous`). Word stages:
  convert         source.docx -> PDF            (fixture = this row's source)
  compare         previous vs source            (error names the refused file as
                                                 <sequence>.docx or starting_point.docx)
  redline_render  a tool's redline docx -> PDF  (not a fixture: a tool output)
"""

import collections
import csv
import json
import re
import sqlite3
import sys
from pathlib import Path

DB, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)

WORD_ITSELF = {"corrupt", "word_failed", "convert_failed", "compare_failed"}
GATE = {"unsafe_package", "external_content", "active_content", "not_docx", "macros",
        "encrypted", "too_large"}


def classify(error: str) -> tuple[str, str, str]:
    """-> (family, code, http)"""
    http = (m.group(1) if (m := re.search(r"HTTP (\d+)", error)) else "")
    if (m := re.search(r'"code": "([a-z_]+)"', error)):
        code = m.group(1)
        if code in WORD_ITSELF:
            return "word_rejected", code, http
        if code in GATE:
            return "gate_rejected", code, http
        return "other", code, http
    if "<html" in error.lower() or "doctype" in error.lower():
        return "infrastructure", f"gateway_html_{http}", http
    if "ReadError" in error:
        return "infrastructure", "read_error", http
    if "unsafe generated package" in error:
        return "bench_side", "bench_unsafe_generated_package", http
    if "Traceback" in error:
        return "bench_side", "pdf_probe_traceback", http
    return "other", error[:60], http


db = sqlite3.connect(DB)
rows = [json.loads(p) for (p,) in db.execute(
    "select payload from bench_results order by run_id, sequence")]

fixtures: dict[str, dict] = {}   # by sha256
pairs = []                       # compare failures where both inputs passed convert
renders = []                     # failed Word renders of tool redlines
convert_err: dict[str, str] = {}

def fixture(doc: dict) -> dict:
    meta = doc.get("metadata", {}).get("corpus", {})
    return fixtures.setdefault(doc["sha256"], {
        "sha256": doc["sha256"], "corpus_id": doc["id"], "url": doc["url"],
        "corpus_filename": meta.get("filename", ""), "type": doc.get("type", ""),
        "language": doc.get("language", ""), "word_count": meta.get("word_count", ""),
        "bytes": doc.get("metadata", {}).get("download_bytes", ""),
        "bench_preflight": doc.get("security", {}).get("status", ""),
        "bench_preflight_error": doc.get("security", {}).get("error", ""),
        "word_convert": "", "family": "", "code": "", "http": "", "duration_ms": "",
        "request_id": "", "error": "", "runs": set(), "sequences": set(),
    })

def rid(err: str) -> str:
    return m.group(1) if (m := re.search(r'"request_id": "(\w+)"', err)) else ""

# Pass 1: each fixture's own single-file Word convert is its verdict. The compare
# error prefix is always the original's name (livebench/tools.py:223) and the
# endpoint stops at the first refused input, so compare cannot name the culprit.
for r in rows:
    f = fixture(r["source"])
    f["runs"].add(r["run_id"][:8]); f["sequences"].add(r["sequence"])
    if r.get("previous", {}).get("sha256"):
        fixture(r["previous"])
    for s in r["stages"]:
        if s["tool"] == "word" and s["operation"] == "convert":
            f["word_convert"] = s["status"]
            if s["status"] != "ok":
                err = s.get("error") or ""
                f["family"], f["code"], f["http"] = classify(err)
                f["duration_ms"], f["request_id"], f["error"] = round(s["duration_ms"]), rid(err), err[:300]

# Pass 2: compare failures not explained by an input's convert verdict, and renders.
for r in rows:
    prev, src = fixtures.get(r.get("previous", {}).get("sha256")), fixtures[r["source"]["sha256"]]
    for s in r["stages"]:
        if s["tool"] != "word" or s["status"] == "ok":
            continue
        err = s.get("error") or ""
        family, code, http = classify(err)
        if s["operation"] == "redline_render":
            renders.append({"run": r["run_id"][:8], "sequence": r["sequence"],
                            "redline": err.split(":", 1)[0], "family": family, "code": code,
                            "http": http, "source_sha256": src["sha256"], "error": err[:300]})
        elif s["operation"] == "compare":
            inputs_ok = all(x and x["word_convert"] == "ok" for x in (prev, src))
            if inputs_ok:
                if family == "gate_rejected":
                    family, code = "gate_rejected_word_output", f"output_{code}"
                pairs.append({"run": r["run_id"][:8], "sequence": r["sequence"],
                              "family": family, "code": code, "http": http,
                              "duration_ms": round(s["duration_ms"]),
                              "previous_sha256": prev["sha256"], "source_sha256": src["sha256"],
                              "previous_url": prev["url"], "source_url": src["url"],
                              "request_id": rid(err), "error": err[:300]})

RANK = {"word_rejected": 0, "gate_rejected": 1, "infrastructure": 2, "bench_side": 3, "other": 4}
cols = ["sha256", "corpus_id", "url", "corpus_filename", "type", "language", "word_count",
        "bytes", "family", "code", "http", "duration_ms", "word_convert", "bench_preflight",
        "runs", "sequences", "request_id", "error"]
out_rows = [{k: (" ".join(map(str, sorted(f[k]))) if isinstance(f[k], set) else f[k]) for k in cols}
            for f in fixtures.values() if f["word_convert"] not in ("ok", "")]
out_rows.sort(key=lambda x: (RANK[x["family"]], x["code"], x["corpus_filename"]))
never = [f for f in fixtures.values() if f["word_convert"] == ""]

def dump(name, data, fields=None):
    with open(OUT / name, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields or list(data[0]))
        w.writeheader(); w.writerows(data)

dump("word_rejected_fixtures.csv", out_rows)
dump("word_compare_pair_failures.csv", pairs)
dump("word_redline_render_failures.csv", renders)
dump("never_sent_to_word.csv", [{"sha256": f["sha256"], "url": f["url"],
      "bench_preflight": f["bench_preflight"], "bench_preflight_error": f["bench_preflight_error"]}
      for f in never])

print("fixtures seen:", len(fixtures), "| Word convert ran:",
      sum(1 for f in fixtures.values() if f["word_convert"]), "| ok:",
      sum(1 for f in fixtures.values() if f["word_convert"] == "ok"),
      "| refused/failed:", len(out_rows), "| never sent:", len(never))
print("never sent, by bench preflight:", dict(collections.Counter(
    (f["bench_preflight"], f["bench_preflight_error"][:50]) for f in never)))
print("\nfixtures by verdict (own Word convert):")
for k, v in collections.Counter((x["family"], x["code"]) for x in out_rows).most_common():
    print(f"  {v:5} {k[0]:15} {k[1]}")
print("\ncompare failures where both inputs converted fine (pair-level):")
for k, v in collections.Counter((x["family"], x["code"]) for x in pairs).most_common():
    print(f"  {v:5} {k[0]:26} {k[1]}")
print("\nredline renders Word failed (tool outputs, not fixtures):")
for k, v in collections.Counter((x["redline"], x["code"]) for x in renders).most_common():
    print(f"  {v:5} {k[0]:32} {k[1]}")

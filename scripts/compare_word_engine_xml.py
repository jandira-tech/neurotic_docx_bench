#!/usr/bin/env python3
"""Compare Word oracle redline document.xml to an engine redline document.xml.

Usage:
  uv run python scripts/compare_word_engine_xml.py \\
    --keys-file /tmp/keys.txt \\
    --engine-bin src/neurotic_docx_bench/utils/jubarte/jubarte-rust/redline \\
    --out /tmp/xml_compare

Or pass keys as positional args. Never invent markup shape from scores —
always unpack both DOCXs and classify paragraphs from the real OOXML.
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

ROOT = Path(__file__).resolve().parents[1]

MAPS = [
    (
        ROOT / "corpus/word_based/centralized_mapping.csv",
        ROOT / "corpus/word_based/docx_source",
        ROOT / "corpus/word_based/docx_redlines_word",
    ),
    (
        ROOT / "corpus/word_based/centralized_mapping_randomized.csv",
        ROOT / "corpus/word_based/docx_source_randomized",
        ROOT / "corpus/word_based/docx_redlines_randomized",
    ),
    (
        ROOT / "corpus/word_redlines_superdoc/centralized_mapping.csv",
        ROOT / "corpus/word_redlines_superdoc/docx_source",
        ROOT / "corpus/word_redlines_superdoc/docx_redlines_word",
    ),
]


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if tag.startswith("{") else tag


def extract_document_xml(docx: Path) -> str:
    with zipfile.ZipFile(docx) as z:
        return z.read("word/document.xml").decode("utf-8")


def pretty_xml(xml: str) -> str:
    try:
        return minidom.parseString(xml.encode("utf-8")).toprettyxml(indent="  ")
    except Exception:
        return xml


def body_paras(xml: str) -> list[ET.Element]:
    root = ET.fromstring(xml)
    body = next((el for el in root.iter() if local(el.tag) == "body"), None)
    if body is None:
        return []
    return [c for c in list(body) if local(c.tag) == "p"]


def para_text(p_el: ET.Element) -> str:
    bits: list[str] = []
    for el in p_el.iter():
        if local(el.tag) in ("t", "delText") and el.text:
            bits.append(el.text)
    return "".join(bits)


def para_class(p_el: ET.Element) -> str:
    has_ins = has_del = False
    for el in p_el.iter():
        ln = local(el.tag)
        if ln == "ins":
            has_ins = True
        elif ln == "del":
            has_del = True
    if has_ins and has_del:
        return "MIX"
    if has_ins:
        return "I"
    if has_del:
        return "D"
    return "EQ"


def has_numpr(p_el: ET.Element) -> bool:
    return any(local(el.tag) == "numPr" for el in p_el.iter())


def summarize(xml: str) -> list[dict]:
    rows = []
    for i, p in enumerate(body_paras(xml)):
        rows.append(
            {
                "i": i,
                "cls": para_class(p),
                "numPr": has_numpr(p),
                "text": para_text(p)[:120],
            }
        )
    return rows


def shape(rows: list[dict]) -> str:
    c = {"I": 0, "D": 0, "MIX": 0, "EQ": 0}
    for r in rows:
        c[r["cls"]] = c.get(r["cls"], 0) + 1
    return f"n={len(rows)} I={c['I']} D={c['D']} MIX={c['MIX']} EQ={c['EQ']}"


def class_seq(rows: list[dict]) -> str:
    return "".join("M" if r["cls"] == "MIX" else r["cls"][0] for r in rows)


def load_mapping() -> dict[str, dict]:
    by_key: dict[str, dict] = {}
    for mpath, sdir, rdir in MAPS:
        if not mpath.exists():
            continue
        with mpath.open(newline="") as f:
            for row in csv.DictReader(f):
                stem = (row.get("pair_stem") or "").strip()
                if not stem or stem in by_key:
                    continue
                base = (row.get("base") or "").replace(".docx", "")
                nxt = (row.get("next") or "").replace(".docx", "")
                candidates = [
                    rdir / f"{stem}_redline.docx",
                    rdir / f"{stem}_word_redline.docx",
                    ROOT / "corpus/word_based/docx_redlines_word" / f"{stem}_redline.docx",
                ]
                word = next((p for p in candidates if p.exists()), None)
                by_key[stem] = {
                    "base": sdir / f"{base}.docx",
                    "next": sdir / f"{nxt}.docx",
                    "word": word,
                }
    return by_key


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("keys", nargs="*", help="pair_stem keys")
    ap.add_argument("--keys-file", type=Path, help="one key per line")
    ap.add_argument(
        "--engine-bin",
        type=Path,
        default=ROOT
        / "src/neurotic_docx_bench/utils/jubarte/jubarte-rust/redline",
    )
    ap.add_argument("--out", type=Path, default=Path("/tmp/xml_compare"))
    ap.add_argument(
        "--engine-docx-dir",
        type=Path,
        default=None,
        help="if set, use existing <key>*redline.docx instead of generating",
    )
    args = ap.parse_args()

    keys: list[str] = list(args.keys)
    if args.keys_file:
        keys.extend(
            ln.strip()
            for ln in args.keys_file.read_text().splitlines()
            if ln.strip() and not ln.startswith("#")
        )
    if not keys:
        raise SystemExit("pass keys or --keys-file")

    out: Path = args.out
    for sub in ("word", "engine", "diff"):
        (out / sub).mkdir(parents=True, exist_ok=True)

    by = load_mapping()
    report = []
    missing = []

    for key in keys:
        info = by.get(key)
        if not info:
            missing.append({"key": key, "why": "not in mapping"})
            continue
        if info["word"] is None or not info["word"].exists():
            missing.append({"key": key, "why": "no Word redline docx on disk"})
            continue

        eng_path = out / "engine" / f"{key}.docx"
        if args.engine_docx_dir:
            hits = sorted(args.engine_docx_dir.glob(f"{key}*redline*.docx"))
            if not hits:
                missing.append({"key": key, "why": f"no engine docx under {args.engine_docx_dir}"})
                continue
            eng_path.write_bytes(hits[0].read_bytes())
        else:
            if not info["base"].exists() or not info["next"].exists():
                missing.append({"key": key, "why": "missing base/next source"})
                continue
            r = subprocess.run(
                [
                    str(args.engine_bin),
                    str(info["base"]),
                    str(info["next"]),
                    "-o",
                    str(eng_path),
                    "--force",
                    "--quiet",
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if r.returncode != 0 or not eng_path.exists():
                missing.append(
                    {
                        "key": key,
                        "why": f"engine fail: {(r.stderr or r.stdout or '')[-300:]}",
                    }
                )
                continue

        word_xml = extract_document_xml(info["word"])
        eng_xml = extract_document_xml(eng_path)
        (out / "word" / f"{key}.document.xml").write_text(word_xml)
        (out / "engine" / f"{key}.document.xml").write_text(eng_xml)
        (out / "word" / f"{key}.pretty.xml").write_text(pretty_xml(word_xml))
        (out / "engine" / f"{key}.pretty.xml").write_text(pretty_xml(eng_xml))

        wrows, erows = summarize(word_xml), summarize(eng_xml)
        n = max(len(wrows), len(erows))
        mismatches = []
        for i in range(n):
            w = wrows[i] if i < len(wrows) else None
            e = erows[i] if i < len(erows) else None
            if w is None or e is None or w["cls"] != e["cls"] or w["text"].strip() != e["text"].strip():
                mismatches.append({"i": i, "word": w, "engine": e})

        entry = {
            "key": key,
            "word_path": str(info["word"]),
            "word_shape": shape(wrows),
            "engine_shape": shape(erows),
            "word_seq": class_seq(wrows),
            "engine_seq": class_seq(erows),
            "seq_match": class_seq(wrows) == class_seq(erows),
            "n_mismatch_rows": len(mismatches),
            "word_paras": wrows,
            "engine_paras": erows,
            "mismatches_head": mismatches[:20],
        }
        report.append(entry)

        lines = [
            f"KEY: {key}",
            f"WORD:   {info['word']}",
            f"ENGINE: {eng_path}",
            f"WORD shape:   {entry['word_shape']}  seq={entry['word_seq']}",
            f"ENGINE shape: {entry['engine_shape']}  seq={entry['engine_seq']}",
            f"SEQ MATCH: {entry['seq_match']}",
            "",
            "--- WORD paras (from unpacked word/document.xml) ---",
        ]
        for r in wrows:
            lines.append(f"  p{r['i']:02d} {r['cls']:3} numPr={int(r['numPr'])} {r['text']!r}")
        lines.append("--- ENGINE paras (from unpacked word/document.xml) ---")
        for r in erows:
            lines.append(f"  p{r['i']:02d} {r['cls']:3} numPr={int(r['numPr'])} {r['text']!r}")
        lines.append("--- MISMATCHES ---")
        for m in mismatches[:20]:
            lines.append(repr(m))
        (out / "diff" / f"{key}.txt").write_text("\n".join(lines) + "\n")

    (out / "report.json").write_text(
        json.dumps({"report": report, "missing": missing}, indent=2)
    )

    print("=" * 72)
    print("WORD ORACLE XML vs ENGINE XML (unpacked document.xml)")
    print("=" * 72)
    for e in report:
        flag = "OK " if e["seq_match"] else "DIFF"
        print(f"\n[{flag}] {e['key']}")
        print(f"  WORD   {e['word_shape']}  seq={e['word_seq']}")
        print(f"  ENGINE {e['engine_shape']}  seq={e['engine_seq']}")
        if not e["seq_match"]:
            for m in e["mismatches_head"][:5]:
                w, eng = m.get("word"), m.get("engine")
                wt = f"{w['cls']}/{w['text']!r}" if w else "MISSING"
                et = f"{eng['cls']}/{eng['text']!r}" if eng else "MISSING"
                print(f"    p{m['i']}: Word={wt}  Eng={et}")
    if missing:
        print("\nMISSING:")
        for m in missing:
            print(f"  {m['key']}: {m['why']}")
    print(f"\nArtifacts: {out}/{{word,engine,diff}}/ report.json")
    print(f"Compared {len(report)} keys from real Word redline DOCX XML")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

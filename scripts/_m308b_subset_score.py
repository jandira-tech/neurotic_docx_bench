#!/usr/bin/env python3
"""Score M308b subset PDFs vs Word oracles; compare to restored/M308 baselines."""
from __future__ import annotations

import json
import shutil
import statistics
from pathlib import Path

from neurotic_docx_bench import pipeline

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runs" / "m308b_subset"


def find_oracle(key: str) -> Path | None:
    oracle_dirs = [
        ROOT / "corpus/word_based/pdf_redlines_word",
        ROOT / "corpus/word_based/pdf_redlines_randomized/pdf",
        ROOT / "corpus/word_redlines_superdoc/pdf_redlines_word",
    ]
    for d in oracle_dirs:
        for name in [f"{key}_redline.pdf", f"{key}_word_redline.pdf"]:
            p = d / name
            if p.exists():
                return p
        hits = sorted(d.glob(f"{key}*redline*.pdf"))
        if hits:
            return hits[0]
    return None


def main() -> None:
    pdf_src = OUT / "pdf"
    cand_dir = OUT / "cand_pdf"
    oracle_dir = OUT / "oracle_pdf"
    work = OUT / "score_work"
    shutil.rmtree(cand_dir, ignore_errors=True)
    shutil.rmtree(oracle_dir, ignore_errors=True)
    shutil.rmtree(work, ignore_errors=True)
    cand_dir.mkdir()
    oracle_dir.mkdir()

    for p in pdf_src.glob("*.pdf"):
        stem = p.stem
        if stem.endswith("_jubarte-rust_redline"):
            key = stem[: -len("_jubarte-rust_redline")]
        else:
            key = stem
        shutil.copy2(p, cand_dir / f"{key}_jubarte-rust_redline.pdf")
        o = find_oracle(key)
        if o:
            shutil.copy2(o, oracle_dir / f"{key}_redline.pdf")

    print(
        "cand",
        len(list(cand_dir.glob("*.pdf"))),
        "oracle",
        len(list(oracle_dir.glob("*.pdf"))),
        flush=True,
    )

    results = pipeline.score_folders_full(
        oracle_dir,
        cand_dir,
        work,
        dpi=144,
        jobs=8,
        candidate_tool="jubarte-rust",
    )
    print("scored", len(results), flush=True)

    restored_scores = m308_scores = None
    for ln in (ROOT / "results/bench.jsonl").read_text().splitlines():
        o = json.loads(ln)
        if o.get("vendor") != "jubarte-rust" or o.get("n_docs", 0) < 700:
            continue
        tv = o.get("tool_version", "")
        if "git.2351844" in tv:
            restored_scores = o["scores"]
        if "git.059808d" in tv:
            m308_scores = o["scores"]

    rows = []
    for k, v in results.items():
        sc = pipeline.overall_from_result(v)
        r0 = restored_scores.get(k) if restored_scores else None
        r1 = m308_scores.get(k) if m308_scores else None
        rows.append(
            {
                "key": k,
                "m308b": sc,
                "restored": r0,
                "m308": r1,
                "d_rest": sc - r0 if r0 is not None else None,
                "d_m308": sc - r1 if r1 is not None else None,
            }
        )

    vals = [r["m308b"] for r in rows]
    drest = [r["d_rest"] for r in rows if r["d_rest"] is not None]
    print(f"\n=== SUBSET n={len(vals)}")
    print(f"mean={statistics.mean(vals):.3f} median={statistics.median(vals):.3f}")
    print(f"vs restored: meanΔ={statistics.mean(drest):+.3f} sumΔ={sum(drest):+.2f}")

    crit = [
        "file_197_file_198",
        "file_2_file_3",
        "file_54_file_55",
        "bullet_list_bold_demo_id_paraid_overflow_bullet_list_demo_id_paraid_overflow",
        "super_editor__broken_list_missing_items_36b4199e_super_editor__multiple_nodes_in_list_79d915a2",
        "super_editor__broken_list_missing_items_36b4199e_super_editor__list_spacer1_06383c66",
        "super_editor__basic_list_0fcfe705_super_editor__sd_1707_list_enter_track_changes_with_fd93fd8b",
    ]
    print("\nCRITICAL:")
    byk = {r["key"]: r for r in rows}
    for c in crit:
        r = byk.get(c)
        if r:
            print(
                f"  m308b={r['m308b']:6.2f} rest={r['restored']:6.2f} "
                f"m308={r['m308']:6.2f} dR={r['d_rest']:+7.2f}  {c[:70]}"
            )
        else:
            print("  MISSING", c)

    rows_sorted = sorted(rows, key=lambda r: r["d_rest"] if r["d_rest"] is not None else 0)
    print("\nworst 10 vs restored:")
    for r in rows_sorted[:10]:
        print(
            f"  {r['d_rest']:+7.2f} m308b={r['m308b']:.1f} rest={r['restored']:.1f} "
            f"m308={r['m308']:.1f}  {r['key'][:60]}"
        )
    print("best 10:")
    for r in rows_sorted[-10:]:
        print(
            f"  {r['d_rest']:+7.2f} m308b={r['m308b']:.1f} rest={r['restored']:.1f} "
            f"m308={r['m308']:.1f}  {r['key'][:60]}"
        )

    (OUT / "scores.json").write_text(json.dumps(rows, indent=2))
    print("wrote", OUT / "scores.json")


if __name__ == "__main__":
    main()

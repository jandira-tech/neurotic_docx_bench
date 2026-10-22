"""Download the bench's Word corpus and Word's fresh compares from Hugging Face.

Git carries only the corpus tables (documents.csv, comparisons.csv, pools, notices, the
manifest). The documents, Word's PDFs of them, and Word's fresh compares live on two
public datasets:

- ``arthrod/neurotic_docx_bench-fixtures``, ``word/`` -> ``corpus/word`` (verified
  against ``corpus/word/MANIFEST.sha256.json``)
- ``arthrod/neurotic_docx_bench``, ``outputs/redlines_0929_full/fresh_compares`` ->
  ``results/compare_regen/out`` with its ``regen_list.csv``

    uv run python scripts/fetch_corpus.py              # both, into this checkout
    uv run python scripts/fetch_corpus.py --no-compare-regen --revision <sha>

No login is needed; HF_TOKEN only adds rate-limit headroom. Files already present and
unchanged are not downloaded again.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from neurotic_docx_bench import hub


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path, default=Path("."), help="the bench checkout (default: .)")
    ap.add_argument("--revision", help="a dataset commit or tag of the fixtures repo (default: main)")
    ap.add_argument(
        "--no-compare-regen",
        action="store_true",
        help="fetch corpus/word only, not results/compare_regen",
    )
    a = ap.parse_args(argv)
    root = a.root.expanduser().resolve()
    api = hub.default_api()
    try:
        report = hub.fetch_word_corpus(root, api=api, revision=a.revision)
        print(f"corpus/word: {report.describe()}")
        if not a.no_compare_regen:
            ids = hub.fetch_compare_regen(root / hub.DEFAULT_COMPARE_REGEN, api=api)
            print(f"{hub.DEFAULT_COMPARE_REGEN}: {len(ids)} fresh compares, regen_list.csv written")
    except hub.ManifestError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

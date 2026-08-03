#!/usr/bin/env python
"""Generate the mutation-probe corpus (seed.docx + one single-mutation DOCX per
probe) and a probes_manifest.csv in the centralized_mapping.csv 12-column shape,
consumable by generate-native-redlines.ts via --manifest/--source-dir.

    uv run python scripts/mutation_probes_gen.py [--seed path.docx] [--out corpus/mutation_probes]
"""

from __future__ import annotations

import argparse
import csv
import io
from pathlib import Path

from neurotic_docx_bench.mutation_probes import ProbeRecord, generate_probes

MANIFEST_COLUMNS = (
    'pair_stem',
    'base',
    'next',
    'origin',
    'docx_source_base',
    'docx_source_next',
    'redline_docx',
    'redline_docx_word',
    'accepted_docx',
    'pdf_redline',
    'pdf_accepted',
    'missing',
)


def manifest_text(records: list[ProbeRecord]) -> str:
    """Manifest CSV text, LF line endings so regeneration never dirties the tree."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=MANIFEST_COLUMNS, lineterminator='\n')
    writer.writeheader()
    for rec in records:
        if not rec.applicable:
            continue
        # Stems in base/next, filenames in docx_source_* — the redline
        # generator joins sourceDir + `${pair.base}.docx`, so it consumes
        # the stems.
        writer.writerow({
            'pair_stem': rec.name,
            'base': 'seed',
            'next': rec.name,
            'origin': 'mutation_probe',
            'docx_source_base': 'seed.docx',
            'docx_source_next': f'{rec.name}.docx',
            'redline_docx': '',
            'redline_docx_word': '',
            'accepted_docx': '',
            'pdf_redline': '',
            'pdf_accepted': '',
            'missing': '',
        })
    return buf.getvalue()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--seed', type=Path, default=None, help='seed DOCX to mutate (default: the built-in synthetic seed)'
    )
    parser.add_argument(
        '--out',
        type=Path,
        default=Path('corpus/mutation_probes'),
        help='output directory for the probe corpus (default: corpus/mutation_probes)',
    )
    args = parser.parse_args(argv)

    records = generate_probes(args.seed, args.out)

    manifest = args.out / 'probes_manifest.csv'
    manifest.write_text(manifest_text(records), newline='')

    applicable = [r for r in records if r.applicable]
    skipped = [r for r in records if not r.applicable]
    print(f'wrote {len(applicable)} probes + seed.docx to {args.out}')
    print(f'manifest: {manifest}')
    for rec in skipped:
        print(f'skipped {rec.name}: {rec.reason}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

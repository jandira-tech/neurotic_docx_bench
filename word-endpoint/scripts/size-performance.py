"""Show hourly request medians within fixed DOCX input-size bands."""
import argparse
from collections import defaultdict
from datetime import datetime
import json
from pathlib import Path
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BANDS = (('<32 KiB', 0, 32768), ('32-64 KiB', 32768, 65536),
         ('64-128 KiB', 65536, 131072), ('128-256 KiB', 131072, 262144),
         ('256-512 KiB', 262144, 524288), ('>=512 KiB', 524288, None))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--since', default=datetime.now().strftime('%Y-%m-%d 00:00:00'))
    parser.add_argument('--until')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    command = [sys.executable, '-B', str(ROOT / 'scripts/performance-audit.py'),
               '--since', args.since, '--include-requests']
    if args.until:
        command += ['--until', args.until]
    audit = json.loads(subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                     encoding='utf-8', check=True, timeout=30).stdout)
    rows = audit.pop('successful_requests')
    hours = sorted({row['at_local'][:13] for row in rows})
    report = {'generated_local': datetime.now().astimezone().isoformat(),
              'since': args.since, 'until_exclusive': args.until,
              'input_size_definition': audit['input_size_definition'],
              'post_statuses': audit['post_statuses'], 'hours': hours, 'endpoints': {}}
    for kind in ('compare', 'compare_pdf', 'convert'):
        selected = [row for row in rows if row['kind'] == kind and 'input_bytes' in row]
        by_band = {}
        for label, lower, upper in BANDS:
            periods = {}
            for hour in hours:
                samples = [row['http_ms'] for row in selected if row['at_local'].startswith(hour)
                           and row['input_bytes'] >= lower
                           and (upper is None or row['input_bytes'] < upper)]
                periods[hour] = {'count': len(samples), 'median_ms': statistics.median(samples) if samples else None}
            by_band[label] = periods
        exact = defaultdict(lambda: defaultdict(list))
        for row in selected:
            exact[row['input_bytes']][row['at_local'][:13]].append(row['http_ms'])
        repeated = {str(size): {hour: {'count': len(samples), 'median_ms': statistics.median(samples)}
                               for hour, samples in sorted(periods.items())}
                    for size, periods in sorted(exact.items()) if len(periods) > 1}
        report['endpoints'][kind] = {'size_bands': by_band, 'repeated_exact_input_sizes': repeated,
                                     'missing_input_size_count': sum(row['kind'] == kind and 'input_bytes' not in row for row in rows)}
    report['limitations'] = ('Successful requests only, including synthetic checks/benchmarks. Hourly cells are independent medians, '
                            'with counts; empty cells are not estimated. Equal compressed bytes do not establish identical '
                            'documents, page counts, comments, revisions or complexity. Last hour is partial. '
                            'No causal attribution to runtime or background load.')
    rendered = json.dumps(report, indent=2)
    if args.output:
        args.output.write_text(rendered + '\n', encoding='utf-8')
    for kind, endpoint in report['endpoints'].items():
        print(kind + ' | ' + ' | '.join(hours))
        for band, periods in endpoint['size_bands'].items():
            if any(cell['count'] for cell in periods.values()):
                print(band + ' | ' + ' | '.join(f"{cell['median_ms']/1000:.2f}s (n={cell['count']})"
                                               if cell['count'] else '-' for cell in periods.values()))
    print('Repeated exact input sizes: ' + json.dumps({kind: row['repeated_exact_input_sizes']
                                                      for kind, row in report['endpoints'].items()}))


if __name__ == '__main__':
    main()

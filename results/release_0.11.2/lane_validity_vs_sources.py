"""Which validator errors in the jubarte lane's redlines are the tool's, and which came with the sources?

For every redline of the lane: the OpenXmlValidator's errors as (id, part) kinds, minus the
kinds either source document already has. Prints the redlines with a kind of their own and
a table of those kinds. Run from the bench root:
  uv run python results/release_0.11.2/lane_validity_vs_sources.py [lane]
"""
import collections
import csv
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

V = str(Path.home() / 'temp/T/jubarte-redlines/tools/validate-docx/bin/Release/net8.0/validate-docx')
R, W = Path('results/redlines_0929_full'), Path('corpus/word')
LANE = sys.argv[1] if len(sys.argv) > 1 else 'jubarte-0.11.2'


def kinds(path: Path) -> collections.Counter:
    if not path.is_file():
        return collections.Counter({('ABSENT', ''): 1})
    out = subprocess.run([V, str(path)], capture_output=True, text=True)
    got = collections.Counter()
    for line in out.stdout.splitlines():
        cells = line.split('\t')
        if len(cells) > 3:
            got[cells[1], cells[3]] += 1
        elif len(cells) > 1:
            got[cells[1], ''] += 1
    if out.returncode not in (0, 1) and not got:
        got['EXIT', str(out.returncode)] += 1
    return got


def one(r: dict) -> tuple[str, collections.Counter, collections.Counter]:
    mine = kinds(R / LANE / 'docx' / f'{r["key"]}_{LANE}.docx')
    if not mine:
        return r['key'], mine, mine
    src = set(kinds(W / f'{r["base"]}.docx')) | set(kinds(W / f'{r["next"]}.docx'))
    return r['key'], mine, collections.Counter({k: n for k, n in mine.items() if k not in src})


rows = list(csv.DictReader(open('results/release_0.11.2_evidence/gen_pairs_sample.csv')))
with ThreadPoolExecutor(3) as pool:
    done = list(pool.map(one, rows))
flagged = [d for d in done if d[1]]
own = [d for d in done if d[2]]
print(f'{LANE}: {len(rows)} redlines; {len(flagged)} with validator errors; {len(own)} with a kind neither source has')
table = collections.Counter()
for key, _, new in own:
    for k in new:
        table[k] += 1
for (err, part), n in table.most_common():
    print(f'  {n:4} redlines  {err}  {part}')
for key, _, new in own:
    print('OWN', key, dict(new))

"""Pick 100 Word tracking redlines for the reject-all set (seed 20260929), none from the accept set.

Same rules as ``select_accept.py`` (stratified by source set, one pair per base first, pairs
touching a document Word refused left out), drawn only from pairs the accept set did not use.
The pool has 65 with-comments redlines and the accept set took 40, so the quota is the 25
left with comments and 75 without. Writes reject_selection.csv.
"""

import csv
import random
from collections import defaultdict
from pathlib import Path

from select_accept import REFUSED, allocate, ids, pick

HERE = Path(__file__).parent
SEED = 20260929
QUOTA = {'with_comments_tracking': 25, 'tracking_without_comments': 75}


def main():
    rng = random.Random(SEED)
    accepted = {r['id'] for r in csv.DictReader(open(HERE / 'accept_selection.csv'))}
    rows = [
        r for r in csv.DictReader(open(HERE / 'pool_pairs.csv')) if not ids(r) & REFUSED and r['id'] not in accepted
    ]
    chosen = []
    for state, quota in QUOTA.items():
        by_set = defaultdict(list)
        for r in rows:
            if r['state'] == state:
                by_set[r['sets']].append(r)
        alloc = allocate({s: len(v) for s, v in by_set.items()}, quota)
        for s in sorted(by_set):
            chosen += pick(by_set[s], alloc[s], rng)
    assert not {r['id'] for r in chosen} & accepted
    with open(HERE / 'reject_selection.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(chosen)
    print(len(chosen), 'selected;', len(REFUSED), 'refused ids excluded;', len(accepted), 'accept ids excluded')


if __name__ == '__main__':
    main()

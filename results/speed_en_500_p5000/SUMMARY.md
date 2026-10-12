# Speed fixtures: representative English documents

- source: `corpus/word/pools/en_pairs_500_renders.csv` (1000 documents)
- English pool: 981 (excluded 19, see excluded.csv)
- picked: 500 (seed 42), stratified by Word page count x structure
- pairs: 5000 distinct base->next, each fixture 10x base and 10x next

| stratum | pool | picked |
| --- | ---: | ---: |
| 10-29p/plain | 12 | 6 |
| 10-29p/rich | 86 | 44 |
| 1p/plain | 87 | 44 |
| 1p/rich | 77 | 39 |
| 2-3p/plain | 159 | 81 |
| 2-3p/rich | 225 | 115 |
| 30p+/plain | 1 | 1 |
| 30p+/rich | 42 | 21 |
| 4-9p/plain | 60 | 31 |
| 4-9p/rich | 232 | 118 |

| measure | pool median | picked median |
| --- | ---: | ---: |
| pages | 3 | 3 |
| words | 672 | 693 |
| tables | 1 | 1 |
| pictures | 1 | 1 |
| bytes | 46902 | 46686 |

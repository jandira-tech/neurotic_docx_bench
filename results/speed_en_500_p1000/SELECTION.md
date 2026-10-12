# How these 1000 pairs were chosen

Source: `../speed_en_500_p5000/pairs.csv` (5000 pairs = 10 rounds of 500; in each round every one of
the 500 fixtures is base once and next once). Candidates were the 45 ways to keep two whole rounds,
so fixture balance holds by construction and no pair was picked by hand.

Rule (fairness to Docxodus): on the metrics where jubarte was the same or worse than Docxodus in the
5000-pair run, the subset must not shrink Docxodus's edge, and it may not carry more Docxodus failures
than the 5000-pair rate (4/5000 → 0 in 1000). Among the subsets that pass, the one closest to the
5000-pair ratios (median, CLI median, Docxodus win share, mean, p95, p99) was taken.

Chosen: rounds 6 and 10 (keys r2501–r3000 and r4501–r5000). Measured on run_5000
(jubarte-rust-inproc vs docxodus-csharp-inproc):

| metric | 5000 pairs | rounds 6+10 |
| --- | ---: | ---: |
| jubarte median / Docxodus median | 1.215 | 1.242 |
| CLI median / Docxodus median | 1.316 | 1.343 |
| pairs Docxodus wins | 58.6% | 59.1% |
| Docxodus mean / jubarte mean | 3.18 | 3.26 |
| Docxodus p95 / jubarte p95 | 2.69 | 2.69 |
| Docxodus p99 / jubarte p99 | 7.02 | 7.71 |
| Docxodus failures | 4 | 0 |

Four subsets passed; no subset was fair in both directions (none also kept jubarte's mean, p95 and
p99 edge from growing). The chosen one leans to Docxodus on median and win share and to jubarte on
p99 (7.7× vs 7.0×); quote the 5000-pair p99 ratio next to it.

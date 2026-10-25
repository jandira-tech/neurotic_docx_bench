# Redline speed, 10,000 planned pairs

One call per pair, engines run one after another on the same machine. Node lanes time an in-memory `compare(base, next)`; `jubarte-rust` spawns the CLI per pair (process start and file I/O included); SuperDoc's SDK is file based (open, compare, apply, save). No redline is kept.
Base size quartile cuts: [10601, 19102, 56197] bytes. Machine state: ENV.txt.
A call past the per-pair timeout (120 s) is a failure; its row keeps the timeout as its time.

## Coverage

- docxodus: 10000 of 10000 planned pairs
- jubarte-rust: 10000 of 10000 planned pairs
- jubarte-rust-inproc: 10000 of 10000 planned pairs
- jubarte-wasm: 10000 of 10000 planned pairs
- superdoc: 10000 of 10000 planned pairs

## Same pairs for every tool

| tool | pairs | n | ok | failed | median ms | mean ms | p95 ms | p99 ms | max ms | ok total s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| docxodus | 10000 common | 10000 | 9933 | 67 | 79.1 | 1731.7 | 7197.7 | 40675.7 | 116815.3 | 17200.6 |
| jubarte-rust | 10000 common | 10000 | 10000 | 0 | 45.0 | 83.0 | 246.8 | 671.7 | 3818.1 | 830.1 |
| jubarte-rust-inproc | 10000 common | 10000 | 10000 | 0 | 38.9 | 74.3 | 234.6 | 621.0 | 3818.8 | 743.3 |
| jubarte-wasm | 10000 common | 10000 | 10000 | 0 | 70.9 | 140.6 | 461.3 | 1202.8 | 5859.9 | 1406.1 |
| superdoc | 10000 common | 10000 | 798 | 9202 | 75.7 | 418.9 | 1623.1 | 6350.0 | 31746.8 | 334.3 |

## By pair category

| tool | category | n | ok | failed | median ms | mean ms | p95 ms | p99 ms | max ms | ok total s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| docxodus | all | 10000 | 9933 | 67 | 79.1 | 1731.7 | 7197.7 | 40675.7 | 116815.3 | 17200.6 |
| docxodus | grid | 5961 | 5928 | 33 | 116.1 | 2064.5 | 8934.3 | 45458.4 | 116815.3 | 12238.5 |
| docxodus | identity | 300 | 300 | 0 | 0.1 | 0.3 | 1.0 | 5.9 | 7.5 | 0.1 |
| docxodus | reverse | 1000 | 990 | 10 | 52.4 | 1317.8 | 4990.0 | 45081.4 | 81329.7 | 1304.6 |
| docxodus | word_compare | 2739 | 2715 | 24 | 45.7 | 1347.1 | 4643.2 | 35400.5 | 109684.8 | 3657.4 |
| jubarte-rust | all | 10000 | 10000 | 0 | 45.0 | 83.0 | 246.8 | 671.7 | 3818.1 | 830.1 |
| jubarte-rust | grid | 5961 | 5961 | 0 | 55.7 | 101.3 | 313.5 | 783.3 | 3028.3 | 604.0 |
| jubarte-rust | identity | 300 | 300 | 0 | 5.2 | 9.0 | 27.2 | 59.8 | 97.7 | 2.7 |
| jubarte-rust | reverse | 1000 | 1000 | 0 | 34.5 | 57.6 | 172.5 | 466.6 | 2546.2 | 57.6 |
| jubarte-rust | word_compare | 2739 | 2739 | 0 | 35.4 | 60.5 | 169.4 | 457.2 | 3818.1 | 165.8 |
| jubarte-rust-inproc | all | 10000 | 10000 | 0 | 38.9 | 74.3 | 234.6 | 621.0 | 3818.8 | 743.3 |
| jubarte-rust-inproc | grid | 5961 | 5961 | 0 | 48.5 | 90.3 | 296.1 | 695.7 | 2992.7 | 538.3 |
| jubarte-rust-inproc | identity | 300 | 300 | 0 | 2.4 | 6.1 | 22.7 | 54.4 | 119.1 | 1.8 |
| jubarte-rust-inproc | reverse | 1000 | 1000 | 0 | 28.5 | 50.9 | 157.8 | 419.1 | 2405.7 | 50.9 |
| jubarte-rust-inproc | word_compare | 2739 | 2739 | 0 | 30.2 | 55.6 | 164.1 | 468.3 | 3818.8 | 152.3 |
| jubarte-wasm | all | 10000 | 10000 | 0 | 70.9 | 140.6 | 461.3 | 1202.8 | 5859.9 | 1406.1 |
| jubarte-wasm | grid | 5961 | 5961 | 0 | 89.2 | 172.7 | 569.7 | 1494.8 | 5305.6 | 1029.5 |
| jubarte-wasm | identity | 300 | 300 | 0 | 4.4 | 18.6 | 76.5 | 294.7 | 474.3 | 5.6 |
| jubarte-wasm | reverse | 1000 | 1000 | 0 | 56.2 | 99.6 | 308.1 | 759.8 | 5146.3 | 99.6 |
| jubarte-wasm | word_compare | 2739 | 2739 | 0 | 54.0 | 99.1 | 295.9 | 793.4 | 5859.9 | 271.4 |
| superdoc | all | 10000 | 798 | 9202 | 75.7 | 418.9 | 1623.1 | 6350.0 | 31746.8 | 334.3 |
| superdoc | grid | 5961 | 16 | 5945 | 93.4 | 336.2 | 3585.5 | 3585.5 | 3585.5 | 5.4 |
| superdoc | identity | 300 | 265 | 35 | 343.2 | 1095.9 | 3403.1 | 12359.0 | 31746.8 | 290.4 |
| superdoc | reverse | 1000 | 144 | 856 | 65.6 | 76.4 | 129.4 | 208.3 | 228.7 | 11.0 |
| superdoc | word_compare | 2739 | 373 | 2366 | 59.0 | 73.7 | 156.1 | 219.3 | 291.8 | 27.5 |

## By base size quartile

| tool | quartile | n | ok | failed | median ms | mean ms | p95 ms | p99 ms | max ms | ok total s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| docxodus | Q1 | 2499 | 2499 | 0 | 21.4 | 216.5 | 435.9 | 4267.3 | 38258.4 | 541.1 |
| docxodus | Q2 | 2497 | 2495 | 2 | 45.5 | 471.0 | 1168.3 | 11683.2 | 77293.0 | 1175.0 |
| docxodus | Q3 | 2502 | 2485 | 17 | 117.9 | 2842.6 | 13489.2 | 65597.5 | 116815.3 | 7063.9 |
| docxodus | Q4 | 2502 | 2454 | 48 | 230.7 | 3431.4 | 19517.9 | 64970.6 | 115067.5 | 8420.6 |
| jubarte-rust | Q1 | 2499 | 2499 | 0 | 11.2 | 36.8 | 121.1 | 342.3 | 3028.3 | 92.0 |
| jubarte-rust | Q2 | 2497 | 2497 | 0 | 26.5 | 48.2 | 136.9 | 467.1 | 2176.4 | 120.3 |
| jubarte-rust | Q3 | 2502 | 2502 | 0 | 59.4 | 87.6 | 208.2 | 599.4 | 2407.2 | 219.2 |
| jubarte-rust | Q4 | 2502 | 2502 | 0 | 113.4 | 159.3 | 450.1 | 1063.5 | 3818.1 | 398.6 |
| jubarte-rust-inproc | Q1 | 2499 | 2499 | 0 | 7.4 | 30.5 | 109.0 | 359.4 | 2016.5 | 76.2 |
| jubarte-rust-inproc | Q2 | 2497 | 2497 | 0 | 21.7 | 41.6 | 125.3 | 419.1 | 1955.6 | 104.0 |
| jubarte-rust-inproc | Q3 | 2502 | 2502 | 0 | 52.4 | 78.9 | 188.1 | 552.5 | 2992.7 | 197.4 |
| jubarte-rust-inproc | Q4 | 2502 | 2502 | 0 | 104.4 | 146.2 | 411.6 | 965.3 | 3818.8 | 365.7 |
| jubarte-wasm | Q1 | 2499 | 2499 | 0 | 12.1 | 58.7 | 211.5 | 615.2 | 3810.8 | 146.7 |
| jubarte-wasm | Q2 | 2497 | 2497 | 0 | 38.9 | 80.1 | 229.5 | 883.2 | 3453.3 | 200.0 |
| jubarte-wasm | Q3 | 2502 | 2502 | 0 | 96.6 | 154.3 | 405.1 | 1182.5 | 4454.4 | 386.0 |
| jubarte-wasm | Q4 | 2502 | 2502 | 0 | 185.1 | 269.2 | 762.0 | 1974.9 | 5859.9 | 673.4 |
| superdoc | Q1 | 2499 | 585 | 1914 | 63.3 | 86.3 | 173.5 | 282.7 | 3585.5 | 50.5 |
| superdoc | Q2 | 2497 | 85 | 2412 | 236.1 | 285.4 | 685.0 | 1512.0 | 1512.0 | 24.3 |
| superdoc | Q3 | 2502 | 73 | 2429 | 696.1 | 1212.9 | 5847.2 | 7270.1 | 7270.1 | 88.5 |
| superdoc | Q4 | 2502 | 55 | 2447 | 1623.1 | 3109.2 | 12359.0 | 31746.8 | 31746.8 | 171.0 |

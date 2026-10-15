# Get Jubarte Rust

Use this map whenever reconciliation work needs the Rust DOCX redline engine.
The canonical source checkout is **`~/T/jubarte-redlines`** (linked in this repo as `src/neurotic_docx_bench/utils/jubarte/jubarte-redlines`, see `scripts/link_engines.sh`). Do not edit or
build from the older Jubarte copies under `ooxmlsdk`, `ooxmlsdk-redline`, or
`jubarte_family`; they are historical checkouts and may be on different
branches.

## Name and ownership map

| Name | Meaning | Authoritative location |
| --- | --- | --- |
| `jubarte-redlines` | Canonical local source folder | `~/T/jubarte-redlines` |
| `jubarte-rs` | GitHub repository name | `https://github.com/arthrod/jubarte-rs` |
| `jubarte` | Cargo package, Rust library, and CLI binary | `~/T/jubarte-redlines` |
| `jubarte-rust` | Benchmark vendor/method name for the native CLI | `bench.yaml` |
| `jubarte-wasm` | Benchmark-owned wasm-bindgen adapter around the same Rust library | `src/neurotic_docx_bench/utils/jubarte/jubarte-wasm` |

`ooxmlsdk-redline` is the retired engine name. `ooxmlsdk` remains a separate
OOXML SDK workspace and must not be used as the Jubarte source-of-truth name.

## Data and build flow

```text
~/T/jubarte-redlines
  Cargo package: jubarte
       |
       +-- cargo build --release
       |     `-- target/release/jubarte
       |             `-- copied to the bench as utils/jubarte/jubarte-rust/redline
       |
       +-- path dependency
             `-- bench utils/jubarte/jubarte-wasm
                    `-- wasm-pack build --target nodejs --release
                           `-- pkg/jubarte_wasm_bg.wasm

bench script_redlines --> generated DOCX --> LibreOffice PDF --> Word-oracle score
bench 5k speed test  --> native CLI and WASM timing distributions
```

The source checkout owns comparison behavior, Rust tests, the native CLI, and
the public Rust API. The benchmark owns adapters, installed binaries, generated
WASM artifacts, fidelity runs, speed runs, and published result tables. Never
fix engine behavior in a copied bench binary or generated WASM glue; change
`~/T/jubarte-redlines`, rebuild, and re-run the benchmark.

## Build and install the native CLI

Run Cargo commands sequentially and use the repository's default `target/`:

```bash
cd src/neurotic_docx_bench/utils/jubarte/jubarte-redlines
cargo build --release

cp target/release/jubarte \
  src/neurotic_docx_bench/utils/jubarte/jubarte-rust/redline
```

The benchmark computes the installed binary's content hash as its version pin.
Record the Jubarte Git commit alongside that hash when publishing results.

## Build the WASM adapter

The adapter uses `~/T/jubarte-redlines` as a local Cargo path dependency:

```bash
cd src/neurotic_docx_bench/utils/jubarte/jubarte-wasm
wasm-pack build --target nodejs --release
```

`wasm-pack` invokes `wasm-opt -O3` through the checked-in release profile. The
generated package is under `pkg/`; do not hand-edit its JavaScript or `.wasm`.

## Verification order

From `~/T/neurotic_docx_bench`:

1. Run `script_redlines` for `jubarte-rust` after installing the native binary.
2. Run `script_redlines` for `jubarte-wasm` after rebuilding the WASM adapter.
3. Require equal per-document scores between native and WASM for the same source
   commit and corpus. A speed win does not excuse a fidelity difference.
4. Run the large-N speed test with 1,000 fixtures and at least 5,000 pairs.
5. Keep fidelity and speed claims separate and link the immutable run report.

```bash
uv run bench run --only jubarte-rust --rerun --no-gate
uv run bench run --only jubarte-wasm --rerun --no-gate

node --import tsx scripts/redline_speed_bench.ts \
  --methods jubarte-wasm,jubarte-rust \
  --fixture-count 1000 --min-pairs 5000 --warmup 50 --reps 1 \
  --no-profile --out results/redline_speed_bench/<run-name>
```

The current native/WASM run and exact commands are documented in the benchmark
repository's `docs/SPEED.md`. Treat those figures as a measured snapshot, not a
timeless performance guarantee.

## Before changing Jubarte

- Confirm `git -C ~/T/jubarte-redlines status --short` is understood before editing.
- Read `~/T/jubarte-redlines/AGENTS.md` and the benchmark `AGENTS.md`.
- Preserve Microsoft Word parity as the primary correctness oracle.
- Push source changes first; then rebuild and pin the consumer artifacts in the
  benchmark commit so every published result can be traced back to source.

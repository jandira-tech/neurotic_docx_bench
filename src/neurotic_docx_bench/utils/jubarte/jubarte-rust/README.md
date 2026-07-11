# jubarte-rust (ooxmlsdk-redline)

Release `redline` binary from the **ooxmlsdk** repo (`crates/ooxmlsdk-redline`).

## Refresh binary

```bash
cd /path/to/ooxmlsdk/crates/ooxmlsdk-redline
cargo build --release --bin redline
cp -f target/release/redline \
  /path/to/neurotic_docx_bench/src/neurotic_docx_bench/utils/jubarte/jubarte-rust/redline
cp -f target/release/redline \
  /path/to/neurotic_docx_bench/src/neurotic_docx_bench/utils/jubarte/jubarte-rust/jubarte
chmod +x redline jubarte
```

## Bench run

```bash
cd neurotic_docx_bench
uv run bench run --only jubarte-rust --rerun
```

Generator: `scripts/generate-native-redlines.ts --method=jubarte-rust --dist=src/neurotic_docx_bench/utils/jubarte/jubarte-rust`

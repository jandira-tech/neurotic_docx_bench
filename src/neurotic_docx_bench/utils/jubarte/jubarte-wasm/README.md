# jubarte-wasm

`wasm-bindgen` package for the canonical **jubarte-redlines**
`compare_documents` implementation (Word-mode redline).

Read `~/T/reconciliation_plan/GET_JUBARTE_RUST.md` before rebuilding. The source
of truth is `~/T/jubarte-redlines`; this adapter and its generated `pkg/` output
belong to the benchmark and must not become an independent engine fork.

## Toolchain (why this one)

| Tool | Role |
|------|------|
| **[wasm-pack](https://rustwasm.github.io/wasm-pack/)** | De-facto Rust→npm WASM creator (`cdylib` + wasm-bindgen glue) |
| **[Binaryen `wasm-opt -O3`](https://github.com/WebAssembly/binaryen)** | Post-link optimizer — maximizes runtime speed (not `-Oz` size) |
| **target `wasm32-unknown-unknown`** | Node / browser host (same class as Docxodus npm WASM) |

wasm-pack + wasm-opt is still the market default for shipping high-performance
Rust compute into Node/V8. WASI+Wasmtime can be faster as a *native* host, but
it is not drop-in for the Docxodus-style “import in Node” path this bench uses.

## Build

```bash
# once: rustup target add wasm32-unknown-unknown
# once: cargo install wasm-pack
# once: brew install binaryen   # wasm-opt
wasm-pack build --target nodejs --release
# → pkg/  (jubarte_wasm.js + jubarte_wasm_bg.wasm)
```

The checked-in Cargo path dependency resolves to `~/T/jubarte-redlines`. After
building, run both `script_redlines` and the 5,000-pair speed lane described in
`../../../../../docs/SPEED.md`; native and WASM fidelity scores must match for
the same source commit before publishing a speed comparison.

## Smoke

```js
import init, { compareDocuments, initPanicHook } from "./pkg/jubarte_wasm.js";
await init();
initPanicHook();
const out = compareDocuments(baseU8, nextU8, "jubarte-wasm");
```

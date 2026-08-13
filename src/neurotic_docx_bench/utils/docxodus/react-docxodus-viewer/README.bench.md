# Bench harness notes (react-docxodus-viewer)

The neurotic-docx-bench `docxodus-playwright-*` runs drive `demo/harness.html` via
Playwright. The viewer must load a **matched pair** of Docxodus JS bindings and
WASM — mixing published registry JS with a different local WASM (or the reverse)
fails to boot the .NET runtime (stuck on "Loading document engine…", or worker 403).
Current pin: **docxodus 9.8.0** (npm package + `public/wasm` copied from that tarball).

## What is wired

| Piece | Path |
|---|---|
| JS + WASM package | npm `docxodus@9.8.0` (see `package.json` → `devDependencies.docxodus`) |
| Served WASM (harness `wasmBasePath`) | `public/wasm/` (copy of the package's `dist/wasm`) |
| Vite allow-list | `node_modules/docxodus` so `docxodus.worker.js` is served (not 403) |
| Version reported in JSONL | `package: "docxodus@9.8.0"` in `bench.yaml` |

## Rebuild matched JS + WASM

From repo root:

```bash
# 1) C# → WASM (needs .NET 10 + Emscripten pack)
cd src/neurotic_docx_bench/utils/docxodus/Docxodus
bash scripts/build-wasm.sh

# 2) TypeScript bindings + worker bundles
cd npm
npm install --no-fund --no-audit
npm run build:ts
npm run build:pagination-bundle
npm run build:session-bundle
npm run build:editor-bundle
npm run build:worker-bundle
# bump package.json version if you want a new tool_version string

# 3) Re-link into the viewer + refresh public/wasm
cd ../react-docxodus-viewer
npm install --no-fund --no-audit
rm -rf public/wasm
cp -R node_modules/docxodus/dist/wasm public/wasm
rm -rf node_modules/.vite
```

Optional: if you change `WmlToHtmlConverter` / other engine code, step 1 is required.
JS-only API changes need steps 2–3 only.

## Known converter fix in the local build

`CalculateSpanWidthForTabs` used to call `DocumentSettingsPart.GetXDocument()` with
no null check. Minimal OOXML packages (no `word/settings.xml`) threw
`ArgumentNullException("part")` and wiped most of `docx_source` on
`visual_rendering`. The vendored C# now treats settings as optional (default tab
stop 720 twips). The harness also injects missing optional parts via
`demo/normalize-docx.ts` as a belt-and-suspenders shim.

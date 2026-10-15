// One vendor compare per process: node --import tsx results/wordcraft_20261014_fresh/one_redline.ts METHOD DIST BASE NEXT OUT
// Uses the bench's own engine loader (scripts/generate-native-redlines.ts), so the call is exactly the
// bench's lane for that method; the version is chosen by DOCXODUS_NODE_MODULES / FOLIO_MODULE_ROOT
// (set by generate_fresh.py to this folder's bin/npm installs). The parent process kills a hang.
import { readFileSync, writeFileSync } from "node:fs";
import { loadEngine } from "../../scripts/generate-native-redlines.ts";
const [method, dist, base, next, out] = process.argv.slice(2);
const engine = await loadEngine(method, dist);
const bytes = await engine(new Uint8Array(readFileSync(base)), new Uint8Array(readFileSync(next)));
writeFileSync(out, bytes);
process.exit(0);

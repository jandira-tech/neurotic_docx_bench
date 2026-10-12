// One docxodus compare per process (site_1011): node --import tsx scripts/_site1011_docxodus_one.ts BASE NEXT OUT
// The bench's own engine loader, so the call is exactly the bench's docxodus lane; the parent kills a hang.
import { readFileSync, writeFileSync } from "node:fs";
import { loadEngine } from "./generate-native-redlines.ts";
const [base, next, out] = process.argv.slice(2);
const engine = await loadEngine("docxodus", "src/neurotic_docx_bench/utils/docxodus");
const bytes = await engine(new Uint8Array(readFileSync(base)), new Uint8Array(readFileSync(next)));
writeFileSync(out, bytes);
process.exit(0);

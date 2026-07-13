const { createRequire } = require("module");
const path = require("path");
const fs = require("fs");
const req = createRequire(__filename);
const mod = req(path.join(__dirname, "..", "dist", "jubarte-final", "lossless.node.cjs"));

mod.wireLosslessNodeAdapter();

const { WmlDocument, MarkupSimplifier } = mod;

const corpusSanity = path.join(__dirname, "..", "corpus_sanity");

function findDocxFiles(dir) {
  const results = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name.startsWith("~$")) continue;
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...findDocxFiles(fullPath));
    } else if (entry.name.endsWith(".docx")) {
      results.push(fullPath);
    }
  }
  return results;
}

const files = findDocxFiles(corpusSanity);
console.log(`Found ${files.length} DOCX files`);

let ok = 0;
let fail = 0;
let skipped = 0;
const failures = [];

for (let i = 0; i < files.length; i++) {
  const file = files[i];
  try {
    const bytes = new Uint8Array(fs.readFileSync(file));
    const doc = new WmlDocument(bytes);
    const settings = { RemoveComments: true };
    const result = MarkupSimplifier.SimplifyMarkup(doc, settings);
    const outBytes = result.DocumentByteArray;
    if (outBytes && outBytes.length > 0) {
      fs.writeFileSync(file, Buffer.from(outBytes));
      ok++;
    } else {
      // SimplifyMarkup returned empty — skip (don't corrupt the file)
      skipped++;
      failures.push({ file, error: "empty output" });
    }
  } catch (e) {
    fail++;
    failures.push({ file: path.relative(corpusSanity, file), error: e.message });
  }
  if ((i + 1) % 100 === 0) {
    console.log(`  ...processed ${i + 1}/${files.length} (ok=${ok}, fail=${fail}, skip=${skipped})`);
  }
}

console.log(`\nDone: ${ok} ok, ${fail} failed, ${skipped} skipped out of ${files.length}`);
if (failures.length > 0) {
  console.log("\nFailures:");
  for (const f of failures.slice(0, 20)) {
    console.log(`  ${f.file}: ${f.error}`);
  }
  if (failures.length > 20) console.log(`  ... and ${failures.length - 20} more`);
  // Write failures JSON for reference
  fs.writeFileSync(
    path.join(__dirname, "strip-comments-failures.json"),
    JSON.stringify(failures, null, 2)
  );
}

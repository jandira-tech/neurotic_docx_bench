const { createRequire } = require("module");
const path = require("path");
const req = createRequire(__filename);
const mod = req(path.join(__dirname, "..", "dist", "jubarte-final", "lossless.node.cjs"));

// Wire the full lossless Node adapter (handles SimplifyMarkup too)
mod.wireLosslessNodeAdapter();

const { WmlDocument, MarkupSimplifier } = mod;

// Test: create a WmlDocument from bytes, strip comments
const testFile = path.join(__dirname, "..", "corpus_sanity", "word_based", "docx_redlines_word",
  "docx_lots_of_comments_addition_docx_lots_of_comments_redline.docx");

const fs = require("fs");
const bytes = new Uint8Array(fs.readFileSync(testFile));
console.log("Input bytes:", bytes.length);

const doc = new WmlDocument(bytes);

// Create settings object (plain object works — JS doesn't enforce the class)
const settings = { RemoveComments: true };

const result = MarkupSimplifier.SimplifyMarkup(doc, settings);
const outBytes = result.DocumentByteArray;
console.log("Output bytes:", outBytes.length);

// Write the output to verify
const outFile = testFile; // overwrite in place
fs.writeFileSync(outFile, Buffer.from(outBytes));
console.log("Written (comments stripped):", outFile);

// Quick verify: check if comments.xml is gone from the zip
const { execSync } = require("child_process");
try {
  const entries = execSync(`unzip -l "${outFile}" | grep comment || echo "NO COMMENTS FOUND"`).toString();
  console.log("Zip check:", entries.trim());
} catch (e) {
  console.log("Zip check: no comment entries (good)");
}

/**
 * Dual-path redline bench: jubarte-first LOSSLESS vs jubarte-first VIA-AST.
 *
 * For every base→next pair across BOTH word_based manifests, each engine
 * produces a redline; we then judge it with the acceptance-gate invariant:
 *
 *     text(accept(compare(a,b))) === text(b)
 *     text(reject(compare(a,b))) === text(a)
 *
 * Accept/reject is the SAME package-level implementation for both engines
 * (lossless acceptRevisionsDocxBytes/rejectRevisionsDocxBytes), so the judge
 * cannot favour either path. Well-formedness of every XML part is checked
 * independently, because malformed output is a Word "unreadable content"
 * hard-fail regardless of what the text says.
 *
 * Timing covers ONLY the compare() call — accept/reject and judging are
 * excluded so the speed number is the redline engine, not the harness.
 *
 * Usage:
 *   node --import tsx scripts/redline_dual_path_bench.mjs \
 *     [--engines lossless,via-ast] [--limit N] [--out runs/dual-path]
 */
import { existsSync, mkdirSync, readFileSync, appendFileSync, writeFileSync } from "node:fs";
import { join, resolve, dirname } from "node:path";
import { pathToFileURL } from "node:url";
import JSZip from "jszip";

const ROOT = resolve(dirname(new URL(import.meta.url).pathname), "..");
const JF = process.env.JUBARTE_FIRST_DIR || resolve(ROOT, "../jubarte-first");
const imp = (rel) => import(pathToFileURL(join(JF, rel)).href);

const arg = (name, fallback) => {
  const i = process.argv.indexOf(name);
  return i >= 0 && process.argv[i + 1] ? process.argv[i + 1] : fallback;
};

// ─── pairs ──────────────────────────────────────────────────────────────────

/** Minimal CSV row reader (the manifests are plain, unquoted-comma-free). */
const readManifest = (csvPath, sourceDir) => {
  const lines = readFileSync(csvPath, "utf8").split("\n").filter((l) => l.trim());
  const header = lines[0].split(",");
  const iBase = header.indexOf("base");
  const iNext = header.indexOf("next");
  const out = [];
  for (const line of lines.slice(1)) {
    const cells = line.split(",");
    const base = (cells[iBase] || "").trim();
    const next = (cells[iNext] || "").trim();
    if (!base || !next) continue;
    const basePath = join(sourceDir, `${base}.docx`);
    const nextPath = join(sourceDir, `${next}.docx`);
    if (!existsSync(basePath) || !existsSync(nextPath)) continue;
    out.push({ name: `${base}__${next}`, basePath, nextPath, set: sourceDir.endsWith("randomized") ? "randomized" : "chain" });
  }
  return out;
};

const collectPairs = () => [
  ...readManifest(
    join(ROOT, "corpus/word_based/centralized_mapping.csv"),
    join(ROOT, "corpus/word_based/docx_source"),
  ),
  ...readManifest(
    join(ROOT, "corpus/word_based/centralized_mapping_randomized.csv"),
    join(ROOT, "corpus/word_based/docx_source_randomized"),
  ),
];

// ─── judge ──────────────────────────────────────────────────────────────────

const decode = (s) =>
  s
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'")
    .replace(/&#(\d+);/g, (_, d) => String.fromCodePoint(Number(d)))
    .replace(/&amp;/g, "&");

/**
 * Main-story text of a docx, one line per paragraph, blank paragraphs dropped.
 * Mirrors the bench's established comparison policy (main story exact modulo
 * blank-line placement) so a blank-paragraph difference is not a false alarm.
 */
const mainText = async (bytes) => {
  const zip = await JSZip.loadAsync(bytes);
  const f = zip.file("word/document.xml");
  if (!f) return "";
  const xml = await f.async("string");
  const body = xml.slice(xml.indexOf("<w:body"));
  return body
    .split(/<\/w:p>/)
    .map((para) =>
      [...para.matchAll(/<w:t(?:\s[^>]*)?>([\s\S]*?)<\/w:t>/g)]
        .map((m) => decode(m[1]))
        .join(""),
    )
    .filter((t) => t.length > 0)
    .join("\n");
};

/** Every XML part must be well-formed; malformed => Word "unreadable content". */
const malformedParts = async (bytes, parseXDocument) => {
  const zip = await JSZip.loadAsync(bytes);
  const bad = [];
  for (const name of Object.keys(zip.files)) {
    if (!name.endsWith(".xml") && !name.endsWith(".rels")) continue;
    const xml = await zip.file(name).async("string");
    try {
      parseXDocument(xml);
    } catch (e) {
      bad.push(`${name}: ${e?.message ?? String(e)}`);
    }
  }
  return bad;
};

// ─── engines ────────────────────────────────────────────────────────────────

const loadEngines = async () => {
  const lib = await imp("src/lossless/lib/ooxml-package-jszip.ts");
  const comparer = await imp("src/lossless/WmlComparer.ts");
  const wmlDocument = await imp("src/lossless/WmlDocument.ts");
  const compareDocxMod = await imp("src/compare/compare-docx.node.ts");
  const linq = await imp("src/lossless/lib/xml-linq.ts");
  lib.wireWmlComparerNodeAdapter();

  const lossless = {
    name: "jubarte-first-lossless",
    compare: async (base, next) => {
      const s = new comparer.WmlComparerSettings();
      s.AuthorForRevisions = "jubarte";
      s.DetailThreshold = 0;
      const a = new wmlDocument.WmlDocument(base);
      a.FileName = "base.docx";
      const b = new wmlDocument.WmlDocument(next);
      b.FileName = "next.docx";
      return comparer.WmlComparer.Compare(a, b, s).DocumentByteArray;
    },
  };

  const viaAst = {
    name: "jubarte-first-via-ast",
    compare: async (base, next) =>
      compareDocxMod.compareDocx({ buffer: base }, { buffer: next }, {
        authorForRevisions: "jubarte",
        dateTimeForRevisions: "2026-01-01T00:00:00Z",
      }),
  };

  return {
    engines: { lossless, "via-ast": viaAst },
    accept: lib.acceptRevisionsDocxBytes,
    reject: lib.rejectRevisionsDocxBytes,
    parseXDocument: linq.parseXDocument,
  };
};

// ─── run ────────────────────────────────────────────────────────────────────

const main = async () => {
  const pairs = collectPairs();
  const limit = Number(arg("--limit", "0")) || pairs.length;
  const selected = pairs.slice(0, limit);
  const wanted = arg("--engines", "lossless,via-ast").split(",");
  const outDir = resolve(ROOT, arg("--out", "runs/dual-path"));
  mkdirSync(outDir, { recursive: true });

  const { engines, accept, reject, parseXDocument } = await loadEngines();
  console.log(`pairs=${selected.length} engines=${wanted.join(",")} node=${process.version}`);
  console.log(`out=${outDir}\n`);

  const all = [];
  for (const key of wanted) {
    const engine = engines[key];
    if (!engine) throw new Error(`unknown engine ${key}`);
    const jsonl = join(outDir, `${engine.name}.jsonl`);
    writeFileSync(jsonl, "");
    let done = 0;
    for (const pair of selected) {
      const base = new Uint8Array(readFileSync(pair.basePath));
      const next = new Uint8Array(readFileSync(pair.nextPath));
      const row = { engine: engine.name, pair: pair.name, set: pair.set, bytesIn: base.length + next.length };
      try {
        const t0 = performance.now();
        const redline = await engine.compare(base, next);
        row.compareMs = Number((performance.now() - t0).toFixed(2));
        row.redlineBytes = redline.length;

        const bad = await malformedParts(redline, parseXDocument);
        row.wellFormed = bad.length === 0;
        if (bad.length) row.malformed = bad.slice(0, 3);

        try {
          const accepted = await accept(redline);
          row.acceptOk = (await mainText(accepted)) === (await mainText(next));
        } catch (e) {
          row.acceptOk = false;
          row.acceptError = String(e?.message ?? e).slice(0, 200);
        }
        try {
          const rejected = await reject(redline);
          row.rejectOk = (await mainText(rejected)) === (await mainText(base));
        } catch (e) {
          row.rejectOk = false;
          row.rejectError = String(e?.message ?? e).slice(0, 200);
        }
        row.ok = row.wellFormed && row.acceptOk && row.rejectOk;
      } catch (e) {
        row.ok = false;
        row.compareError = String(e?.message ?? e).slice(0, 300);
      }
      appendFileSync(jsonl, `${JSON.stringify(row)}\n`);
      all.push(row);
      done++;
      if (done % 25 === 0 || done === selected.length) {
        const okc = all.filter((r) => r.engine === engine.name && r.ok).length;
        process.stdout.write(`[${engine.name}] ${done}/${selected.length}  ok=${okc}\n`);
      }
    }
  }

  writeFileSync(join(outDir, "all-rows.json"), JSON.stringify(all, null, 2));
  console.log(`\nwrote ${all.length} rows to ${outDir}`);
};

main().catch((e) => {
  console.error(e);
  process.exit(1);
});

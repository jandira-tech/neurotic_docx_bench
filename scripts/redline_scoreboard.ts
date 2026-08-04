/**
 * D-2: cross-engine accept/reject scoreboard (plan §4, Task D-2).
 *
 * For every base→next pair in the corpus manifest and every engine, generate a
 * redline, materialize accept-all / reject-all, and judge them through THREE
 * lenses; pass-rates land as a scoreboard in RESULTS.md so a fidelity
 * regression in EITHER engine shows up as a diff in a committed file.
 *
 * The three lenses (triangulation — see TODO.md §4; both failure directions
 * shipped once: folio's resolver bug failed a correct engine, and an engine's
 * own reject masked its paragraph-mark defect from its self-tests):
 *   1. ENGINE lens — the engine's own accept/reject outputs, text-compared to
 *      next/base via folio's XML-direct extractor (`redline-lossless-verify`).
 *   2. FOLIO lens — folio's `FolioDocxReviewer` views of the same redline
 *      (`final` = accept-all, `original` = reject-all) against base/next.
 *   3. WORD lens (WV-1, optional) — `bench word-validate` on a sample of
 *      accepted outputs (macOS + Word only).
 * Lenses that both ran and disagree on a pair are the ALARM: the row is
 * flagged and the job exits non-zero.
 *
 * HARD PIN (A-4 mandate): every row must carry an engine pin, the corpus
 * vintage (last commit touching the corpus dir), and the bench source commit.
 * A row without them throws `MissingEnginePinError` — "unknown engine" rows
 * cannot land in RESULTS.md. The git fallback for a pin only applies to engine
 * checkouts OUTSIDE this repo; vendored dists must carry ENGINE_COMMIT.txt.
 *
 * Usage (scheduled job):
 *   node --import tsx scripts/redline_scoreboard.ts \
 *     [--engines jubarte-native,jubarte-first-lossless] [--limit N] \
 *     [--manifest corpus/word_based/centralized_mapping_randomized.csv] \
 *     [--source-dir corpus/word_based/docx_source_randomized] \
 *     [--jubarte-cli ../jubarte-redlines/target/release/jubarte] \
 *     [--jubarte-first-dir ../jubarte-first] [--folio-dir <folio checkout>] \
 *     [--word-validate] [--update-results] [--out runs/d2-scoreboard]
 */
import { execFileSync, spawnSync } from "node:child_process";
import {
	appendFileSync,
	existsSync,
	mkdirSync,
	readFileSync,
	statSync,
	writeFileSync,
} from "node:fs";
import { dirname, isAbsolute, join, resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { parseManifest, type Pair } from "./generate-native-redlines.ts";

const ROOT = resolve(dirname(new URL(import.meta.url).pathname), "..");

// ─── contract types ─────────────────────────────────────────────────────────

export type LensVerdict =
	| { ran: false }
	| { ran: true; acceptOk: boolean; rejectOk: boolean; detail?: string };

export type WordLensVerdict = {
	sampled: number;
	valid: number;
	invalid: number;
	unjudgeable?: number;
	unavailable: boolean;
};

export type ScoreboardRow = {
	pair: string;
	engine: string;
	enginePin: string;
	corpusVintage: string;
	benchCommit: string;
	folioCommit?: string;
	engineLens: LensVerdict;
	folioLens: LensVerdict;
	wordLens?: WordLensVerdict;
	disagreement: boolean;
};

export class MissingEnginePinError extends Error {
	constructor(message: string) {
		super(message);
		this.name = "MissingEnginePinError";
	}
}

// ─── row construction (hard pin) ────────────────────────────────────────────

const lensPassed = (v: LensVerdict): boolean => v.ran && v.acceptOk && v.rejectOk;

/** Lenses that both ran and reached opposite verdicts are the alarm. */
export const detectLensDisagreement = (a: LensVerdict, b: LensVerdict): boolean => {
	if (!a.ran || !b.ran) return false;
	return lensPassed(a) !== lensPassed(b);
};

export type ScoreboardRowInput = {
	pair: string;
	engine: string;
	enginePin: string;
	corpusVintage: string;
	benchCommit: string;
	folioCommit?: string;
	engineLens: LensVerdict;
	folioLens: LensVerdict;
	wordLens?: WordLensVerdict;
};

export const buildScoreboardRow = (input: ScoreboardRowInput): ScoreboardRow => {
	for (const field of ["enginePin", "corpusVintage", "benchCommit"] as const) {
		const value = input[field];
		if (typeof value !== "string" || value.trim().length === 0) {
			throw new MissingEnginePinError(
				`scoreboard row for ${input.engine}/${input.pair} is missing ${field}; ` +
					"rows without full provenance are refused (A-4 hard pin)",
			);
		}
	}
	return {
		pair: input.pair,
		engine: input.engine,
		enginePin: input.enginePin,
		corpusVintage: input.corpusVintage,
		benchCommit: input.benchCommit,
		folioCommit: input.folioCommit,
		engineLens: input.engineLens,
		folioLens: input.folioLens,
		wordLens: input.wordLens,
		disagreement: detectLensDisagreement(input.engineLens, input.folioLens),
	};
};

export const writeScoreboardRow = (path: string, row: ScoreboardRow): void => {
	mkdirSync(dirname(path), { recursive: true });
	appendFileSync(path, `${JSON.stringify(row)}\n`);
};

// ─── provenance resolution ──────────────────────────────────────────────────

const git = (cwd: string, ...args: string[]): string =>
	execFileSync("git", ["-C", cwd, ...args], { encoding: "utf8" }).trim();

/** Last commit touching the corpus dir — the corpus vintage. */
export const resolveCorpusVintage = (corpusDir: string, repoRoot: string = ROOT): string => {
	const vintage = git(repoRoot, "log", "-1", "--format=%h", "--", corpusDir);
	if (!vintage) {
		throw new MissingEnginePinError(`no commit history for corpus dir ${corpusDir}`);
	}
	return vintage;
};

/**
 * Engine pin: ENGINE_COMMIT.txt beside the artifact (or an ancestor), else the
 * HEAD of the git checkout CONTAINING the artifact — but only when that
 * checkout is not this bench repo itself (a vendored dist inside the bench
 * must carry its own pin; the bench commit does not identify an engine build).
 */
export const resolveEnginePin = (artifactPath: string): string => {
	const abs = resolve(ROOT, artifactPath);
	const start = statSync(abs, { throwIfNoEntry: false })?.isDirectory() ? abs : dirname(abs);
	for (let dir = start; ; dir = dirname(dir)) {
		const pinFile = join(dir, "ENGINE_COMMIT.txt");
		if (existsSync(pinFile)) {
			const pin = readFileSync(pinFile, "utf8").trim().split(/\s+/)[0];
			if (pin) return pin;
		}
		if (dirname(dir) === dir) break;
	}
	try {
		const engineRepo = git(start, "rev-parse", "--show-toplevel");
		if (engineRepo && resolve(engineRepo) !== resolve(ROOT)) {
			return git(start, "rev-parse", "--short=7", "HEAD");
		}
	} catch {
		// not inside a git checkout — fall through to the refusal
	}
	throw new MissingEnginePinError(
		`no engine pin for ${artifactPath}: add ENGINE_COMMIT.txt beside the artifact ` +
			"or point at an engine checkout (A-4 hard pin)",
	);
};

// ─── RESULTS.md scoreboard section ──────────────────────────────────────────

const BEGIN = "<!-- D2_SCOREBOARD:BEGIN -->";
const END = "<!-- D2_SCOREBOARD:END -->";
const SPEED_HEADING = "## Redline generation speed";

export type ScoreboardMeta = { runId: string; date: string };

export const renderScoreboardSection = (rows: ScoreboardRow[], meta: ScoreboardMeta): string => {
	const engines = [...new Set(rows.map((r) => r.engine))];
	const lines: string[] = [];
	lines.push("## Accept/reject scoreboard (D-2)");
	lines.push("");
	lines.push(
		`Run \`${meta.runId}\` (${meta.date}). Each pair: engine redline → accept-all/reject-all, ` +
			"judged by the engine's own outputs (folio XML-direct text), folio's reviewer views, " +
			"and a WV-1 Word sample. **Lens disagreement is the alarm.**",
	);
	lines.push("");
	lines.push(
		"| engine | engine pin | corpus vintage | bench commit | folio commit | pairs | engine lens | folio lens | disagreements | word sample |",
	);
	lines.push("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |");
	for (const engine of engines) {
		const engineRows = rows.filter((r) => r.engine === engine);
		const first = engineRows[0];
		const engineRan = engineRows.filter((r) => r.engineLens.ran);
		const folioRan = engineRows.filter((r) => r.folioLens.ran);
		const enginePass = engineRows.filter((r) => lensPassed(r.engineLens)).length;
		const folioPass = engineRows.filter((r) => lensPassed(r.folioLens)).length;
		const disagreements = engineRows.filter((r) => r.disagreement).length;
		const word = engineRows.find((r) => r.wordLens && !r.wordLens.unavailable)?.wordLens;
		const wordCell = word
			? `${word.valid}/${word.sampled} valid` +
				(word.unjudgeable ? ` (${word.unjudgeable} unjudgeable)` : "")
			: engineRows.some((r) => r.wordLens?.unavailable)
				? "unavailable"
				: "—";
		lines.push(
			`| ${engine} | \`${first.enginePin}\` | \`${first.corpusVintage}\` | \`${first.benchCommit}\` | ` +
				`${first.folioCommit ? `\`${first.folioCommit}\`` : "—"} | ${engineRows.length} | ` +
				`${enginePass}/${engineRan.length} | ${folioPass}/${folioRan.length} | ${disagreements} | ${wordCell} |`,
		);
	}
	const alarms = rows.filter((r) => r.disagreement);
	if (alarms.length > 0) {
		lines.push("");
		lines.push(`⚠️ ${alarms.length} pair(s) with lens disagreement:`);
		for (const row of alarms.slice(0, 20)) {
			lines.push(
				`- \`${row.pair}\` (${row.engine}): engine lens ${lensPassed(row.engineLens) ? "pass" : "FAIL"}, ` +
					`folio lens ${lensPassed(row.folioLens) ? "pass" : "FAIL"}`,
			);
		}
	}
	lines.push("");
	return lines.join("\n");
};

export const updateResultsScoreboard = (
	resultsPath: string,
	rows: ScoreboardRow[],
	meta: ScoreboardMeta,
): void => {
	const section = `${BEGIN}\n${renderScoreboardSection(rows, meta)}\n${END}`;
	const current = readFileSync(resultsPath, "utf8");
	let next: string;
	if (current.includes(BEGIN) && current.includes(END)) {
		const before = current.slice(0, current.indexOf(BEGIN));
		const after = current.slice(current.indexOf(END) + END.length);
		next = `${before}${section}${after}`;
	} else if (current.includes(SPEED_HEADING)) {
		next = current.replace(SPEED_HEADING, `${section}\n\n${SPEED_HEADING}`);
	} else {
		next = `${current.trimEnd()}\n\n${section}\n`;
	}
	writeFileSync(resultsPath, next);
};

// ─── engines ────────────────────────────────────────────────────────────────

type EngineDriver = {
	name: string;
	pin: string;
	compare: (base: Uint8Array, next: Uint8Array) => Promise<Uint8Array>;
	accept: (redline: Uint8Array) => Promise<Uint8Array>;
	reject: (redline: Uint8Array) => Promise<Uint8Array>;
};

const importFrom = async (base: string, rel: string): Promise<Record<string, unknown>> =>
	import(pathToFileURL(join(base, rel)).href) as Promise<Record<string, unknown>>;

const runCli = (cli: string, args: string[]): void => {
	const proc = spawnSync(cli, args, { encoding: "utf8" });
	if (proc.status !== 0) {
		throw new Error(
			`${cli} ${args.join(" ")} exited ${proc.status}: ${proc.stderr || proc.stdout}`,
		);
	}
};

const loadNativeEngine = (cli: string, scratch: string): EngineDriver => {
	const pin = resolveEnginePin(cli);
	let n = 0;
	const tmp = (name: string): string => join(scratch, `native-${n++}-${name}`);
	const viaFiles = (
		run: (input: string[], out: string) => void,
		inputs: Uint8Array[],
		label: string,
	): Uint8Array => {
		const inPaths = inputs.map((bytes, i) => {
			const p = tmp(`${label}-in${i}.docx`);
			writeFileSync(p, bytes);
			return p;
		});
		const out = tmp(`${label}-out.docx`);
		run(inPaths, out);
		return new Uint8Array(readFileSync(out));
	};
	return {
		name: "jubarte-native",
		pin,
		compare: async (base, next) =>
			viaFiles((i, o) => runCli(cli, [i[0], i[1], "-o", o, "--force", "-q"]), [base, next], "cmp"),
		accept: async (redline) =>
			viaFiles((i, o) => runCli(cli, ["accept", i[0], "-o", o, "--force"]), [redline], "acc"),
		reject: async (redline) =>
			viaFiles((i, o) => runCli(cli, ["reject", i[0], "-o", o, "--force"]), [redline], "rej"),
	};
};

const loadLosslessEngine = async (jubarteFirstDir: string): Promise<EngineDriver> => {
	const pin = resolveEnginePin(jubarteFirstDir);
	const lib = await importFrom(jubarteFirstDir, "src/lossless/lib/ooxml-package-jszip.ts");
	const comparer = await importFrom(jubarteFirstDir, "src/lossless/WmlComparer.ts");
	const wmlDocument = await importFrom(jubarteFirstDir, "src/lossless/WmlDocument.ts");
	(lib.wireWmlComparerNodeAdapter as () => void)();
	const WmlComparer = comparer.WmlComparer as {
		Compare: (a: unknown, b: unknown, s: unknown) => { DocumentByteArray: Uint8Array };
	};
	const WmlComparerSettings = comparer.WmlComparerSettings as new () => {
		AuthorForRevisions: string;
		DetailThreshold: number;
	};
	const WmlDocument = wmlDocument.WmlDocument as new (bytes: Uint8Array) => { FileName: string };
	const accept = lib.acceptRevisionsDocxBytes as (bytes: Uint8Array) => Uint8Array;
	const reject = lib.rejectRevisionsDocxBytes as (bytes: Uint8Array) => Uint8Array;
	return {
		name: "jubarte-first-lossless",
		pin,
		compare: async (base, next) => {
			const settings = new WmlComparerSettings();
			settings.AuthorForRevisions = "jubarte";
			// Match the public lossless surface (DocumentComparer.CompareDocuments).
			settings.DetailThreshold = 0;
			const a = new WmlDocument(base);
			a.FileName = "base.docx";
			const b = new WmlDocument(next);
			b.FileName = "next.docx";
			return WmlComparer.Compare(a, b, settings).DocumentByteArray;
		},
		accept: async (redline) => accept(redline),
		reject: async (redline) => reject(redline),
	};
};

// ─── lenses ─────────────────────────────────────────────────────────────────

const toArrayBuffer = (bytes: Uint8Array): ArrayBuffer =>
	bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer;

type FolioJudge = {
	folioCommit: string;
	/** Lens 1 medium: engine outputs, folio XML-direct text comparison. */
	compareEngineOutputs: (views: {
		accepted: Uint8Array;
		rejected: Uint8Array;
		base: Uint8Array;
		revised: Uint8Array;
	}) => Promise<string | null>;
	/** Lens 2: folio reviewer views of the redline vs base/next main text. */
	compareReviewerViews: (
		redline: Uint8Array,
		base: Uint8Array,
		revised: Uint8Array,
	) => Promise<string | null>;
};

const loadFolioJudge = async (folioDir: string): Promise<FolioJudge> => {
	const folioCommit = git(folioDir, "rev-parse", "--short=7", "HEAD");
	const verify = await importFrom(folioDir, "packages/core/src/redline-lossless-verify.ts");
	const server = await importFrom(folioDir, "packages/core/src/server.ts");
	const extract = verify.extractComparableDocxContent as (
		docx: ArrayBuffer,
	) => Promise<unknown>;
	const compare = verify.compareLossless as (options: {
		accepted: unknown;
		rejected: unknown;
		base: unknown;
		revised: unknown;
	}) => string | null;
	const Reviewer = server.FolioDocxReviewer as {
		fromBuffer: (buffer: ArrayBuffer) => Promise<{
			listStories: () => { handle: { type: string } }[];
			readReviewedStory: (options: { story: unknown; view: "final" | "original" }) => {
				snapshot: { blocks: { text: string }[] };
			} | null;
		}>;
	};
	const mainText = async (bytes: Uint8Array, view: "final" | "original"): Promise<string> => {
		const reviewer = await Reviewer.fromBuffer(toArrayBuffer(bytes));
		for (const { handle } of reviewer.listStories()) {
			if (handle.type !== "main") continue;
			const story = reviewer.readReviewedStory({ story: handle, view });
			if (!story) return "";
			// Match compareLossless's comparison policy (main story exact modulo
			// blank-line placement): empty blocks are dropped there too, so a
			// blank-paragraph placement difference must not read as a lens
			// disagreement.
			return story.snapshot.blocks
				.map(({ text }) => text)
				.filter((text) => text.length > 0)
				.join("\n");
		}
		return "";
	};
	return {
		folioCommit,
		compareEngineOutputs: async ({ accepted, rejected, base, revised }) =>
			compare({
				accepted: await extract(toArrayBuffer(accepted)),
				rejected: await extract(toArrayBuffer(rejected)),
				base: await extract(toArrayBuffer(base)),
				revised: await extract(toArrayBuffer(revised)),
			}),
		compareReviewerViews: async (redline, base, revised) => {
			const [acceptedText, rejectedText, baseText, revisedText] = await Promise.all([
				mainText(redline, "final"),
				mainText(redline, "original"),
				mainText(base, "final"),
				mainText(revised, "final"),
			]);
			if (acceptedText !== revisedText) {
				return "reviewer accept-all view diverges from the revised document";
			}
			if (rejectedText !== baseText) {
				return "reviewer reject-all view diverges from the base document";
			}
			return null;
		},
	};
};

/**
 * WV-1 sample: run `bench word-validate` over a dir of accepted outputs.
 *
 * A wholly-invalid sample retries ONCE (historical stopgap for the timeout ≠
 * dialog confusion — TODO.md §1; observed live in the first D-2 sweep, where
 * 0/5 lossless "invalid" re-validated 5/5 minutes later). WV-1 now detects an
 * ACTUAL modal via System Events and reports slow opens as UNJUDGEABLE instead
 * of invalid, so wholesale false-invalid sweeps should no longer occur; the
 * retry stays as a cheap belt-and-suspenders for invalid verdicts.
 */
/**
 * Parse `bench word-validate` per-doc output. UNJUDGEABLE (budget exhausted, no
 * modal observed — Word merely slow) is its own outcome, reported separately;
 * it contains no "VALID" substring so the valid arithmetic is unaffected.
 */
export const parseWordValidateOutput = (
	stdout: string,
	sampled: number,
): WordLensVerdict => {
	const validSubstrings = (stdout.match(/VALID/g) ?? []).length;
	const invalid = (stdout.match(/INVALID/g) ?? []).length;
	const unjudgeable = (stdout.match(/UNJUDGEABLE/g) ?? []).length;
	return { sampled, valid: validSubstrings - invalid, invalid, unjudgeable, unavailable: false };
};

export const runWordSample = (sampleDir: string, sampled: number): WordLensVerdict => {
	const attempt = (): WordLensVerdict => {
		const proc = spawnSync("uv", ["run", "bench", "word-validate", sampleDir], {
			cwd: ROOT,
			encoding: "utf8",
			timeout: 15 * 60 * 1000,
		});
		if (proc.error || proc.status === 2) {
			return { sampled, valid: 0, invalid: 0, unavailable: true };
		}
		return parseWordValidateOutput(proc.stdout, sampled);
	};
	const first = attempt();
	if (first.unavailable || first.valid > 0) return first;
	return attempt();
};

// ─── the job ────────────────────────────────────────────────────────────────

export type ScoreboardJobOptions = {
	manifest: string;
	sourceDir: string;
	engines: string[];
	limit?: number;
	outDir: string;
	jubarteCli: string;
	jubarteFirstDir: string;
	folioDir: string;
	wordValidate: boolean;
	wordSampleCount: number;
	updateResults: boolean;
	resultsPath: string;
};

export const runScoreboard = async (options: ScoreboardJobOptions): Promise<ScoreboardRow[]> => {
	const runId = `d2-${new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19)}`;
	const runDir = join(options.outDir, runId);
	mkdirSync(runDir, { recursive: true });
	const jsonl = join(runDir, "scoreboard.jsonl");
	const benchCommit = git(ROOT, "rev-parse", "--short=7", "HEAD");
	const corpusVintage = resolveCorpusVintage(dirname(resolve(ROOT, options.manifest)));
	const judge = await loadFolioJudge(options.folioDir);

	let pairs = parseManifest(resolve(ROOT, options.manifest), ["ok"]).filter(
		(p: Pair) =>
			existsSync(join(options.sourceDir, `${p.base}.docx`)) &&
			existsSync(join(options.sourceDir, `${p.next}.docx`)),
	);
	if (options.limit) pairs = pairs.slice(0, options.limit);

	const rows: ScoreboardRow[] = [];
	for (const engineName of options.engines) {
		const scratch = join(runDir, engineName);
		mkdirSync(scratch, { recursive: true });
		const engine =
			engineName === "jubarte-native"
				? loadNativeEngine(resolve(ROOT, options.jubarteCli), scratch)
				: engineName === "jubarte-first-lossless"
					? await loadLosslessEngine(resolve(ROOT, options.jubarteFirstDir))
					: null;
		if (!engine) throw new Error(`unknown engine ${engineName}`);

		const sampleDir = join(scratch, "word-sample");
		let sampledCount = 0;
		for (const pair of pairs) {
			const pairName = `${pair.base}_${pair.next}`;
			const base = new Uint8Array(readFileSync(join(options.sourceDir, `${pair.base}.docx`)));
			const next = new Uint8Array(readFileSync(join(options.sourceDir, `${pair.next}.docx`)));
			let engineLens: LensVerdict;
			let folioLens: LensVerdict;
			try {
				const redline = await engine.compare(base, next);
				const accepted = await engine.accept(redline);
				const rejected = await engine.reject(redline);
				const engineMismatch = await judge.compareEngineOutputs({
					accepted,
					rejected,
					base,
					revised: next,
				});
				const acceptOk = !engineMismatch?.includes("accept-all");
				const rejectOk = !engineMismatch?.includes("reject-all");
				engineLens = {
					ran: true,
					acceptOk: engineMismatch === null ? true : acceptOk,
					rejectOk: engineMismatch === null ? true : rejectOk,
					detail: engineMismatch ?? undefined,
				};
				let folioMismatch: string | null = null;
				try {
					folioMismatch = await judge.compareReviewerViews(redline, base, next);
					folioLens = {
						ran: true,
						acceptOk: !folioMismatch?.includes("accept-all"),
						rejectOk: !folioMismatch?.includes("reject-all"),
						detail: folioMismatch ?? undefined,
					};
				} catch (error) {
					folioLens = {
						ran: true,
						acceptOk: false,
						rejectOk: false,
						detail: `reviewer failed: ${String(error)}`,
					};
				}
				if (options.wordValidate && sampledCount < options.wordSampleCount) {
					mkdirSync(sampleDir, { recursive: true });
					writeFileSync(join(sampleDir, `${pairName}_${engineName}_accepted.docx`), accepted);
					sampledCount++;
				}
			} catch (error) {
				engineLens = { ran: true, acceptOk: false, rejectOk: false, detail: String(error) };
				folioLens = { ran: false };
			}
			const row = buildScoreboardRow({
				pair: pairName,
				engine: engine.name,
				enginePin: engine.pin,
				corpusVintage,
				benchCommit,
				folioCommit: judge.folioCommit,
				engineLens,
				folioLens,
			});
			rows.push(row);
			writeScoreboardRow(jsonl, row);
			const mark = row.disagreement ? "⚠︎DISAGREE" : lensPassed(engineLens) ? "ok" : "FAIL";
			console.log(`[${engine.name}] ${pairName}: ${mark}`);
		}
		if (options.wordValidate && sampledCount > 0) {
			const word = runWordSample(sampleDir, sampledCount);
			const engineRows = rows.filter((r) => r.engine === engine.name);
			for (const row of engineRows) row.wordLens = word;
		}
	}

	const meta: ScoreboardMeta = { runId, date: new Date().toISOString().slice(0, 10) };
	writeFileSync(join(runDir, "summary.md"), renderScoreboardSection(rows, meta));
	if (options.updateResults) {
		updateResultsScoreboard(resolve(ROOT, options.resultsPath), rows, meta);
	}
	return rows;
};

// ─── CLI ────────────────────────────────────────────────────────────────────

const arg = (name: string, fallback: string): string => {
	const index = process.argv.indexOf(name);
	return index >= 0 && process.argv[index + 1] ? process.argv[index + 1] : fallback;
};

const isMain = (): boolean => {
	if (!process.argv[1]) return false;
	const self = new URL(import.meta.url).pathname;
	return resolve(process.argv[1]) === self || self.endsWith(process.argv[1]);
};

if (isMain()) {
	const options: ScoreboardJobOptions = {
		manifest: arg("--manifest", "corpus/word_based/centralized_mapping_randomized.csv"),
		sourceDir: resolve(
			ROOT,
			arg("--source-dir", "corpus/word_based/docx_source_randomized"),
		),
		engines: arg("--engines", "jubarte-native,jubarte-first-lossless").split(","),
		limit: process.argv.includes("--limit")
			? Number(arg("--limit", "0")) || undefined
			: undefined,
		outDir: resolve(ROOT, arg("--out", "runs/d2-scoreboard")),
		jubarteCli: arg("--jubarte-cli", "../jubarte-redlines/target/release/jubarte"),
		jubarteFirstDir: arg("--jubarte-first-dir", "../jubarte-first"),
		folioDir: arg("--folio-dir", "../reconciliation_plan/folio"),
		wordValidate: process.argv.includes("--word-validate"),
		wordSampleCount: Number(arg("--word-sample-count", "5")),
		updateResults: process.argv.includes("--update-results"),
		resultsPath: arg("--results", "RESULTS.md"),
	};
	runScoreboard(options)
		.then((rows) => {
			const disagreements = rows.filter((r) => r.disagreement).length;
			const failures = rows.filter((r) => !lensPassed(r.engineLens)).length;
			console.log(
				`\n${rows.length} rows; ${failures} engine-lens failures; ${disagreements} lens disagreements`,
			);
			process.exit(disagreements > 0 ? 2 : 0);
		})
		.catch((error) => {
			console.error(error);
			process.exit(1);
		});
}

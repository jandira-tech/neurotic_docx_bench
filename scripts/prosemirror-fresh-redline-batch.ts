// SPDX-License-Identifier: GPL-3.0-only
// Copyright (c) 2026 Jandira Technologies, LLC
//
// Batch redline generation for the cross-editor DOCX bench.
//
// Drives both editors over the fixture-pair manifest
// (`word_redlined_fixtures/word_redline_report.csv`) and writes one redlined
// DOCX per pair into a per-editor output directory. Each editor uses its OWN
// engine to produce the tracked changes — see prosemirror-headless-editor-
// server.ts for the single-pair contract.
//
// Usage:
//   node --import tsx prosemirror-fresh-redline-batch.ts --editor <id> [options]
//
// Options:
//   --csv <path>            CSV manifest.
//                            Default: word_redlined_fixtures/word_redline_report.csv
//   --source-dir <path>     Directory holding the source DOCX fixtures.
//                            Default: original_fixtures
//   --out-dir <path>        Output directory.
//                            Default: <editor>_redlined_fixtures
//   --status <list>         CSV statuses to run (comma-separated). Default: ok
//   --start-at <index>      First pair_index to run.
//   --limit <count>         Maximum number of selected pairs to run.
//   --force                 Regenerate outputs that already exist.
//   --dry-run               Print selected pairs without writing.
//   --fail-fast             Stop after the first failed pair.
//   --help, -h              Show this help.

import {
	existsSync,
	mkdirSync,
	readFileSync,
	statSync,
	unlinkSync,
	writeFileSync,
} from "node:fs";
import { basename, join, resolve } from "node:path";
import { parse } from "csv-parse/sync";

import {
	runSuperDocVitest,
	type EditorId,
} from "./prosemirror-headless-editor-server.js";

const REPO_ROOT = resolve(import.meta.dirname);
const CASUALOFFICE_ROOT = resolve(REPO_ROOT, "docs", "docx-editor");
const DEFAULT_CSV = resolve(
	REPO_ROOT,
	"word_redlined_fixtures",
	"word_redline_report.csv",
);
const DEFAULT_SOURCE_DIR = resolve(REPO_ROOT, "original_fixtures");
const DEFAULT_STATUSES = ["ok"] as const;

type RawCsvRow = {
	pair_index?: string;
	status?: string;
	base_filename?: string;
	next_filename?: string;
};

type CsvRow = {
	pairIndex: number;
	status: string;
	base: string;
	next: string;
};

type PlanItem = CsvRow & {
	fileA: string;
	fileB: string;
	outputPath: string;
};

type BatchOptions = {
	editor: EditorId;
	csvPath: string;
	sourceDir: string;
	outDir: string;
	statuses: string[];
	startAt?: number;
	limit?: number;
	force: boolean;
	dryRun: boolean;
	failFast: boolean;
	author: string;
};

type ItemResult = {
	pairIndex: number;
	base: string;
	next: string;
	ok: boolean;
	cached: boolean;
	bytes?: number;
	error?: string;
};

function usage(): string {
	return `
Usage:
  node --import tsx prosemirror-fresh-redline-batch.ts --editor <id> [options]

Options:
  --editor <casualoffice|superdoc>   Editor whose engine generates the redlines. Required.
  --csv <path>                       CSV manifest. Default: ${DEFAULT_CSV}
  --source-dir <path>                Source DOCX directory. Default: ${DEFAULT_SOURCE_DIR}
  --out-dir <path>                   Output directory. Default: <editor>_redlined_fixtures
  --status <list>                    CSV statuses to run. Default: ${DEFAULT_STATUSES.join(",")}
  --start-at <index>                 First pair_index to run.
  --limit <count>                    Maximum number of selected pairs to run.
  --force                            Regenerate outputs that already exist.
  --dry-run                          Print selected pairs without writing.
  --fail-fast                        Stop after the first failed pair.
  --author <name>                    Tracked-change author. Default: <editor>-batch
  --help, -h                         Show this help.
`.trim();
}

function parsePositiveInteger(value: string, flag: string): number {
	const parsed = Number(value);
	if (!Number.isInteger(parsed) || parsed <= 0) {
		throw new Error(`${flag} must be a positive integer`);
	}
	return parsed;
}

function parseEditor(value: string): EditorId {
	if (value === "casualoffice" || value === "superdoc") return value;
	throw new Error(`Unknown editor ${JSON.stringify(value)}`);
}

function parseArgs(argv: string[]): BatchOptions | "help" {
	const opts: BatchOptions = {
		editor: "casualoffice",
		csvPath: DEFAULT_CSV,
		sourceDir: DEFAULT_SOURCE_DIR,
		outDir: "",
		statuses: [...DEFAULT_STATUSES],
		force: false,
		dryRun: false,
		failFast: false,
		author: "",
	};
	let editorSet = false;
	for (let i = 0; i < argv.length; i += 1) {
		const arg = argv[i]!;
		const value = (): string => {
			const v = argv[i + 1];
			if (v == null || v.startsWith("--"))
				throw new Error(`Missing value for ${arg}`);
			i += 1;
			return v;
		};
		switch (arg) {
			case "--help":
			case "-h":
				return "help";
			case "--editor":
				opts.editor = parseEditor(value());
				editorSet = true;
				break;
			case "--csv":
				opts.csvPath = resolve(value());
				break;
			case "--source-dir":
				opts.sourceDir = resolve(value());
				break;
			case "--out-dir":
				opts.outDir = resolve(value());
				break;
			case "--status":
				opts.statuses = value()
					.split(",")
					.map((s) => s.trim())
					.filter(Boolean);
				if (opts.statuses.length === 0)
					throw new Error("--status requires at least one status");
				break;
			case "--start-at":
				opts.startAt = parsePositiveInteger(value(), "--start-at");
				break;
			case "--limit":
				opts.limit = parsePositiveInteger(value(), "--limit");
				break;
			case "--force":
				opts.force = true;
				break;
			case "--dry-run":
				opts.dryRun = true;
				break;
			case "--fail-fast":
				opts.failFast = true;
				break;
			case "--author":
				opts.author = value();
				break;
			default:
				throw new Error(`Unknown argument ${arg}`);
		}
	}
	if (!editorSet)
		throw new Error("--editor <casualoffice|superdoc> is required");
	if (!opts.outDir) {
		opts.outDir = resolve(REPO_ROOT, `${opts.editor}_redlined_fixtures`);
	}
	if (!opts.author) opts.author = `${opts.editor}-batch`;
	return opts;
}

export function parseCsv(csvText: string): CsvRow[] {
	const rows = parse(csvText, {
		columns: true,
		skip_empty_lines: true,
		trim: true,
	}) as RawCsvRow[];
	return rows.map((row, index) => {
		const pairIndex = Number(row.pair_index);
		if (!Number.isInteger(pairIndex) || pairIndex <= 0) {
			throw new Error(`CSV row ${index + 1} has invalid pair_index`);
		}
		if (!row.base_filename)
			throw new Error(`CSV row ${index + 1} is missing base_filename`);
		if (!row.next_filename)
			throw new Error(`CSV row ${index + 1} is missing next_filename`);
		if (!row.status) throw new Error(`CSV row ${index + 1} is missing status`);
		return {
			pairIndex,
			status: row.status,
			base: row.base_filename,
			next: row.next_filename,
		};
	});
}

function sourcePath(sourceDir: string, filename: string): string {
	return join(sourceDir, basename(filename));
}

/**
 * Build the output filename for a pair from sanitized basenames only, and
 * verify the resolved path stays inside outDir. CSV row.base / row.next are
 * attacker-controlled strings; using them raw allowed path traversal
 * (e.g. base_filename="../../etc/evil" escaping outDir on write).
 */
function safeOutputPath(
	outDir: string,
	base: string,
	next: string,
	editor: string,
): string {
	const baseStem = basename(base).replace(/\.docx$/i, "");
	const nextStem = basename(next).replace(/\.docx$/i, "");
	const candidate = join(
		outDir,
		`${baseStem}_${nextStem}_${editor}_redline.docx`,
	);
	const resolvedOutDir = resolve(outDir);
	const resolvedCandidate = resolve(candidate);
	if (
		resolvedCandidate !== resolve(resolvedOutDir, basename(resolvedCandidate))
	) {
		throw new Error(`output path escapes outDir: ${candidate}`);
	}
	return resolvedCandidate;
}

export function planBatch(options: BatchOptions): PlanItem[] {
	const selectedStatuses = new Set(options.statuses);
	const selected = parseCsv(readFileSync(options.csvPath, "utf8"))
		.filter((row) => selectedStatuses.has(row.status))
		.filter(
			(row) => options.startAt == null || row.pairIndex >= options.startAt,
		)
		.sort((a, b) => a.pairIndex - b.pairIndex);
	const limited =
		options.limit == null ? selected : selected.slice(0, options.limit);
	return limited.map((row) => ({
		...row,
		fileA: sourcePath(options.sourceDir, row.base),
		fileB: sourcePath(options.sourceDir, row.next),
		outputPath: safeOutputPath(
			options.outDir,
			row.base,
			row.next,
			options.editor,
		),
	}));
}

function existingNonEmpty(path: string): boolean {
	return existsSync(path) && statSync(path).size > 0;
}

// ---------------------------------------------------------------------------
// CasualOffice batch: in-process loop (its own parser/serializer engine)
// ---------------------------------------------------------------------------

async function runCasualOfficeBatch(
	options: BatchOptions,
	plan: PlanItem[],
): Promise<ItemResult[]> {
	const { compareDocxBytes } = await import(
		CASUALOFFICE_ROOT + "/packages/core/src/redline-engine.ts"
	);
	const results: ItemResult[] = [];
	for (const [index, item] of plan.entries()) {
		const tag = `[${index + 1}/${plan.length}] #${item.pairIndex}`;
		if (options.dryRun) {
			console.log(`${tag} DRY ${item.base} <> ${item.next}`);
			results.push({
				pairIndex: item.pairIndex,
				base: item.base,
				next: item.next,
				ok: true,
				cached: false,
			});
			continue;
		}
		try {
			if (!options.force && existingNonEmpty(item.outputPath)) {
				const bytes = statSync(item.outputPath).size;
				console.log(`${tag} CACHE ${bytes}B ${basename(item.outputPath)}`);
				results.push({
					pairIndex: item.pairIndex,
					base: item.base,
					next: item.next,
					ok: true,
					cached: true,
					bytes,
				});
				continue;
			}
			const base = readFileSync(item.fileA);
			const next = readFileSync(item.fileB);
			const out = await compareDocxBytes(
				new Uint8Array(base),
				new Uint8Array(next),
				{
					author: options.author,
				},
			);
			mkdirSync(options.outDir, { recursive: true });
			writeFileSync(item.outputPath, out.bytes);
			console.log(
				`${tag} OK ${out.bytes.length}B ${basename(item.outputPath)}`,
			);
			results.push({
				pairIndex: item.pairIndex,
				base: item.base,
				next: item.next,
				ok: true,
				cached: false,
				bytes: out.bytes.length,
			});
		} catch (error) {
			const message = error instanceof Error ? error.message : String(error);
			console.error(`${tag} FAIL ${message.split("\n")[0]}`);
			results.push({
				pairIndex: item.pairIndex,
				base: item.base,
				next: item.next,
				ok: false,
				cached: false,
				error: message,
			});
			if (options.failFast) break;
		}
	}
	return results;
}

// ---------------------------------------------------------------------------
// SuperDoc batch: one vitest invocation over a JSON plan (its own engine)
// ---------------------------------------------------------------------------

async function runSuperDocBatch(
	options: BatchOptions,
	plan: PlanItem[],
): Promise<ItemResult[]> {
	const results: ItemResult[] = [];
	if (options.dryRun) {
		for (const [index, item] of plan.entries()) {
			console.log(
				`[${index + 1}/${plan.length}] #${item.pairIndex} DRY ${item.base} <> ${item.next}`,
			);
			results.push({
				pairIndex: item.pairIndex,
				base: item.base,
				next: item.next,
				ok: true,
				cached: false,
			});
		}
		return results;
	}
	// Cache-skip: split into pending + already-cached.
	const pending: PlanItem[] = [];
	for (const item of plan) {
		if (!options.force && existingNonEmpty(item.outputPath)) {
			const bytes = statSync(item.outputPath).size;
			console.log(
				`#${item.pairIndex} CACHE ${bytes}B ${basename(item.outputPath)}`,
			);
			results.push({
				pairIndex: item.pairIndex,
				base: item.base,
				next: item.next,
				ok: true,
				cached: true,
				bytes,
			});
		} else {
			pending.push(item);
		}
	}
	if (pending.length === 0) return results;

	mkdirSync(options.outDir, { recursive: true });
	const planPath = join(
		options.outDir,
		".tmp",
		`superdoc-plan-${Date.now()}.json`,
	);
	mkdirSync(join(options.outDir, ".tmp"), { recursive: true });
	writeFileSync(
		planPath,
		JSON.stringify(
			pending.map((item) => ({
				fileA: item.fileA,
				fileB: item.fileB,
				output: item.outputPath,
			})),
		),
	);
	try {
		await runSuperDocVitest({
			REDLINE_PLAN: planPath,
			REDLINE_AUTHOR: options.author,
		});
		for (const item of pending) {
			if (existingNonEmpty(item.outputPath)) {
				const bytes = statSync(item.outputPath).size;
				console.log(
					`#${item.pairIndex} OK ${bytes}B ${basename(item.outputPath)}`,
				);
				results.push({
					pairIndex: item.pairIndex,
					base: item.base,
					next: item.next,
					ok: true,
					cached: false,
					bytes,
				});
			} else {
				console.error(`#${item.pairIndex} FAIL no output written`);
				results.push({
					pairIndex: item.pairIndex,
					base: item.base,
					next: item.next,
					ok: false,
					cached: false,
					error: "no output written",
				});
				if (options.failFast) break;
			}
		}
	} finally {
		try {
			if (existsSync(planPath)) unlinkSync(planPath);
		} catch {
			// plan file cleanup is best-effort
		}
	}
	return results;
}

export async function runBatch(options: BatchOptions): Promise<void> {
	const plan = planBatch(options);
	if (!options.dryRun) mkdirSync(options.outDir, { recursive: true });
	console.log(
		`${options.editor} batch: ${plan.length} pairs -> ${options.outDir}`,
	);
	console.log(`manifest: ${options.csvPath}`);

	const results =
		options.editor === "casualoffice"
			? await runCasualOfficeBatch(options, plan)
			: await runSuperDocBatch(options, plan);

	const ok = results.filter((r) => r.ok).length;
	const cached = results.filter((r) => r.cached).length;
	const failed = results.filter((r) => !r.ok).length;
	console.log(
		`${options.editor} summary: ok=${ok} cached=${cached} failed=${failed}`,
	);
	if (failed > 0) process.exitCode = 1;
}

export async function runCli(argv = process.argv.slice(2)): Promise<void> {
	const parsed = parseArgs(argv);
	if (parsed === "help") {
		console.log(usage());
		return;
	}
	await runBatch(parsed);
}

if (import.meta.url === new URL(`file://${process.argv[1]}`).href) {
	runCli().catch((error: unknown) => {
		console.error(error instanceof Error ? error.message : error);
		process.exitCode = 1;
	});
}

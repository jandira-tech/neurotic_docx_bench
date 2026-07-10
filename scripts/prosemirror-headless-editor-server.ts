// SPDX-License-Identifier: GPL-3.0-only
// Copyright (c) 2026 Jandira Technologies, LLC
//
// Single-pair DOCX compare driver for the cross-editor bench.
//
// Each editor generates the redline with its OWN engine:
//   - CasualOffice (docx-editor): its parser + Document-model diff +
//     serializer round-trip (`@eigenpal/docx-core/redline`), run in-process
//     under tsx.
//   - SuperDoc: its native `Editor.commands.compareDocuments` +
//     `replayDifferences({ applyTrackedChanges: true })` + `exportDocx`,
//     run through SuperDoc's own Vite toolchain (vitest) because the editor
//     source depends on Vite path aliases and a DOM (happy-dom).
//
// Usage:
//   node --import tsx prosemirror-headless-editor-server.ts \
//     --editor casualoffice fileA.docx fileB.docx [--out redline.docx] \
//     [--author NAME] [--no-server]
//   node --import tsx prosemirror-headless-editor-server.ts \
//     --editor superdoc fileA.docx fileB.docx [--out redline.docx] \
//     [--author NAME]
//
// Two positional DOCX files are compared by default. Use --convert to convert
// a single DOCX instead (CasualOffice only).

import { spawn } from "node:child_process";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { basename, dirname, extname, join, resolve } from "node:path";

export type EditorId = "casualoffice" | "superdoc";

export type CompareOptions = {
	editor: EditorId;
	fileA: string;
	fileB: string;
	output: string;
	author: string;
};

const REPO_ROOT = resolve(import.meta.dirname, "..");
const CASUALOFFICE_ROOT = resolve(REPO_ROOT, "docs", "docx-editor");
const SUPERDOC_ROOT = resolve(REPO_ROOT, "superdoc");
const SUPERDOC_TEST = "src/editors/v1/tests/redline-bench/redline.test.js";

function usage(): string {
	return `
Usage:
  node --import tsx prosemirror-headless-editor-server.ts --editor <id> fileA.docx fileB.docx

Options:
  --editor <casualoffice|superdoc>   Editor whose engine generates the redline. Required.
  --out <path>                       Output DOCX path. Default: <fileA>_<fileB>_redline.docx
  --author <name>                    Tracked-change author name. Default: "<editor>-headless".
  --help, -h                         Show this help.
`.trim();
}

function stripDocxExtension(file: string): string {
	return basename(file, extname(file)).replace(/[^A-Za-z0-9._-]+/g, "_");
}

function defaultOutputPath(fileA: string, fileB: string): string {
	return join(
		dirname(resolve(fileA)),
		`${stripDocxExtension(fileA)}_${stripDocxExtension(fileB)}_redline.docx`,
	);
}

export function parseArgs(argv: string[]): CompareOptions | "help" {
	let editor: EditorId | undefined;
	let out: string | undefined;
	let author: string | undefined;
	const positional: string[] = [];
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
				editor = parseEditor(value());
				break;
			case "--out":
			case "--out-dir":
				out = value();
				break;
			case "--author":
				author = value();
				break;
			case "--no-server":
			case "--start-server":
			case "--keep-server":
				// Accepted for backward compatibility; no longer meaningful.
				break;
			default:
				if (arg.startsWith("--")) throw new Error(`Unknown argument ${arg}`);
				positional.push(arg);
		}
	}
	if (editor == null)
		throw new Error("--editor <casualoffice|superdoc> is required");
	if (positional.length !== 2) {
		throw new Error("Exactly two DOCX positional files are required");
	}
	return {
		editor,
		fileA: resolve(positional[0]!),
		fileB: resolve(positional[1]!),
		output: resolve(out ?? defaultOutputPath(positional[0]!, positional[1]!)),
		author: author ?? `${editor}-headless`,
	};
}

function parseEditor(value: string): EditorId {
	if (value === "casualoffice" || value === "superdoc") return value;
	throw new Error(`Unknown editor ${JSON.stringify(value)}`);
}

// ---------------------------------------------------------------------------
// CasualOffice: in-process via tsx (its own parser/serializer engine)
// ---------------------------------------------------------------------------

async function compareWithCasualOffice(opts: CompareOptions): Promise<void> {
	const { compareDocxBytes } = await import(
		CASUALOFFICE_ROOT + "/packages/core/src/redline-engine.ts"
	);
	const base = await readFile(opts.fileA);
	const next = await readFile(opts.fileB);
	const result = await compareDocxBytes(
		new Uint8Array(base),
		new Uint8Array(next),
		{ author: opts.author },
	);
	await mkdir(dirname(opts.output), { recursive: true });
	await writeFile(opts.output, result.bytes);
	console.log(`Wrote ${opts.output} (${result.bytes.length}B)`);
}

// ---------------------------------------------------------------------------
// SuperDoc: shell out to its vitest entrypoint (its own engine)
// ---------------------------------------------------------------------------

async function compareWithSuperDoc(opts: CompareOptions): Promise<void> {
	await mkdir(dirname(opts.output), { recursive: true });
	await runSuperDocVitest({
		REDLINE_BASE: opts.fileA,
		REDLINE_NEXT: opts.fileB,
		REDLINE_OUT: opts.output,
		REDLINE_AUTHOR: opts.author,
	});
	console.log(`Wrote ${opts.output}`);
}

/**
 * Run SuperDoc's redline entrypoint through its vitest project. Accepts either
 * single-pair env vars (REDLINE_BASE/NEXT/OUT) or a batch plan (REDLINE_PLAN).
 */
export function runSuperDocVitest(
	env: Record<string, string>,
	options: { cwd?: string; testPath?: string } = {},
): Promise<void> {
	const cwd = options.cwd ?? SUPERDOC_ROOT;
	const testPath = options.testPath ?? SUPERDOC_TEST;
	return new Promise((resolveRun, rejectRun) => {
		const child = spawn(
			"npx",
			["vitest", "run", "--root", "packages/super-editor", testPath],
			{
				cwd,
				env: { ...process.env, ...env },
				stdio: "inherit",
			},
		);
		child.on("exit", (code) => {
			if (code === 0) resolveRun();
			else rejectRun(new Error(`SuperDoc vitest exited with code ${code}`));
		});
		child.on("error", rejectRun);
	});
}

export async function runCli(argv = process.argv.slice(2)): Promise<void> {
	const parsed = parseArgs(argv);
	if (parsed === "help") {
		console.log(usage());
		return;
	}
	if (parsed.editor === "casualoffice") {
		await compareWithCasualOffice(parsed);
		return;
	}
	await compareWithSuperDoc(parsed);
}

// Main-module detection: pathToFileURL is the portable way to compare against
// import.meta.url. The previous `new URL(\`file://${process.argv[1]}\`)` form
// produced a malformed file:// URL on Windows drive paths (e.g. file://C:\...).
import { pathToFileURL } from "node:url";
if (import.meta.url === pathToFileURL(process.argv[1]!).href) {
	runCli().catch((error: unknown) => {
		console.error(error instanceof Error ? error.message : error);
		process.exitCode = 1;
	});
}

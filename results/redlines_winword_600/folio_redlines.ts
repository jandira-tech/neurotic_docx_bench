/**
 * folio's redlines of the fixed set redline_600, made with `compareDocx` the way folio's own
 * compare benchmark calls it (benchmarks/compare/run.ts: same OPTIONS, strict by default,
 * `onUnverified: "emit"` as the best-effort second mode).
 *
 *     node --import tsx results/redline600_contabo/folio_redlines.ts \
 *         --folio-dir .scratch/redline600-contabo/folio [--jobs 6] [--timeout 300] [--limit N]
 *
 * `--folio-dir` is a pnpm install of `@stll/folio-core` (its package.json pins the version,
 * which is checked against `--version`). Every pair of `results/sets/redline_600.csv` is
 * compared in a child process of its own, under `--timeout` seconds per mode, so a pathological
 * pair cannot stall the run and no pair inherits another's warmed JIT or heap. Inputs are read
 * from the set's paths and their sha256 checked against the set.
 *
 * Each pair runs in both modes:
 *   strict (the default, refuses a redline it cannot prove)
 *       -> folio-<v>/docx/<key>_folio-<v>.docx when it produced one
 *   emit   (`onUnverified: "emit"`, the best attempt plus what did not hold)
 *       -> folio-<v>-emit/docx/<key>_folio-<v>-emit.docx, for every pair it produced
 * Both outputs' sha256 are recorded, so "emit returns the strict package when strict produced
 * one" is a measured fact per pair, not an assumption.
 *
 * One JSON line per pair goes to `folio_redlines.jsonl`: key, per mode the status
 * (produced|refused|error|timeout), the error tag and message, change count, verification
 * status, compatibility, unsupported reasons, seconds, output sha256. A pair whose outputs are
 * already on disk is skipped.
 */

import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import { appendFileSync, existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const HERE = path.dirname(new URL(import.meta.url).pathname);
const ROOT = path.resolve(HERE, "../..");
const SET_CSV = path.join(ROOT, "results/sets/redline_600.csv");
const LOG = path.join(HERE, "folio_redlines.jsonl");
const OPTIONS = { author: "folio compare benchmark", timestamp: "2000-01-01T00:00:00.000Z" };

const arg = (name: string, fallback: string | null = null): string | null => {
	const i = process.argv.indexOf(`--${name}`);
	return i === -1 ? fallback : (process.argv[i + 1] ?? fallback);
};
const sha256 = (b: Uint8Array): string => createHash("sha256").update(b).digest("hex");
const exactArrayBuffer = (b: Buffer): ArrayBuffer =>
	// A pooled Buffer's .buffer is the whole pool: slice out exactly this file's bytes.
	b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength) as ArrayBuffer;

type Row = { key: string; base: string; next: string; base_sha256: string; next_sha256: string };

const readSet = (): Row[] => {
	const [head, ...lines] = readFileSync(SET_CSV, "utf8").trim().split(/\r?\n/);
	const cols = head.split(",");
	return lines.map((line) => {
		const cells = line.split(",");
		if (cells.length !== cols.length) throw new Error(`${SET_CSV}: a quoted or short row: ${line.slice(0, 80)}`);
		return Object.fromEntries(cols.map((c, i) => [c, cells[i]])) as unknown as Row;
	});
};

const lanes = (version: string) => {
	const strict = `folio-${version}`;
	const emit = `folio-${version}-emit`;
	return {
		strict,
		emit,
		out: (lane: string, key: string) => path.join(HERE, lane, "docx", `${key}_${lane}.docx`),
	};
};

// ---------------------------------------------------------------- child: one pair, one mode
const runChild = async (): Promise<void> => {
	const folioDir = path.resolve(ROOT, arg("folio-dir") ?? "");
	const mode = arg("mode") as "strict" | "emit";
	const base = readFileSync(arg("base") ?? "");
	const next = readFileSync(arg("next") ?? "");
	const out = arg("out") ?? "";
	const entry = path.join(folioDir, "node_modules/@stll/folio-core/dist/compare/compare.js");
	const { compareDocx } = await import(pathToFileURL(entry).href);
	const t0 = performance.now();
	const result = await compareDocx(
		exactArrayBuffer(base),
		exactArrayBuffer(next),
		mode === "emit" ? { ...OPTIONS, onUnverified: "emit" } : OPTIONS,
	);
	const seconds = (performance.now() - t0) / 1000;
	if (result.isErr()) {
		const e = result.error as { _tag?: string; name?: string; message?: string };
		process.stdout.write(
			`${JSON.stringify({ status: "refused", seconds, error_tag: e._tag ?? e.name ?? "Error", error: String(e.message ?? e).slice(0, 600) })}\n`,
		);
		return;
	}
	const { buffer, changes, verification, compatibility, unsupported } = result.value;
	const bytes = new Uint8Array(buffer);
	mkdirSync(path.dirname(out), { recursive: true });
	writeFileSync(`${out}.part`, bytes);
	renameSync(`${out}.part`, out);
	process.stdout.write(
		`${JSON.stringify({
			status: "produced",
			seconds,
			changes: changes.length,
			verification: verification?.status ?? null,
			compatibility: compatibility?.status ?? null,
			unsupported: [...new Set((unsupported ?? []).map((u: { reason: string }) => u.reason))].sort(),
			sha256: sha256(bytes),
			bytes: bytes.byteLength,
		})}\n`,
	);
};

// ---------------------------------------------------------------- parent
const runMode = (row: Row, mode: "strict" | "emit", out: string, timeoutS: number) =>
	new Promise<Record<string, unknown>>((resolve) => {
		const t0 = performance.now();
		const child = spawn(
			process.execPath,
			[
				...process.execArgv,
				new URL(import.meta.url).pathname,
				"--child",
				"--folio-dir", arg("folio-dir") ?? "",
				"--mode", mode,
				"--base", path.join(ROOT, row.base),
				"--next", path.join(ROOT, row.next),
				"--out", out,
			],
			{ cwd: ROOT, stdio: ["ignore", "pipe", "pipe"] },
		);
		let stdout = "";
		let stderr = "";
		child.stdout.on("data", (d) => (stdout += d));
		child.stderr.on("data", (d) => (stderr += d));
		const timer = setTimeout(() => child.kill("SIGKILL"), timeoutS * 1000);
		child.on("close", (code, signal) => {
			clearTimeout(timer);
			const wall = (performance.now() - t0) / 1000;
			const line = stdout.trim().split("\n").at(-1) ?? "";
			if (signal === "SIGKILL") return resolve({ status: "timeout", wall, error: `killed after ${timeoutS} s` });
			try {
				return resolve({ ...JSON.parse(line), wall });
			} catch {
				// compareDocx threw instead of returning an Err (e.g. a CanonicalSessionError
				// refusal): keep the message and the tag, not the stack frames.
				const text = (stderr || stdout || `exit ${code}`).split("\n").filter((l) => !/^\s+at /.test(l));
				const message = text.find((l) => /^\w*(Error|Exception)\b.*:/.test(l)) ?? text.join(" ").trim();
				const tag = /_tag: '([^']+)'/.exec(stderr)?.[1] ?? /^(\w+):/.exec(message)?.[1] ?? null;
				return resolve({ status: "error", wall, rc: code, error_tag: tag, error: message.trim().slice(0, 600) });
			}
		});
	});

const runParent = async (): Promise<void> => {
	const folioDir = path.resolve(ROOT, arg("folio-dir") ?? "");
	const want = arg("version", "0.70.0") ?? "";
	const pkg = path.join(folioDir, "node_modules/@stll/folio-core/package.json");
	const found = existsSync(pkg) ? JSON.parse(readFileSync(pkg, "utf8")).version : null;
	if (found !== want) throw new Error(`${pkg}: @stll/folio-core ${found}, expected ${want}`);
	const L = lanes(want);
	const jobs = Number(arg("jobs", "6"));
	const timeoutS = Number(arg("timeout", "300"));
	let rows = readSet();
	if (rows.length !== 600) throw new Error(`${SET_CSV} has ${rows.length} rows, not 600`);
	const limit = Number(arg("limit", "0"));
	if (limit) rows = rows.slice(0, limit);
	const logged = new Set(
		existsSync(LOG) ? readFileSync(LOG, "utf8").trim().split("\n").filter(Boolean).map((l) => JSON.parse(l).key) : [],
	);
	const todo = rows.filter((r) => !logged.has(r.key));
	console.log(`folio-core ${found}: ${rows.length} pairs, ${rows.length - todo.length} already logged, ${todo.length} to run, ${jobs} at a time`);
	const started = performance.now();
	let done = 0;
	const tally = { strict: 0, emit: 0, same: 0 };
	const worker = async () => {
		for (let r = todo.shift(); r; r = todo.shift()) {
			const rec: Record<string, unknown> = { key: r.key, tool: `@stll/folio-core ${found}`, options: OPTIONS };
			const bad = [
				[r.base, r.base_sha256],
				[r.next, r.next_sha256],
			].find(([p, want]) => sha256(readFileSync(path.join(ROOT, p))) !== want);
			if (bad) {
				rec.error = `${bad[0]} does not match the set's sha256; not compared`;
			} else {
				rec.strict = await runMode(r, "strict", L.out(L.strict, r.key), timeoutS);
				rec.emit = await runMode(r, "emit", L.out(L.emit, r.key), timeoutS);
				const s = rec.strict as { status: string; sha256?: string };
				const e = rec.emit as { status: string; sha256?: string };
				rec.emit_equals_strict = s.status === "produced" && e.status === "produced" ? s.sha256 === e.sha256 : null;
				tally.strict += Number(s.status === "produced");
				tally.emit += Number(e.status === "produced");
				tally.same += Number(rec.emit_equals_strict === true);
			}
			appendFileSync(LOG, `${JSON.stringify(rec)}\n`);
			done++;
			const s = rec.strict as { status?: string; error_tag?: string } | undefined;
			const e = rec.emit as { status?: string } | undefined;
			console.log(
				`[${((performance.now() - started) / 60000).toFixed(1).padStart(5)} min] ${String(done).padStart(3)} ` +
					`strict=${s?.status ?? "-"}${s?.error_tag ? `(${s.error_tag})` : ""} emit=${e?.status ?? "-"} ${r.key.slice(0, 60)}` +
					` | produced strict ${tally.strict}, emit ${tally.emit}, identical ${tally.same}`,
			);
		}
	};
	await Promise.all(Array.from({ length: jobs }, worker));
	console.log(`done: strict produced ${tally.strict}, emit produced ${tally.emit}, emit == strict ${tally.same} (this pass)`);
};

if (process.argv.includes("--child")) await runChild();
else await runParent();

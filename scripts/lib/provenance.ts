/**
 * Provenance for speed rows: the same pin shape the Python side writes
 * (tool_updater.resolve_local_version) and a machine fingerprint.
 *
 * A speed number without a tool version and a machine is not comparable to
 * anything; both were absent from every row before this module existed.
 */
import { createHash } from "node:crypto";
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { arch, cpus, platform, release, totalmem } from "node:os";
import { join, relative } from "node:path";

export interface HardwareInfo {
	system: string;
	release: string;
	machine: string;
	cpu: string;
	cores: number;
	ram_gb: number;
	node: string;
}

function walk(dir: string, out: string[]): void {
	for (const ent of readdirSync(dir, { withFileTypes: true })) {
		const p = join(dir, ent.name);
		if (ent.isDirectory()) walk(p, out);
		else if (ent.isFile()) out.push(p);
	}
}

/** `<label>@<sha256[:12]>[+git.<sha>]` over (relpath, bytes) of every file in the dist. */
export function toolVersionForDist(dist: string): string | null {
	if (!dist || !existsSync(dist) || !statSync(dist).isDirectory()) return null;
	let label = dist.split("/").filter(Boolean).at(-1) ?? "dist";
	const pkg = join(dist, "package.json");
	if (existsSync(pkg)) {
		try {
			const v = (JSON.parse(readFileSync(pkg, "utf8")) as { version?: string }).version;
			if (v) label = String(v);
		} catch {
			/* keep the directory name */
		}
	}
	const files: string[] = [];
	walk(dist, files);
	const rel = (f: string) => relative(dist, f).split("\\").join("/");
	files.sort((a, b) => (rel(a) < rel(b) ? -1 : rel(a) > rel(b) ? 1 : 0));
	const h = createHash("sha256");
	for (const f of files) {
		const r = rel(f);
		const base = r.split("/").at(-1) ?? r;
		if (base.startsWith("ENGINE_") && base.endsWith(".txt")) continue;
		h.update(r);
		h.update(readFileSync(f));
	}
	let pin = `${label}@${h.digest("hex").slice(0, 12)}`;
	const commitFile = join(dist, "ENGINE_COMMIT.txt");
	if (existsSync(commitFile)) {
		const commit = readFileSync(commitFile, "utf8").trim();
		if (commit) pin += `+git.${commit}`;
	}
	return pin;
}

/** Installed version of an npm package under the repo's node_modules, or null. */
export function npmVersion(pkg: string, root: string): string | null {
	try {
		const raw = readFileSync(join(root, "node_modules", pkg, "package.json"), "utf8");
		return (JSON.parse(raw) as { version?: string }).version ?? null;
	} catch {
		return null;
	}
}

/** Pin for a speed method: npm-installed engines by package version, local dists by content hash. */
export function toolVersionForMethod(engineId: string, dist: string, root: string): string | null {
	if (engineId === "docxodus") return npmVersion("docxodus", root);
	if (engineId.startsWith("superdoc")) return npmVersion("@superdoc-dev/sdk", root);
	return toolVersionForDist(dist);
}

export function hardwareInfo(): HardwareInfo {
	const list = cpus();
	return {
		system: platform(),
		release: release(),
		machine: arch(),
		cpu: list[0]?.model ?? arch(),
		cores: list.length || 1,
		ram_gb: Math.round((totalmem() / 2 ** 30) * 10) / 10,
		node: process.version,
	};
}

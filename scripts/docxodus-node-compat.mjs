/**
 * Node ESM cannot load published docxodus ≥9.3: the package root re-exports
 * DocxEditor, which imports Atlaskit via package.json-directory specifiers
 * (`@atlaskit/pragmatic-drag-and-drop/element/adapter`). Node rejects
 * directory imports; those files are also extensionless. Bun accepts both.
 * This hook follows each Atlaskit subpath's `module` field and appends `.js`
 * to its relative imports so `node --import tsx` can still measure the
 * published package. It does not change compareDocuments.
 */
import { createRequire, registerHooks } from "node:module";
import { existsSync, readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";


function pinnedDocxodusVersion(fromDir) {
	const pkgPath = resolve(fromDir, "../package.json");
	if (!existsSync(pkgPath)) return null;
	const pkg = JSON.parse(readFileSync(pkgPath, "utf8"));
	return pkg.dependencies?.docxodus ?? pkg.devDependencies?.docxodus ?? null;
}

/** Remap Atlaskit directory imports. `entry` is the chosen `docxodus/dist/index.js`,
 *  used only to locate the pin when no importing module is in context. */
const INSTALLED = Symbol.for("neurotic.docxodusNodeCompat");
export function installDocxodusNodeCompat(entry) {
	// Global flag, not a module-local one: vitest's vi.resetModules() re-executes
	// this module with a fresh `installed = false`, and every re-registration
	// stacks another resolve hook on the worker — three stacked hooks deadlock
	// real docxodus's import graph. globalThis survives module resets.
	if (globalThis[INSTALLED]) return;
	globalThis[INSTALLED] = true;
	if (typeof globalThis.Bun !== "undefined") return;
	registerHooks({
		resolve(specifier, context, nextResolve) {
			if (specifier.startsWith("@atlaskit/pragmatic-drag-and-drop")) {
				try {
					// Resolve from the IMPORTING module: pnpm isolates each package's
					// dependencies in its own .pnpm neighborhood, so a require rooted
					// at the docxodus entry cannot see Atlaskit packages that live
					// beside their actual importer (@atlaskit/pragmatic-drag-and-drop
					// is a dependency of -auto-scroll, not of docxodus). Bun's shared
					// hoisted tree hid this; the pnpm tree exposes it.
					const from =
						context.parentURL ??
						(entry ? pathToFileURL(entry).href : import.meta.url);
					const parentReq = createRequire(from);
					const pkgPath = parentReq.resolve(`${specifier}/package.json`);
					const pkg = JSON.parse(readFileSync(pkgPath, "utf8"));
					const rel = pkg.module ?? pkg.main;
					if (rel) {
						return nextResolve(pathToFileURL(resolve(dirname(pkgPath), rel)).href, context);
					}
				} catch {
					// fall through to default resolution
				}
			}
			if (
				specifier.startsWith(".") &&
				!specifier.endsWith(".js") &&
				context.parentURL?.includes("@atlaskit/pragmatic-drag-and-drop")
			) {
				return nextResolve(`${specifier}.js`, context);
			}
			return nextResolve(specifier, context);
		},
	});
}

/** Pin-tree (repo-root node_modules) first, vendored utils/docxodus as fallback.
 *  Skips a tree whose package.json version is not the repo pin. */
export function resolveDocxodusEntry(fromDir = dirname(fileURLToPath(import.meta.url))) {
	// An explicit tree (a source build, an unreleased main) replaces the pin: the caller
	// named the package to measure, and its own version is what the run records.
	const override = process.env.DOCXODUS_NODE_MODULES;
	if (override) {
		const candidate = join(override, "docxodus/dist/index.js");
		if (!existsSync(candidate)) {
			throw new Error(`DOCXODUS_NODE_MODULES=${override} has no docxodus/dist/index.js`);
		}
		return candidate;
	}
	const pin = pinnedDocxodusVersion(fromDir);
	const roots = [
		resolve(fromDir, "../node_modules"),
		resolve(fromDir, "../src/neurotic_docx_bench/utils/docxodus/node_modules"),
	];
	const seen = [];
	for (const root of roots) {
		const candidate = join(root, "docxodus/dist/index.js");
		const pkgPath = join(root, "docxodus/package.json");
		if (!existsSync(candidate) || !existsSync(pkgPath)) continue;
		const version = JSON.parse(readFileSync(pkgPath, "utf8")).version;
		seen.push(`${root}→${version}`);
		if (pin && version !== pin) continue;
		return candidate;
	}
	throw new Error(
		`docxodus ${pin ?? "pin"} not installed (looked: ${seen.join("; ") || "no trees"})`,
	);
}

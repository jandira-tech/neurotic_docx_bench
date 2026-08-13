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

let installed = false;

function pinnedDocxodusVersion(fromDir) {
	const pkgPath = resolve(fromDir, "../package.json");
	if (!existsSync(pkgPath)) return null;
	const pkg = JSON.parse(readFileSync(pkgPath, "utf8"));
	return pkg.dependencies?.docxodus ?? pkg.devDependencies?.docxodus ?? null;
}

/** Remap Atlaskit directory imports. `entry` is the chosen `docxodus/dist/index.js`
 *  so createRequire walks THAT package's node_modules, not this script's. */
export function installDocxodusNodeCompat(entry) {
	if (installed) return;
	installed = true;
	if (typeof globalThis.Bun !== "undefined") return;
	const req = createRequire(entry ? pathToFileURL(entry).href : import.meta.url);
	registerHooks({
		resolve(specifier, context, nextResolve) {
			if (specifier.startsWith("@atlaskit/pragmatic-drag-and-drop")) {
				try {
					const pkgPath = req.resolve(`${specifier}/package.json`);
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

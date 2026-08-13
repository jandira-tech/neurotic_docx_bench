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

export function installDocxodusNodeCompat() {
	if (installed) return;
	installed = true;
	if (typeof globalThis.Bun !== "undefined") return;
	const req = createRequire(import.meta.url);
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

/** Pin-tree (repo-root node_modules) first, vendored utils/docxodus as fallback. */
export function resolveDocxodusEntry(fromDir = dirname(fileURLToPath(import.meta.url))) {
	const roots = [
		resolve(fromDir, "../node_modules"),
		resolve(fromDir, "../src/neurotic_docx_bench/utils/docxodus/node_modules"),
	];
	for (const root of roots) {
		const candidate = join(root, "docxodus/dist/index.js");
		if (existsSync(candidate)) return candidate;
	}
	return join(roots[roots.length - 1], "docxodus/dist/index.js");
}

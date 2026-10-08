// SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
// SPDX-License-Identifier: AGPL-3.0-only
import { cp, mkdir } from 'node:fs/promises';
const destination = new URL('../public/_astro/pdfjs/', import.meta.url);
await mkdir(destination, { recursive: true });
for (const name of ['cmaps', 'standard_fonts', 'wasm', 'LICENSE']) {
  await cp(new URL(`../node_modules/pdfjs-dist/${name}`, import.meta.url), new URL(name, destination), { recursive: true });
}

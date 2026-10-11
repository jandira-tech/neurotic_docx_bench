// SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
// SPDX-License-Identifier: AGPL-3.0-only
// CSS lives under <public-prefix>/_astro/. Relative fonts work at every alias.
import { readdir, readFile, writeFile } from 'node:fs/promises';
const folder = new URL('../dist/client/_astro/', import.meta.url);
for (const name of await readdir(folder)) {
  if (!name.endsWith('.css')) continue;
  const file = new URL(name, folder);
  const css = await readFile(file, 'utf8');
  await writeFile(file, css.replaceAll(/url\((["']?)\/_astro\//g, 'url($1./'));
}

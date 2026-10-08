// SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
// SPDX-License-Identifier: AGPL-3.0-only
import cloudflare from '@astrojs/cloudflare';
import react from '@astrojs/react';
import { d1, r2 } from '@emdash-cms/cloudflare';
import { defineConfig } from 'astro/config';
import emdash from 'emdash/astro';
import consolePipe from 'vite-plugin-console-pipe';
import { fileURLToPath } from 'node:url';

// The measured-data API must answer heartbeats before CMS setup or migrations.
const benchApi = {
  name: 'jubarte:bench-api',
  hooks: { 'astro:config:setup': ({ addMiddleware }) => {
    addMiddleware({ entrypoint: fileURLToPath(new URL('./src/bench-middleware.ts', import.meta.url)), order: 'pre' });
  } },
};

export default defineConfig({
  output: 'server',
  adapter: cloudflare({ imageService: 'compile' }),
  integrations: [benchApi, react(), emdash({
    database: d1({ binding: 'DB', session: 'auto' }),
    storage: r2({ binding: 'MEDIA' }),
  })],
  vite: { plugins: [consolePipe()], server: { allowedHosts: ['localhost', '127.0.0.1', 'host.docker.internal'] } },
  devToolbar: { enabled: false },
});

// SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
// SPDX-License-Identifier: AGPL-3.0-only
import { defineMiddleware } from 'astro:middleware';
import { env } from 'cloudflare:workers';
import { handleApi } from './lib/api';
import { D1Store } from './lib/store';

export const onRequest = defineMiddleware(async (context, next) => {
  if (context.url.pathname.startsWith('/api/') || context.url.pathname.startsWith('/artifacts/')) {
    return handleApi(context.request, { store: new D1Store(env.DB), bucket: env.MEDIA, token: (env as unknown as { INGEST_TOKEN?: string }).INGEST_TOKEN });
  }
  // This public benchmark does not expose CMS administration or first-user setup.
  if (context.url.pathname !== '/' && !context.url.pathname.startsWith('/_astro/')) {
    return new Response('Not found', { status: 404 });
  }
  return next();
});

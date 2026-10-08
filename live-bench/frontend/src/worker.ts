// SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
// SPDX-License-Identifier: AGPL-3.0-only
import { handle } from '@astrojs/cloudflare/handler';
import type { ExportedHandler, HTMLRewriter as Rewriter } from '@cloudflare/workers-types';
import { internalRequest } from './lib/paths';

declare const HTMLRewriter: { new(): Rewriter };

export default {
  async fetch(request, env, ctx) {
    const internal = internalRequest(request as unknown as Request);
    const response = await handle(internal.request, env, ctx);
    if (!internal.prefix || !response.headers.get('content-type')?.includes('text/html')) return response;
    // Vite emits root-relative asset URLs. Prefix them for all four aliases;
    // their requests are rewritten to the same internal asset manifest above.
    return new HTMLRewriter().on('[src], link[href]', {
      element(element) {
        for (const attribute of ['src', 'href']) {
          const value = element.getAttribute(attribute);
          if (value?.startsWith('/_astro/')) element.setAttribute(attribute, `${internal.prefix}${value}`);
        }
      },
    }).transform(response as never);
  },
} satisfies ExportedHandler<Env>;

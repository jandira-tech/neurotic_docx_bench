// SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
// SPDX-License-Identifier: AGPL-3.0-only
export function publicPrefix(path: string): string {
  return ['/docx-bench-live', '/live'].find((prefix) => path === prefix || path.startsWith(`${prefix}/`)) ?? '';
}

export function internalRequest(request: Request): { request: Request; prefix: string } {
  const url = new URL(request.url);
  const prefix = publicPrefix(url.pathname);
  if (prefix) url.pathname = url.pathname.slice(prefix.length) || '/';
  const headers = new Headers(request.headers);
  // A client cannot choose the prefix rendered into the page.
  headers.set('X-Bench-Prefix', prefix);
  return { request: new Request(url, { method: request.method, headers, body: ['GET', 'HEAD'].includes(request.method) ? null : request.body, redirect: request.redirect, duplex: 'half' } as RequestInit), prefix };
}

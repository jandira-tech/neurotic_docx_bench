// SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
// SPDX-License-Identifier: AGPL-3.0-only
import type { Cohort, Score } from './schema';

export class HttpError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

export function canonical(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (value !== null && typeof value === 'object') return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonical((value as Record<string, unknown>)[key])}`).join(',')}}`;
  return JSON.stringify(value);
}

export async function digest(bytes: Uint8Array): Promise<string> {
  const hash = await crypto.subtle.digest('SHA-256', bytes as BufferSource);
  return [...new Uint8Array(hash)].map((byte) => byte.toString(16).padStart(2, '0')).join('');
}

// Fixed-length digests avoid early exits and token-length-dependent comparisons.
export async function authorized(header: string | null, token: string | undefined): Promise<boolean> {
  if (!token || token.length < 24 || !header?.startsWith('Bearer ')) return false;
  const encoder = new TextEncoder();
  const [provided, expected] = await Promise.all([digest(encoder.encode(header.slice(7))), digest(encoder.encode(token))]);
  let difference = 0;
  for (let i = 0; i < expected.length; i++) difference |= provided.charCodeAt(i) ^ expected.charCodeAt(i);
  return difference === 0;
}

export function aggregate(scores: Score[]): Cohort[] {
  const groups = new Map<string, { cohort: Cohort; total: number }>();
  for (const score of scores) {
    if (!['ok', 'broken'].includes(score.status) || score.tool === score.reference_tool || score.overall === null || !score.reference_tool || !score.reference_renderer) continue;
    const key = canonical([score.tool, score.benchmark, score.reference_tool, score.reference_renderer]);
    const group = groups.get(key) ?? { cohort: { tool: score.tool, benchmark: score.benchmark, reference_tool: score.reference_tool, reference_renderer: score.reference_renderer, count: 0, broken: 0, mean: 0 }, total: 0 };
    group.cohort.count++;
    if (score.status === 'broken') group.cohort.broken++;
    group.total += score.status === 'broken' ? 0 : score.overall;
    group.cohort.mean = group.total / group.cohort.count;
    groups.set(key, group);
  }
  return [...groups.values()].map((group) => group.cohort);
}

export function parseRange(value: string | null, size: number): { offset: number; length: number } | undefined {
  if (!value) return undefined;
  const match = /^bytes=(\d*)-(\d*)$/.exec(value);
  if (!match || (!match[1] && !match[2]) || size === 0) throw new HttpError(416, 'Unsatisfiable range');
  const suffix = match[1] === '';
  const start = suffix ? Math.max(0, size - Number(match[2])) : Number(match[1]);
  const end = suffix || match[2] === '' ? size - 1 : Math.min(Number(match[2]), size - 1);
  if (!Number.isSafeInteger(start) || !Number.isSafeInteger(end) || start > end || start >= size) throw new HttpError(416, 'Unsatisfiable range');
  return { offset: start, length: end - start + 1 };
}

export async function boundedBody(request: Request, limit: number): Promise<Uint8Array> {
  const advertised = request.headers.get('content-length');
  if (advertised && (!/^\d+$/.test(advertised) || Number(advertised) > limit)) throw new HttpError(413, 'Request body too large');
  if (!request.body) return new Uint8Array();
  const reader = request.body.getReader();
  const chunks: Uint8Array[] = [];
  let length = 0;
  try {
    while (true) {
      const part = await reader.read();
      if (part.done) break;
      length += part.value.byteLength;
      if (length > limit) { await reader.cancel(); throw new HttpError(413, 'Request body too large'); }
      chunks.push(part.value);
    }
  } finally { reader.releaseLock(); }
  const bytes = new Uint8Array(length);
  let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
  return bytes;
}

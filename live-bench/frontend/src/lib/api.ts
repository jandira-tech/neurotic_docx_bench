// SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
// SPDX-License-Identifier: AGPL-3.0-only
import { z } from 'zod';
import { MAX_FILE_BYTES, artifactKey, batchSchema, identifier, liveSchema, mediaType, resultSchema, runSchema, sha256 } from './schema';
import { authorized, boundedBody, canonical, digest, HttpError, parseRange } from './policy';
import type { Store } from './store';

export interface ApiContext { store: Store; bucket: R2Bucket; token?: string }
const json = (data: unknown, status = 200) => Response.json(data, { status, headers: { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' } });
const requireRun = async (store: Store, id: string) => {
  const run = await store.run(id);
  if (!run) throw new HttpError(409, 'Run must be ingested first');
  return run;
};

async function payload<T>(request: Request, schema: z.ZodType<T>): Promise<T> {
  if (request.headers.get('content-type')?.split(';')[0].trim() !== 'application/json') throw new HttpError(415, 'Expected application/json');
  let value: unknown;
  try { value = JSON.parse(new TextDecoder().decode(await boundedBody(request, 256 * 1024))); }
  catch (error) { if (error instanceof HttpError) throw error; throw new HttpError(400, 'Invalid JSON'); }
  return schema.parse(value);
}

export async function handleApi(request: Request, context: ApiContext): Promise<Response> {
  const url = new URL(request.url);
  const { store, bucket } = context;
  try {
    if (url.pathname.startsWith('/api/ingest/')) {
      if (!(await authorized(request.headers.get('authorization'), context.token))) throw new HttpError(401, 'Unauthorized');
      if (url.pathname.startsWith('/api/ingest/artifacts/') && request.method === 'PUT') {
        const key = artifactKey.parse(decodeURIComponent(url.pathname.slice('/api/ingest/artifacts/'.length)));
        await requireRun(store, key.split('/')[0]);
        const type = mediaType.parse(request.headers.get('content-type')?.split(';')[0].trim());
        const expected = sha256.parse(request.headers.get('x-content-sha256'));
        const bytes = await boundedBody(request, MAX_FILE_BYTES);
        if (await digest(bytes) !== expected) throw new HttpError(422, 'Artifact checksum mismatch');
        const existing = await bucket.head(key);
        if (existing) {
          if (existing.customMetadata?.sha256 !== expected || existing.size !== bytes.length || existing.httpMetadata?.contentType !== type) throw new HttpError(409, 'Immutable artifact differs');
          return json({ ok: true, created: false });
        }
        const saved = await bucket.put(key, bytes, { onlyIf: { etagDoesNotMatch: '*' }, httpMetadata: { contentType: type }, customMetadata: { sha256: expected } });
        if (!saved) throw new HttpError(409, 'Artifact upload raced; retry');
        return json({ ok: true, created: true }, 201);
      }
      if (request.method !== 'POST') throw new HttpError(405, 'Method not allowed');
      if (url.pathname === '/api/ingest/run') return json({ ok: true, created: await store.saveRun(await payload(request, runSchema)) });
      if (url.pathname === '/api/ingest/live') {
        const live = await payload(request, liveSchema);
        await requireRun(store, live.run_id);
        await store.saveLive(live);
        return json({ ok: true });
      }
      if (url.pathname === '/api/ingest/result') {
        const result = await payload(request, resultSchema);
        await requireRun(store, result.run_id);
        for (const artifact of result.artifacts) {
          const object = await bucket.head(artifact.key);
          if (!object || object.customMetadata?.sha256 !== artifact.sha256 || object.size !== artifact.size || object.httpMetadata?.contentType !== artifact.content_type) throw new HttpError(409, 'Artifact must be uploaded and verified first');
        }
        return json({ ok: true, created: await store.saveResult(result) });
      }
      if (url.pathname === '/api/ingest/batch') {
        const batch = await payload(request, batchSchema);
        const run = await requireRun(store, batch.run_id);
        if (batch.count !== (run.config.batch_size ?? 100)) throw new HttpError(409, 'Batch must match configured batch size');
        const rows = await store.results({ run_id: batch.run_id, batch_id: batch.id, limit: 101 });
        const sequences = rows.map((row) => row.sequence).sort((a, b) => a - b);
        if (sequences.length !== batch.count || sequences.some((sequence, index) => sequence !== batch.first_sequence + index)) throw new HttpError(409, 'Batch requires every result in its exact sequence range');
        const manifest = await bucket.head(batch.manifest_key);
        if (!manifest || manifest.size > MAX_FILE_BYTES || manifest.httpMetadata?.contentType !== 'application/json' || !manifest.customMetadata?.sha256) throw new HttpError(409, 'Verified JSON manifest must be uploaded first');
        const manifestObject = await bucket.get(batch.manifest_key);
        if (!manifestObject) throw new HttpError(409, 'Manifest unavailable');
        let contents: { run: z.infer<typeof runSchema>; results: z.infer<typeof resultSchema>[] };
        try {
          const value = JSON.parse(await new Response(manifestObject.body as unknown as ReadableStream).text());
          if ('result_parts' in value) {
            const index = z.strictObject({ run: runSchema, result_parts: z.array(z.strictObject({ key: artifactKey, size: z.number().int().positive().max(MAX_FILE_BYTES), sha256 })).min(1).max(10) }).parse(value);
            if (new Set(index.result_parts.map((part) => part.key)).size !== index.result_parts.length || index.result_parts.some((part) => part.key === batch.manifest_key || !part.key.startsWith(`${batch.run_id}/${batch.last_sequence}/`))) throw new HttpError(422, 'Invalid archive part keys');
            const complete: z.infer<typeof resultSchema>[] = [];
            for (const part of index.result_parts) {
              const metadata = await bucket.head(part.key);
              if (!metadata || metadata.size !== part.size || metadata.customMetadata?.sha256 !== part.sha256 || metadata.httpMetadata?.contentType !== 'application/json') throw new HttpError(409, 'Archive part must be uploaded and verified first');
              const object = await bucket.get(part.key);
              if (!object) throw new HttpError(409, 'Archive part unavailable');
              complete.push(...z.strictObject({ results: z.array(resultSchema).min(1).max(10) }).parse(JSON.parse(await new Response(object.body as unknown as ReadableStream).text())).results);
            }
            contents = { run: index.run, results: complete };
          } else contents = z.strictObject({ run: runSchema, results: z.array(resultSchema).max(100) }).parse(value);
        }
        catch (error) { if (error instanceof HttpError) throw error; throw new HttpError(422, 'Manifest must contain the run and complete results'); }
        if (canonical(contents.run) !== canonical(run) || contents.results.length !== rows.length || new Set(contents.results.map((result) => result.id)).size !== rows.length || contents.results.some((result) => !rows.some((stored) => stored.id === result.id && canonical(stored) === canonical(result)))) throw new HttpError(409, 'Manifest differs from persisted batch evidence');
        return json({ ok: true, created: await store.saveBatch(batch) });
      }
      throw new HttpError(404, 'Unknown ingestion endpoint');
    }
    if (!['GET', 'HEAD'].includes(request.method)) throw new HttpError(405, 'Method not allowed');
    if (url.pathname === '/api/healthz') { await store.health(); return json({ ok: true, service: 'jubarte-live-bench' }); }
    if (url.pathname === '/api/live') {
      const live = await store.live();
      const run = await store.run(live?.run_id);
      const [results, summary] = await Promise.all([store.results({ run_id: run?.id, limit: 30 }), run ? store.summary(run.id) : Promise.resolve([])]);
      return json({ live, run, results, summary });
    }
    if (url.pathname === '/api/results') {
      const query = z.strictObject({ run_id: identifier.optional(), batch_id: identifier.optional(), before: z.coerce.number().int().positive().optional(), cursor: z.string().max(1000).optional(), q: z.string().trim().max(200).optional(), limit: z.coerce.number().int().min(1).max(100).default(30) }).parse(Object.fromEntries(url.searchParams));
      if (query.before && !query.run_id) throw new HttpError(400, 'Pagination requires run_id');
      const cursor = query.cursor ? z.strictObject({ completed_at: z.iso.datetime(), id: identifier }).parse(JSON.parse(atob(query.cursor))) : undefined;
      const results = await store.results({ ...query, cursor, limit: query.limit + 1 });
      const more = results.length > query.limit;
      const page = results.slice(0, query.limit);
      const last = page.at(-1);
      return json({ results: page, next_cursor: more && last ? btoa(JSON.stringify({ completed_at: last.completed_at, id: last.id })) : null, next_before: more && last ? last.sequence : null });
    }
    if (url.pathname.startsWith('/artifacts/')) {
      const key = artifactKey.parse(decodeURIComponent(url.pathname.slice('/artifacts/'.length)));
      const metadata = await bucket.head(key);
      if (!metadata) throw new HttpError(404, 'Artifact not found');
      let range: ReturnType<typeof parseRange>;
      try { range = parseRange(request.headers.get('range'), metadata.size); }
      catch (error) { if (error instanceof HttpError && error.status === 416) return new Response(null, { status: 416, headers: { 'Content-Range': `bytes */${metadata.size}` } }); throw error; }
      const object = request.method === 'HEAD' ? null : await bucket.get(key, range ? { range } : undefined);
      if (request.method !== 'HEAD' && !object) throw new HttpError(404, 'Artifact not found');
      const headers = new Headers({ 'Content-Type': metadata.httpMetadata?.contentType ?? 'application/octet-stream', 'Content-Length': String(range?.length ?? metadata.size), 'Accept-Ranges': 'bytes', 'Cache-Control': 'public, max-age=31536000, immutable', 'ETag': metadata.httpEtag, 'X-Content-Type-Options': 'nosniff' });
      if (range) headers.set('Content-Range', `bytes ${range.offset}-${range.offset + range.length - 1}/${metadata.size}`);
      return new Response((object?.body ?? null) as ReadableStream | null, { status: range ? 206 : 200, headers });
    }
    throw new HttpError(404, 'Not found');
  } catch (error) {
    if (error instanceof HttpError) return json({ error: error.message }, error.status);
    if (error instanceof z.ZodError || error instanceof URIError || error instanceof SyntaxError || (error instanceof DOMException && error.name === 'InvalidCharacterError')) return json({ error: 'Invalid payload or parameters' }, 400);
    // Never publish D1/R2 exception messages, SQL, credentials or raw payloads.
    console.error('[bench-api] storage operation failed');
    return json({ error: 'Storage temporarily unavailable' }, 503);
  }
}

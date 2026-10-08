// SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
// SPDX-License-Identifier: AGPL-3.0-only
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { handleApi } from '../src/lib/api';
import { digest } from '../src/lib/policy';
import { artifactSchema, MAX_FILE_BYTES } from '../src/lib/schema';
import { at, database, MemoryBucket, result, run, token } from './fakes';

let db: ReturnType<typeof database>;
let bucket: MemoryBucket;
const request = (path: string, value?: unknown, method = value === undefined ? 'GET' : 'POST', headers: Record<string, string> = {}) => new Request(`https://test${path}`, { method, headers: { ...(value === undefined ? {} : { 'Content-Type': 'application/json' }), Authorization: `Bearer ${token}`, ...headers }, body: value === undefined ? undefined : JSON.stringify(value) });
const call = (req: Request) => handleApi(req, { store: db.store, bucket: bucket.binding(), token });
const ingest = (kind: string, value: unknown) => call(request(`/api/ingest/${kind}`, value));
const bytes = new TextEncoder().encode('%PDF-actual-test');
let checksum: string;
const key = 'run-1/1/candidate.pdf';
const upload = (artifactKey = key, content = bytes, hash = checksum, type = 'application/pdf') => call(new Request(`https://test/api/ingest/artifacts/${artifactKey}`, { method: 'PUT', headers: { Authorization: `Bearer ${token}`, 'Content-Type': type, 'X-Content-SHA256': hash }, body: content }));
beforeEach(async () => { db = database(); bucket = new MemoryBucket(); checksum = await digest(bytes); });
afterEach(() => db.close());

describe('measured-data API', () => {
  it('searches full 64-character corpus IDs and long metadata as literal substrings', async () => {
    await ingest('run', run);
    const corpusId = 'a9'.repeat(32);
    const description = 'long search phrase '.repeat(8).trim();
    await ingest('result', { ...result, source: { ...result.source, id: corpusId, metadata: { description } } });
    for (const term of [corpusId, corpusId.toUpperCase(), description]) {
      const response = await call(request(`/api/results?q=${encodeURIComponent(term)}`));
      expect(response.status).toBe(200);
      expect((await response.json()).results.map((item: { id: string }) => item.id)).toEqual([result.id]);
    }
    expect((await (await call(request('/api/results?q=%25'))).json()).results).toEqual([]);
  });
  it('enforces the 20 MB upload and metadata limit without changing old history', async () => {
    await ingest('run', run);
    expect(MAX_FILE_BYTES).toBe(20_000_000);
    const descriptor = { key, content_type: 'application/pdf', sha256: checksum, size: MAX_FILE_BYTES };
    expect(artifactSchema.safeParse(descriptor).success).toBe(true);
    expect(artifactSchema.safeParse({ ...descriptor, size: MAX_FILE_BYTES + 1 }).success).toBe(false);
    const oversized = new Request(`https://test/api/ingest/artifacts/${key}`, { method: 'PUT', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/pdf', 'X-Content-SHA256': checksum, 'Content-Length': String(MAX_FILE_BYTES + 1) }, body: bytes });
    expect((await call(oversized)).status).toBe(413);
    expect(bucket.objects.size).toBe(0);
    expect((await ingest('result', { ...result, artifacts: [{ ...descriptor, size: MAX_FILE_BYTES + 1 }] })).status).toBe(400);
  });
  it('verifies every archive part before preserving the complete group', async () => {
    await ingest('run', run);
    const second = { ...result, id: 'review-2', sequence: 2 };
    await ingest('result', result); await ingest('result', second);
    const batch = { id: 'batch-1', run_id: run.id, first_sequence: 1, last_sequence: 2, count: 2, completed_at: at, manifest_key: 'run-1/2/manifest.json' };
    const partKey = 'run-1/2/manifest-part-001.json';
    const data = new TextEncoder().encode(JSON.stringify({ results: [result, second] }));
    const hash = await digest(data);
    const index = new TextEncoder().encode(JSON.stringify({ run, result_parts: [{ key: partKey, size: data.length, sha256: hash }] }));
    await upload(batch.manifest_key, index, await digest(index), 'application/json');
    expect((await ingest('batch', batch)).status).toBe(409);
    await upload(partKey, data, hash, 'application/json');
    bucket.missingBody = true; expect((await ingest('batch', batch)).status).toBe(409); bucket.missingBody = false;
    expect((await ingest('batch', batch)).status).toBe(200);
    const wrong = new TextEncoder().encode(JSON.stringify({ run, result_parts: [{ key: batch.manifest_key, size: data.length, sha256: hash }] }));
    bucket.objects.delete(batch.manifest_key); await upload(batch.manifest_key, wrong, await digest(wrong), 'application/json');
    expect((await ingest('batch', batch)).status).toBe(422);
  });
  it('accepts perfect-score floating-point noise and keeps retries immutable', async () => {
    await ingest('run', run);
    const perfect = { ...result, scores: [{ ...result.scores[0], overall: 100.00000000000003 }] };
    expect((await ingest('result', perfect)).status).toBe(200);
    expect((await db.store.results({ limit: 1 }))[0].scores[0].overall).toBe(100);
    expect(await (await ingest('result', perfect)).json()).toEqual({ ok: true, created: false });
    expect((await ingest('result', { ...result, id: 'wrong', sequence: 2, scores: [{ ...result.scores[0], overall: 101 }] })).status).toBe(400);
  });
  it('serves a no-store health probe and an honest empty feed before CMS setup', async () => {
    const health = await call(request('/api/healthz')); expect(health.status).toBe(200); expect(health.headers.get('cache-control')).toBe('no-store');
    const empty = await call(request('/api/live')); expect(await empty.json()).toEqual({ live: null, run: null, results: [], summary: [] });
    expect((await call(request('/api/results'))).status).toBe(200);
  });
  it('requires bearer auth for every ingestion path and forbids unintended methods', async () => {
    expect((await call(request('/api/ingest/run', run, 'POST', { Authorization: 'Bearer wrong' }))).status).toBe(401);
    expect((await call(request('/api/ingest/run'))).status).toBe(405);
    expect((await call(request('/api/live', {}, 'POST'))).status).toBe(405);
    expect((await call(request('/api/ingest/unknown', {}))).status).toBe(404);
    expect((await call(request('/unknown'))).status).toBe(404);
  });
  it('rejects wrong media types, malformed/oversize JSON, unknown fields and unknown runs', async () => {
    expect((await call(request('/api/ingest/run', run, 'POST', { 'Content-Type': 'text/plain' }))).status).toBe(415);
    expect((await call(new Request('https://test/api/ingest/run', { method: 'POST', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }, body: '{' }))).status).toBe(400);
    expect((await call(request('/api/ingest/run', run, 'POST', { 'Content-Length': '999999' }))).status).toBe(413);
    expect((await ingest('run', { ...run, accidental_secret: 'secret' })).status).toBe(400);
    expect((await ingest('result', result)).status).toBe(409);
  });
  it('preserves immutable runs and original metadata, normalizes timestamps and retries safely', async () => {
    expect(await (await ingest('run', run)).json()).toEqual({ ok: true, created: true });
    expect(await (await ingest('run', { ...run, started_at: '2026-10-07T20:00:00-04:00' })).json()).toEqual({ ok: true, created: false });
    expect((await ingest('run', { ...run, versions: { jubarte: 'other' } })).status).toBe(409);
    expect(await db.store.run('absent')).toBeNull();
    expect(await db.store.run()).toEqual(run);
  });
  it('keeps live state monotonic across delayed heartbeats and exposes exact metadata', async () => {
    await ingest('run', run);
    const live = { run_id: run.id, sequence: 2, batch_id: 'batch-1', fixture_id: 'fixture-2', phase: 'soffice:convert', updated_at: at, queue_depth: 200, completed: 1 };
    expect((await ingest('live', live)).status).toBe(200);
    await ingest('live', { ...live, sequence: 1, updated_at: '2026-10-08T00:00:01Z' });
    expect(await db.store.live()).toEqual(live);
    await ingest('live', { ...live, updated_at: '2026-10-07T23:59:59Z' });
    expect(await db.store.live()).toEqual(live);
    await ingest('live', { ...live, phase: 'jubarte:convert', updated_at: '2026-10-08T00:00:02Z' });
    expect((await db.store.live())?.phase).toBe('jubarte:convert');
    expect((await ingest('live', { ...live, run_id: 'absent' })).status).toBe(409);
    const feed = await (await call(request('/api/live'))).json(); expect(feed.run).toEqual(run); expect(feed.live.sequence).toBe(2); expect(feed).not.toHaveProperty('batches');
  });
  it('verifies immutable artifacts including type, size, checksum and race conditions', async () => {
    expect((await upload()).status).toBe(409);
    await ingest('run', run);
    expect((await upload(key, bytes, 'f'.repeat(64))).status).toBe(422);
    expect((await upload(key, bytes, checksum, 'text/html')).status).toBe(400);
    expect((await upload('run-1/1/a%2Fb.pdf')).status).toBe(400);
    expect((await upload('run-1/1/%ZZ')).status).toBe(400);
    expect((await upload()).status).toBe(201);
    expect(await (await upload()).json()).toEqual({ ok: true, created: false });
    expect((await upload(key, new TextEncoder().encode('different'), await digest(new TextEncoder().encode('different')))).status).toBe(409);
    expect((await upload(key, bytes, checksum, 'text/plain')).status).toBe(409);
    bucket.race = true; expect((await upload('run-1/1/raced.pdf')).status).toBe(409);
  });
  it('rejects results until each declared artifact is present and verified', async () => {
    await ingest('run', run);
    const withArtifact = { ...result, artifacts: [{ key, content_type: 'application/pdf', sha256: checksum, size: bytes.length }], stages: [{ tool: 'jubarte', operation: 'convert', status: 'ok', duration_ms: 4, artifact: key }] };
    expect((await ingest('result', withArtifact)).status).toBe(409);
    await upload();
    expect((await ingest('result', { ...withArtifact, artifacts: [{ ...withArtifact.artifacts[0], size: 1 }] })).status).toBe(409);
    expect((await ingest('result', { ...withArtifact, artifacts: [{ ...withArtifact.artifacts[0], sha256: 'a'.repeat(64) }] })).status).toBe(409);
    expect((await ingest('result', { ...withArtifact, artifacts: [{ ...withArtifact.artifacts[0], content_type: 'text/plain' }] })).status).toBe(409);
    expect(await (await ingest('result', withArtifact)).json()).toEqual({ ok: true, created: true });
    expect(await (await ingest('result', withArtifact)).json()).toEqual({ ok: true, created: false });
    expect((await ingest('result', { ...withArtifact, source: { ...result.source, id: 'different' } })).status).toBe(409);
    expect((await ingest('result', { ...withArtifact, id: 'other-review' })).status).toBe(409);
    expect((await db.store.results({ limit: 10 }))[0].artifacts).toEqual(withArtifact.artifacts);
  });
  it('retains repeated corpus IDs as independent review occurrences across runs and paginates ties stably', async () => {
    await ingest('run', run); await ingest('run', { ...run, id: 'run-2' });
    await ingest('result', result);
    await ingest('result', { ...result, id: 'review-2', run_id: 'run-2' });
    await ingest('result', { ...result, id: 'review-3', sequence: 2 });
    const first = await (await call(request('/api/results?limit=1'))).json(); expect(first.results[0].id).toBe('review-3'); expect(first.next_cursor).toBeTypeOf('string');
    const second = await (await call(request(`/api/results?limit=1&cursor=${encodeURIComponent(first.next_cursor)}`))).json(); expect(second.results[0].id).toBe('review-2');
    const third = await (await call(request(`/api/results?limit=1&cursor=${encodeURIComponent(second.next_cursor)}`))).json(); expect(third.results[0].id).toBe('review-1'); expect(third.next_cursor).toBeNull();
    expect((await (await call(request('/api/results?run_id=run-1&before=2'))).json()).results.map((item: { id: string }) => item.id)).toEqual(['review-1']);
    expect((await (await call(request('/api/results?batch_id=batch-1'))).json()).results).toHaveLength(3);
    expect((await call(request('/api/results?before=2'))).status).toBe(400);
    expect((await call(request('/api/results?cursor=%25'))).status).toBe(400);
    expect((await call(request('/api/results?cursor=YWJj'))).status).toBe(400);
    expect((await call(request('/api/results?limit=101'))).status).toBe(400);
    expect((await call(request('/api/results?secret=1'))).status).toBe(400);
    expect((await (await call(request('/api/results?q=contract'))).json()).results).toHaveLength(3);
    expect((await (await call(request('/api/results?q=fixture-1'))).json()).results).toHaveLength(3);
    expect((await (await call(request('/api/results?q=review-2'))).json()).results).toHaveLength(1);
    expect((await (await call(request('/api/results?q=%25'))).json()).results).toHaveLength(0);
  });
  it('aggregates real scores by reference cohort, counts broken0, excludes unsupported/self/error rows', async () => {
    await ingest('run', run); await ingest('result', result);
    await ingest('result', { ...result, id: 'review-2', sequence: 2, scores: [{ ...result.scores[0], status: 'broken', overall: 0 }, { ...result.scores[0], tool: 'docxide', status: 'unavailable', overall: null }, { ...result.scores[0], tool: 'soffice', status: 'reference', overall: null }, { ...result.scores[0], tool: 'docxodus', status: 'error', overall: null, reference_tool: null, reference_renderer: null }] });
    expect(await db.store.summary(run.id)).toEqual([{ tool: 'jubarte', benchmark: 'convert', reference_tool: 'soffice', reference_renderer: 'soffice', count: 2, broken: 1, mean: 40 }]);
    const feed = await (await call(request('/api/live'))).json(); expect(feed.summary[0].mean).toBe(40); expect(feed.results).toHaveLength(2);
  });
  it('archives only exact fully persisted internal batches with verified JSON manifests', async () => {
    await ingest('run', run);
    const batch = { id: 'batch-1', run_id: run.id, first_sequence: 1, last_sequence: 2, count: 2, completed_at: at, manifest_key: 'run-1/2/manifest.json' };
    expect((await ingest('batch', batch)).status).toBe(409);
    await ingest('result', result); await ingest('result', { ...result, id: 'review-2', sequence: 2 });
    expect((await ingest('batch', batch)).status).toBe(409);
    await upload(batch.manifest_key); expect((await ingest('batch', batch)).status).toBe(409);
    bucket.objects.delete(batch.manifest_key); await upload(batch.manifest_key, bytes, checksum, 'application/json');
    expect((await ingest('batch', batch)).status).toBe(422);
    const manifestResults = [result, { ...result, id: 'review-2', sequence: 2 }];
    const manifestBytes = new TextEncoder().encode(JSON.stringify({ run, results: manifestResults }));
    bucket.objects.delete(batch.manifest_key); await upload(batch.manifest_key, manifestBytes, await digest(manifestBytes), 'application/json');
    bucket.missingBody = true; expect((await ingest('batch', batch)).status).toBe(409); bucket.missingBody = false;
    expect(await (await ingest('batch', batch)).json()).toEqual({ ok: true, created: true }); expect(await (await ingest('batch', batch)).json()).toEqual({ ok: true, created: false });
    expect((await ingest('batch', { ...batch, completed_at: '2026-10-08T00:00:01Z' })).status).toBe(409);
    expect((await ingest('batch', { ...batch, id: 'wrong', count: 1, last_sequence: 1 })).status).toBe(409);
    expect(await db.store.batches(run.id)).toEqual([batch]); expect(await db.store.batches()).toEqual([batch]);
    const badContents = new TextEncoder().encode(JSON.stringify({ run, results: [result, result] }));
    bucket.objects.delete(batch.manifest_key); await upload(batch.manifest_key, badContents, await digest(badContents), 'application/json');
    expect((await ingest('batch', batch)).status).toBe(409);
    const wrongRun = new TextEncoder().encode(JSON.stringify({ run: { ...run, id: 'other' }, results: manifestResults }));
    bucket.objects.delete(batch.manifest_key); await upload(batch.manifest_key, wrongRun, await digest(wrongRun), 'application/json');
    expect((await ingest('batch', batch)).status).toBe(409);
  });
  it('serves PDFs with range support, immutable caching and HEAD', async () => {
    await ingest('run', run); await upload();
    const full = await call(request(`/artifacts/${key}`)); expect(full.status).toBe(200); expect(await full.text()).toBe('%PDF-actual-test'); expect(full.headers.get('cache-control')).toContain('immutable'); expect(full.headers.get('x-content-type-options')).toBe('nosniff');
    const partial = await call(request(`/artifacts/${key}`, undefined, 'GET', { Range: 'bytes=0-3' })); expect(partial.status).toBe(206); expect(await partial.text()).toBe('%PDF'); expect(partial.headers.get('content-range')).toBe(`bytes 0-3/${bytes.length}`);
    const suffix = await call(request(`/artifacts/${key}`, undefined, 'GET', { Range: 'bytes=-4' })); expect(await suffix.text()).toBe('test');
    const head = await call(request(`/artifacts/${key}`, undefined, 'HEAD')); expect(await head.text()).toBe(''); expect(head.headers.get('content-length')).toBe(String(bytes.length));
    expect((await call(request(`/artifacts/${key}`, undefined, 'GET', { Range: 'bytes=999-' }))).status).toBe(416);
    expect((await call(request('/artifacts/run-1/1/missing.pdf'))).status).toBe(404);
    bucket.missingBody = true; expect((await call(request(`/artifacts/${key}`))).status).toBe(404);
    bucket.objects.get(key)!.httpMetadata = {}; bucket.missingBody = false; expect((await call(request(`/artifacts/${key}`))).headers.get('content-type')).toBe('application/octet-stream');
  });
  it('bounds storage errors without leaking SQL or credentials', async () => {
    db.sqlite.exec('DROP TABLE bench_results');
    const response = await call(request('/api/live')); expect(response.status).toBe(503); expect(await response.text()).toBe('{"error":"Storage temporarily unavailable"}');
  });
});

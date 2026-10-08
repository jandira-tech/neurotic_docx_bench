// SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from 'vitest';
import { aggregate, authorized, boundedBody, canonical, digest, HttpError, parseRange } from '../src/lib/policy';
import { artifactKey, batchSchema, resultSchema, runSchema, scoreSchema, sourceSchema } from '../src/lib/schema';
import { internalRequest, publicPrefix } from '../src/lib/paths';
import { artifactUrl, connection, delayedResults, metricLines, operationName, pdfGeometry, pdfPair, scoreText, toolName } from '../src/lib/view-model';
import { at, result, run, token } from './fakes';

describe('ingestion policy', () => {
  it('bounds PDF preview resolution while retaining the paper aspect ratio', () => {
    expect(pdfGeometry(600, 800, 300, 2)).toEqual({ scale: 1, width: 300, height: 400 });
    const huge = pdfGeometry(10000, 10000, 10000, 4);
    expect(huge.scale ** 2 * 10000 ** 2).toBeLessThanOrEqual(2_000_001);
    expect(pdfGeometry(600, 800, 0, 0).width).toBe(1);
    for (const dimensions of [[0, 800], [600, -1], [NaN, 800], [600, Infinity]]) expect(() => pdfGeometry(dimensions[0], dimensions[1], 300, 2)).toThrow('Invalid PDF geometry');
  });
  it('canonicalizes nested objects without changing arrays', () => expect(canonical({ z: [{ y: null, b: true }], a: 1 })).toBe('{"a":1,"z":[{"b":true,"y":null}]}'));
  it('hashes exact bytes', async () => expect(await digest(new TextEncoder().encode('abc'))).toBe('ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'));
  it('authenticates only full bearer tokens', async () => {
    expect(await authorized(`Bearer ${token}`, token)).toBe(true);
    expect(await authorized(`Bearer ${token}x`, token)).toBe(false);
    expect(await authorized(null, token)).toBe(false);
    expect(await authorized(`Basic ${token}`, token)).toBe(false);
    expect(await authorized(`Bearer ${token}`, undefined)).toBe(false);
    expect(await authorized('Bearer short', 'short')).toBe(false);
  });
  it('bounds streamed bodies even when length is not declared', async () => {
    expect(await boundedBody(new Request('https://test'), 2)).toHaveLength(0);
    expect(new TextDecoder().decode(await boundedBody(new Request('https://test', { method: 'POST', body: 'abc' }), 3))).toBe('abc');
    await expect(boundedBody(new Request('https://test', { method: 'POST', body: 'abcd' }), 3)).rejects.toMatchObject({ status: 413 });
    await expect(boundedBody(new Request('https://test', { method: 'POST', headers: { 'Content-Length': '4' }, body: 'ab' }), 3)).rejects.toMatchObject({ status: 413 });
    await expect(boundedBody(new Request('https://test', { method: 'POST', headers: { 'Content-Length': 'abc' }, body: 'ab' }), 3)).rejects.toMatchObject({ status: 413 });
  });
  it('supports bounded, open and suffix ranges', () => {
    expect(parseRange(null, 10)).toBeUndefined();
    expect(parseRange('bytes=1-4', 10)).toEqual({ offset: 1, length: 4 });
    expect(parseRange('bytes=8-', 10)).toEqual({ offset: 8, length: 2 });
    expect(parseRange('bytes=-3', 10)).toEqual({ offset: 7, length: 3 });
    expect(parseRange('bytes=-20', 10)).toEqual({ offset: 0, length: 10 });
    expect(parseRange('bytes=1-20', 10)).toEqual({ offset: 1, length: 9 });
    for (const range of ['bytes=10-', 'bytes=5-1', 'bytes=-0', 'bytes=-', 'bytes=1-2,4-5', 'bytes=99999999999999999999-']) expect(() => parseRange(range, 10)).toThrow(HttpError);
    expect(() => parseRange('bytes=0-', 0)).toThrow(HttpError);
  });
  it('counts broken0, excludes unavailable, errors and self references, separates cohorts', () => {
    const score = result.scores[0];
    const rows = aggregate([score, { ...score, status: 'broken', overall: 0 }, { ...score, status: 'error', overall: null }, { ...score, status: 'unavailable', overall: null }, { ...score, status: 'reference', overall: null }, { ...score, tool: 'soffice' }, { ...score, overall: null }, { ...score, reference_tool: null }, { ...score, reference_renderer: null }, { ...score, reference_renderer: 'word' }]);
    expect(rows).toEqual([{ tool: 'jubarte', benchmark: 'convert', reference_tool: 'soffice', reference_renderer: 'soffice', count: 2, broken: 1, mean: 40 }, { tool: 'jubarte', benchmark: 'convert', reference_tool: 'soffice', reference_renderer: 'word', count: 1, broken: 0, mean: 80 }]);
  });
});

describe('strict schemas', () => {
  it('preserves bounded corpus, download/security and stage metadata', () => {
    expect(resultSchema.parse({ ...result, source: { ...result.source, type: null, language: 'en', security: { safe: true }, metadata: { nested: { confidence: 0.9 } } }, stages: [{ tool: 'soffice', target_tool: 'jubarte', operation: 'security_preflight', status: 'ok', duration_ms: 1, metadata: { pages: 2 } }] }).stages[0].target_tool).toBe('jubarte');
    expect(runSchema.parse(run)).toEqual(run);
    expect(runSchema.safeParse({ ...run, config: {} }).success).toBe(true);
    expect(runSchema.safeParse({ ...run, config: { batch_size: 0 } }).success).toBe(false);
  });
  it('rejects dangerous URLs, keys and unknown fields', () => {
    for (const url of ['file:///etc/passwd', 'javascript:alert(1)', 'generated://arbitrary.docx']) expect(sourceSchema.safeParse({ ...result.source, url }).success).toBe(false);
    for (const key of ['../1/f.pdf', 'run/../f.pdf', 'run/1/a/b.pdf', 'run/01/f.pdf', 'run/1/..']) expect(artifactKey.safeParse(key).success).toBe(false);
    expect(resultSchema.safeParse({ ...result, secret: token }).success).toBe(false);
  });
  it('requires real scores and distinguishes failed candidates from infrastructure errors', () => {
    const score = result.scores[0];
    expect(scoreSchema.safeParse({ ...score, overall: null }).success).toBe(false);
    expect(scoreSchema.safeParse({ ...score, overall: 90, status: 'broken' }).success).toBe(false);
    expect(scoreSchema.safeParse({ ...score, status: 'error', overall: null, reference_tool: null, reference_renderer: null }).success).toBe(true);
    expect(scoreSchema.safeParse({ ...score, status: 'reference', overall: 100 }).success).toBe(false);
    expect(scoreSchema.safeParse({ ...score, reference_tool: null }).success).toBe(false);
    expect(scoreSchema.safeParse({ ...score, reference_renderer: null }).success).toBe(false);
  });
  it('rejects duplicate scores, wrong artifact ownership and undeclared stage artifacts', () => {
    expect(resultSchema.safeParse({ ...result, scores: [result.scores[0], result.scores[0]] }).success).toBe(false);
    const artifact = { key: 'run-1/1/a.pdf', content_type: 'application/pdf', size: 0, sha256: 'a'.repeat(64), metadata: { mime: 'pdf' } };
    expect(resultSchema.safeParse({ ...result, artifacts: [artifact, artifact] }).success).toBe(false);
    expect(resultSchema.safeParse({ ...result, artifacts: [{ ...artifact, key: 'run-2/1/a.pdf' }] }).success).toBe(false);
    expect(resultSchema.safeParse({ ...result, stages: [{ tool: 'jubarte', operation: 'convert', status: 'ok', duration_ms: 0, artifact: artifact.key }] }).success).toBe(false);
    expect(resultSchema.safeParse({ ...result, artifacts: [artifact], stages: [{ tool: 'jubarte', operation: 'convert', status: 'ok', duration_ms: 0, artifact: artifact.key }] }).success).toBe(true);
    expect(batchSchema.safeParse({ id: 'batch-1', run_id: run.id, first_sequence: 1, last_sequence: 2, count: 2, completed_at: at, manifest_key: 'run-1/2/manifest.json' }).success).toBe(true);
    expect(batchSchema.safeParse({ id: 'batch-1', run_id: run.id, first_sequence: 1, last_sequence: 3, count: 2, completed_at: at, manifest_key: 'run-1/2/manifest.json' }).success).toBe(false);
  });
});

describe('public view policies', () => {
  it('routes only recognized path boundaries and overrides forged prefixes', () => {
    expect(publicPrefix('/live')).toBe('/live'); expect(publicPrefix('/live/api/live')).toBe('/live'); expect(publicPrefix('/docx-bench-live/_astro/a.js')).toBe('/docx-bench-live'); expect(publicPrefix('/lively')).toBe(''); expect(publicPrefix('/other')).toBe('');
    const forwarded = internalRequest(new Request('https://site/live/api/live?q=x', { headers: { 'X-Bench-Prefix': 'evil' } }));
    expect(forwarded.request.url).toBe('https://site/api/live?q=x'); expect(forwarded.request.headers.get('X-Bench-Prefix')).toBe('/live');
    expect(new URL(internalRequest(new Request('https://site/live')).request.url).pathname).toBe('/');
    expect(internalRequest(new Request('https://site/', { headers: { 'X-Bench-Prefix': 'evil' } })).request.headers.get('X-Bench-Prefix')).toBe('');
    expect(internalRequest(new Request('https://site/live/api/ingest/run', { method: 'POST', body: 'a' })).request.method).toBe('POST');
  });
  it('reports actual freshness without assuming a running worker', () => {
    const snapshot = { live: { run_id: run.id, sequence: 1, batch_id: 'batch', fixture_id: 'fixture', phase: 'convert', updated_at: at, queue_depth: 1, completed: 0 }, run, results: [result], summary: [] };
    expect(connection(null, 0, true).state).toBe('offline'); expect(connection(null, 0, false).state).toBe('waiting'); expect(connection({ ...snapshot, live: null }, 0, false).state).toBe('waiting');
    expect(connection(snapshot, Date.parse(at) + 45000, false)).toMatchObject({ state: 'live', age: 45 }); expect(connection(snapshot, Date.parse(at) + 46000, false).state).toBe('stale'); expect(connection(snapshot, 0, false).age).toBe(0);
    expect(delayedResults([result], Date.parse(at) + 9999)).toHaveLength(0); expect(delayedResults([result], Date.parse(at) + 10000)).toEqual([result]); expect(delayedResults([result], Date.parse(at), 0)).toHaveLength(1);
  });
  it('selects candidate/reference PDFs by rendering target and displays actual metrics', () => {
    const scored = { ...result, stages: [{ tool: 'jubarte', operation: 'convert' as const, status: 'ok' as const, duration_ms: 1, artifact: 'run-1/1/c.pdf' }, { tool: 'soffice', operation: 'convert' as const, status: 'ok' as const, duration_ms: 1, artifact: 'run-1/1/r.pdf' }, { tool: 'soffice', target_tool: 'jubarte', operation: 'redline_render' as const, status: 'ok' as const, duration_ms: 1, artifact: 'run-1/1/red.pdf' }] };
    expect(pdfPair(scored, 'convert', 'jubarte')).toMatchObject({ candidate: 'run-1/1/c.pdf', reference: 'run-1/1/r.pdf' }); expect(pdfPair(scored, 'redline', 'jubarte').candidate).toBe('run-1/1/red.pdf'); expect(pdfPair(undefined, 'convert', 'other').score).toBeUndefined();
    expect(pdfPair({ ...scored, scores: [{ ...result.scores[0], reference_tool: null }] }, 'convert', 'jubarte').reference).toBeUndefined();
    expect(artifactUrl('run/1/a.pdf', '/live')).toBe('/live/artifacts/run/1/a.pdf'); expect(artifactUrl('run/1/a.pdf')).toBe('/artifacts/run/1/a.pdf'); expect(toolName('jubarte')).toBe('Jubarte'); expect(toolName('new-tool')).toBe('new-tool'); expect(toolName(null)).toBe('Unavailable'); expect(operationName('redline_render')).toBe('redline render');
    expect(scoreText(result.scores[0])).toBe('80.00'); expect(scoreText({ ...result.scores[0], status: 'broken', overall: 0 })).toBe('BROKEN · 0'); expect(scoreText({ ...result.scores[0], status: 'unavailable', overall: null })).toBe('UNAVAILABLE');
    expect(metricLines(undefined)).toEqual([]); expect(metricLines({ ...result.scores[0], metrics: { pages: 2, ink: 0.5, nested: { a: 1 } }, functional: { tracked: true, note: 'abc' } })).toEqual([['pages', '2'], ['ink', '0.5000'], ['nested', '{"a":1}'], ['tracked', 'true'], ['note', 'abc']]);
  });
});

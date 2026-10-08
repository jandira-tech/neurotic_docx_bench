// SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
// SPDX-License-Identifier: AGPL-3.0-only
import { DatabaseSync } from 'node:sqlite';
import migration from '../migrations/0001_live_bench.sql?raw';
import rollups from '../migrations/0002_cohort_rollups.sql?raw';
import { D1Store } from '../src/lib/store';
import type { Result, Run } from '../src/lib/schema';

// In-memory SQLite uses D1's SQL dialect and transactions without disk/network.
export function database() {
  const sqlite = new DatabaseSync(':memory:');
  sqlite.exec(migration);
  sqlite.exec(rollups);
  class Statement {
    values: (string | number | null)[] = [];
    constructor(private sql: string) {}
    bind(...values: (string | number | null)[]) { this.values = values; return this; }
    async first() { return sqlite.prepare(this.sql).get(...this.values) ?? null; }
    async all() { return { results: sqlite.prepare(this.sql).all(...this.values) }; }
    async run() { return sqlite.prepare(this.sql).run(...this.values); }
  }
  const db = { prepare: (sql: string) => new Statement(sql), batch: async (statements: Statement[]) => {
    sqlite.exec('BEGIN');
    try { const results = []; for (const statement of statements) results.push(await statement.run()); sqlite.exec('COMMIT'); return results; }
    catch (error) { sqlite.exec('ROLLBACK'); throw error; }
  } } as unknown as D1Database;
  return { store: new D1Store(db), close: () => sqlite.close(), sqlite };
}

export class MemoryBucket {
  objects = new Map<string, { bytes: Uint8Array; httpMetadata: { contentType?: string }; customMetadata: Record<string, string>; httpEtag: string; size: number }>();
  race = false;
  missingBody = false;
  async head(key: string) { return this.objects.get(key) ?? null; }
  async put(key: string, bytes: Uint8Array, options: { httpMetadata: { contentType: string }; customMetadata: Record<string, string> }) {
    if (this.race) return null;
    const object = { bytes: bytes.slice(), httpMetadata: options.httpMetadata, customMetadata: options.customMetadata, httpEtag: '"test-etag"', size: bytes.byteLength };
    this.objects.set(key, object); return object;
  }
  async get(key: string, options?: { range?: { offset: number; length: number } }) {
    const object = await this.head(key);
    if (!object || this.missingBody) return null;
    const bytes = options?.range ? object.bytes.slice(options.range.offset, options.range.offset + options.range.length) : object.bytes;
    return { ...object, body: new ReadableStream({ start(controller) { controller.enqueue(bytes); controller.close(); } }) };
  }
  binding() { return this as unknown as R2Bucket; }
}

export const token = 'test-ingest-token-at-least-24-chars';
export const at = '2026-10-08T00:00:00.000Z';
export const run: Run = { id: 'run-1', started_at: at, versions: { jubarte: 'sha256:abc' }, config: { batch_size: 2 } };
export const result: Result = {
  id: 'review-1', run_id: run.id, sequence: 1, batch_id: 'batch-1', source: { id: 'fixture-1', url: 'https://example.org/fixture.docx', sha256: null, review_id: 'review-1', metadata: { filename: 'contract.docx', language: 'en' } },
  previous: { id: 'seed', url: 'generated://starting_point.docx', sha256: null }, completed_at: at,
  stages: [], scores: [{ tool: 'jubarte', benchmark: 'convert', status: 'ok', overall: 80, reference_tool: 'soffice', reference_renderer: 'soffice' }], artifacts: [],
};

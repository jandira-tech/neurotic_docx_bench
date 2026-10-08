// SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
// SPDX-License-Identifier: AGPL-3.0-only
import type { Batch, Cohort, Live, Result, Run } from './schema';
import { canonical, HttpError } from './policy';

export interface Query { run_id?: string; batch_id?: string; before?: number; cursor?: { completed_at: string; id: string }; q?: string; limit: number }
export interface Store {
  health(): Promise<void>;
  run(id?: string): Promise<Run | null>;
  saveRun(run: Run): Promise<boolean>;
  live(): Promise<Live | null>;
  saveLive(live: Live): Promise<void>;
  results(query: Query): Promise<Result[]>;
  saveResult(result: Result): Promise<boolean>;
  batches(runId?: string): Promise<Batch[]>;
  saveBatch(batch: Batch): Promise<boolean>;
  summary(runId: string): Promise<Cohort[]>;
}

interface Payload { payload: string }
const decode = <T>(row: Payload | null): T | null => row ? JSON.parse(row.payload) as T : null;

export class D1Store implements Store {
  constructor(private db: D1Database) {}
  async health() { await this.db.prepare('SELECT 1').first(); }
  async run(id?: string): Promise<Run | null> {
    const row = id ? await this.db.prepare('SELECT payload FROM bench_runs WHERE id = ?').bind(id).first<Payload>() : await this.db.prepare('SELECT payload FROM bench_runs ORDER BY started_at DESC, id DESC LIMIT 1').first<Payload>();
    return decode<Run>(row);
  }
  async saveRun(run: Run): Promise<boolean> {
    const existing = await this.run(run.id);
    if (existing) return this.same(existing, run);
    await this.db.prepare('INSERT INTO bench_runs (id, started_at, payload) VALUES (?, ?, ?)').bind(run.id, run.started_at, canonical(run)).run();
    return true;
  }
  async live(): Promise<Live | null> { return decode<Live>(await this.db.prepare('SELECT payload FROM bench_live WHERE singleton = 1').first<Payload>()); }
  async saveLive(live: Live): Promise<void> {
    await this.db.prepare(`INSERT INTO bench_live (singleton, run_id, sequence, updated_at, payload) VALUES (1, ?, ?, ?, ?)
      ON CONFLICT(singleton) DO UPDATE SET run_id = excluded.run_id, sequence = excluded.sequence, updated_at = excluded.updated_at, payload = excluded.payload
      WHERE excluded.updated_at > bench_live.updated_at AND (excluded.run_id != bench_live.run_id OR excluded.sequence >= bench_live.sequence)`)
      .bind(live.run_id, live.sequence, live.updated_at, canonical(live)).run();
  }
  async results(query: Query): Promise<Result[]> {
    const clauses: string[] = [];
    const values: (string | number)[] = [];
    if (query.run_id) { clauses.push('run_id = ?'); values.push(query.run_id); }
    if (query.batch_id) { clauses.push('batch_id = ?'); values.push(query.batch_id); }
    if (query.before !== undefined) { clauses.push('sequence < ?'); values.push(query.before); }
    if (query.cursor) { clauses.push('(completed_at < ? OR (completed_at = ? AND id < ?))'); values.push(query.cursor.completed_at, query.cursor.completed_at, query.cursor.id); }
    // D1 limits LIKE patterns to 50 bytes; corpus SHA identifiers have 64 characters.
    if (query.q) { clauses.push("(instr(lower(json_extract(payload, '$.source.id')), ?) > 0 OR instr(lower(id), ?) > 0 OR instr(lower(json_extract(payload, '$.source.metadata')), ?) > 0)"); const search = query.q.toLowerCase(); values.push(search, search, search); }
    const rows = await this.db.prepare(`SELECT payload FROM bench_results ${clauses.length ? `WHERE ${clauses.join(' AND ')}` : ''} ORDER BY completed_at DESC, id DESC LIMIT ?`).bind(...values, query.limit).all<Payload>();
    return rows.results.map((row) => decode<Result>(row)!);
  }
  async saveResult(result: Result): Promise<boolean> {
    const row = await this.db.prepare('SELECT payload FROM bench_results WHERE id = ? OR (run_id = ? AND sequence = ?)').bind(result.id, result.run_id, result.sequence).first<Payload>();
    if (row) return this.same(decode<Result>(row), result);
    const statements = [this.db.prepare('INSERT INTO bench_results (id, run_id, sequence, batch_id, completed_at, payload) VALUES (?, ?, ?, ?, ?, ?)').bind(result.id, result.run_id, result.sequence, result.batch_id, result.completed_at, canonical(result))];
    for (const score of result.scores) statements.push(this.db.prepare('INSERT INTO bench_scores (result_id, run_id, tool, benchmark, reference_tool, reference_renderer, status, overall) VALUES (?, ?, ?, ?, ?, ?, ?, ?)').bind(result.id, result.run_id, score.tool, score.benchmark, score.reference_tool, score.reference_renderer, score.status, score.overall));
    await this.db.batch(statements);
    return true;
  }
  async batches(runId?: string): Promise<Batch[]> {
    const query = runId ? this.db.prepare('SELECT payload FROM bench_batches WHERE run_id = ? ORDER BY last_sequence DESC LIMIT 100').bind(runId) : this.db.prepare('SELECT payload FROM bench_batches ORDER BY completed_at DESC LIMIT 100');
    return (await query.all<Payload>()).results.map((row) => decode<Batch>(row)!);
  }
  async saveBatch(batch: Batch): Promise<boolean> {
    const row = await this.db.prepare('SELECT payload FROM bench_batches WHERE id = ? OR (run_id = ? AND last_sequence = ?)').bind(batch.id, batch.run_id, batch.last_sequence).first<Payload>();
    if (row) return this.same(decode<Batch>(row), batch);
    await this.db.prepare('INSERT INTO bench_batches (id, run_id, last_sequence, completed_at, payload) VALUES (?, ?, ?, ?, ?)').bind(batch.id, batch.run_id, batch.last_sequence, batch.completed_at, canonical(batch)).run();
    return true;
  }
  async summary(runId: string): Promise<Cohort[]> {
    const rows = await this.db.prepare(`SELECT tool, benchmark, reference_tool, NULLIF(reference_renderer, '') AS reference_renderer,
      count, broken, score_sum / count AS mean FROM bench_cohorts
      WHERE run_id = ? ORDER BY benchmark, tool`).bind(runId).all<Cohort>();
    return rows.results;
  }
  private same(existing: unknown, incoming: unknown): false {
    if (canonical(existing) !== canonical(incoming)) throw new HttpError(409, 'Immutable record already exists with different content');
    return false;
  }
}

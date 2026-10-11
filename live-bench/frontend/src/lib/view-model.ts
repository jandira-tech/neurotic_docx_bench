// SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
// SPDX-License-Identifier: AGPL-3.0-only
import type { Result, Score, Snapshot } from './schema';

const names: Record<string, string> = { jubarte: 'Jubarte', 'jubarte-rust': 'Jubarte', docxodus: 'Docxodus', 'superdoc-redlines': 'SuperDoc Redlines', soffice: 'LibreOffice', docxide: 'docxide' };
export const toolName = (tool: string | null) => tool ? names[tool] ?? tool : 'Unavailable';
export const operationName = (operation: string) => operation.replaceAll('_', ' ');
export const scoreText = (score: Score) => score.status === 'broken' ? 'BROKEN · 0' : score.status === 'ok' ? score.overall!.toFixed(2) : score.status.toUpperCase();
export const artifactUrl = (key: string, prefix = '') => `${prefix}/artifacts/${key.split('/').map(encodeURIComponent).join('/')}`;

export function pdfGeometry(width: number, height: number, available: number, density: number) {
  if (![width, height, available, density].every(Number.isFinite) || width <= 0 || height <= 0) throw new Error('Invalid PDF geometry');
  const cssScale = Math.max(1, available) / width;
  const scale = Math.min(cssScale * Math.max(1, Math.min(2, density)), Math.sqrt(2_000_000 / (width * height)));
  return { scale, width: width * cssScale, height: height * cssScale };
}

export function connection(snapshot: Snapshot | null, now: number, failed: boolean): { label: string; state: string; age: number | null } {
  if (failed) return { label: 'Connection interrupted', state: 'offline', age: null };
  if (!snapshot?.live) return { label: 'Waiting for worker', state: 'waiting', age: null };
  const age = Math.max(0, Math.floor((now - Date.parse(snapshot.live.updated_at)) / 1000));
  return { label: age <= 45 ? 'Worker live' : 'Worker heartbeat stale', state: age <= 45 ? 'live' : 'stale', age };
}

export function pdfPair(result: Result | undefined, benchmark: 'convert' | 'redline', tool: string) {
  const score = result?.scores.find((item) => item.tool === tool && item.benchmark === benchmark);
  const operation = benchmark === 'convert' ? 'convert' : 'redline_render';
  const stage = (vendor: string) => result?.stages.find((item) => (item.target_tool ?? item.tool) === vendor && item.operation === operation && item.status === 'ok' && item.artifact);
  return { score, candidate: stage(tool)?.artifact, reference: score?.reference_tool ? stage(score.reference_tool)?.artifact : undefined };
}

export const delayedResults = (results: Result[], now: number, delay = 10000) => results.filter((result) => Date.parse(result.completed_at) <= now - delay);

export function metricLines(score: Score | undefined): [string, string][] {
  if (!score) return [];
  return Object.entries({ ...score.metrics, ...score.functional }).map(([key, value]) => [key.replaceAll('_', ' '), typeof value === 'number' ? Number.isInteger(value) ? String(value) : value.toFixed(4) : typeof value === 'object' ? JSON.stringify(value) : String(value)]);
}

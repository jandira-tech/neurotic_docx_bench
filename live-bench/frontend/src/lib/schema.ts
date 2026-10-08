// SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
// SPDX-License-Identifier: AGPL-3.0-only
import { z } from 'zod';

export const MAX_FILE_BYTES = 20_000_000;

export const identifier = z.string().min(1).max(160).regex(/^[a-zA-Z0-9][a-zA-Z0-9._-]*$/);
export const sha256 = z.string().regex(/^[a-f0-9]{64}$/);
const date = z.iso.datetime({ offset: true }).transform((value) => new Date(value).toISOString());
const integer = z.number().int().nonnegative().max(Number.MAX_SAFE_INTEGER);
export const artifactKey = z.string().max(512).regex(/^[a-zA-Z0-9][a-zA-Z0-9._-]*\/(0|[1-9][0-9]*)\/[a-zA-Z0-9][a-zA-Z0-9._-]*$/)
  .refine((value) => !value.split('/').some((part) => part === '.' || part === '..'), 'Unsafe artifact key');
export const mediaType = z.enum(['application/pdf', 'application/json', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'image/png', 'text/plain']);
const jsonObject = z.record(z.string().max(160), z.json());
export const runSchema = z.strictObject({
  id: identifier, started_at: date, versions: jsonObject,
  config: jsonObject.refine((value) => value.batch_size === undefined || (Number.isInteger(value.batch_size) && Number(value.batch_size) >= 1 && Number(value.batch_size) <= 100), 'batch_size must be 1..100'),
});
export const liveSchema = z.strictObject({
  run_id: identifier, sequence: integer, batch_id: identifier,
  fixture_id: z.string().min(1).max(512), phase: z.string().min(1).max(120),
  updated_at: date, queue_depth: integer, completed: integer,
});
export const sourceSchema = z.strictObject({
  id: z.string().min(1).max(512), url: z.url().max(2048).refine((value) => ['http:', 'https:'].includes(new URL(value).protocol) || value === 'generated://starting_point.docx'), sha256: sha256.nullable(),
  language: z.string().max(160).nullable().optional(), type: z.string().max(512).nullable().optional(),
  review_id: identifier.nullable().optional(), metadata: jsonObject.optional(), security: jsonObject.optional(),
});
export const artifactSchema = z.strictObject({ key: artifactKey, content_type: mediaType, sha256, size: integer.max(MAX_FILE_BYTES), metadata: jsonObject.optional() });
export const stageSchema = z.strictObject({
  tool: identifier, operation: z.enum(['download', 'security_preflight', 'functional', 'convert', 'compare', 'redline_render', 'score_convert', 'score_redline', 'native_redline_render']),
  status: z.enum(['ok', 'broken', 'error', 'unavailable']), duration_ms: z.number().nonnegative(),
  error: z.string().max(2000).optional(), artifact: artifactKey.optional(),
  target_tool: identifier.optional(), metadata: jsonObject.optional(),
});
export const scoreSchema = z.strictObject({
  tool: identifier, benchmark: z.enum(['convert', 'redline']), status: z.enum(['ok', 'broken', 'error', 'unavailable', 'reference']),
  // Weighted floating-point aggregates can exceed a bound by a few machine epsilons.
  // Preserve raw metrics in their evidence artifact; normalize only this display aggregate.
  overall: z.number().min(-1e-8).max(100 + 1e-8).transform((value) => Math.max(0, Math.min(100, value))).nullable(), reference_tool: identifier.nullable(), reference_renderer: identifier.nullable(),
  metrics: jsonObject.optional(), functional: jsonObject.optional(),
}).superRefine((value, ctx) => {
  if (value.status === 'ok' && value.overall === null) ctx.addIssue({ code: 'custom', message: 'Successful score requires overall' });
  if (value.status === 'broken' && value.overall !== 0) ctx.addIssue({ code: 'custom', message: 'Broken candidate score must be zero' });
  if (['unavailable', 'reference', 'error'].includes(value.status) && value.overall !== null) ctx.addIssue({ code: 'custom', message: 'Unscored result must have null overall' });
  if (['ok', 'broken'].includes(value.status) && (!value.reference_tool || !value.reference_renderer)) ctx.addIssue({ code: 'custom', message: 'Measured candidate requires reference identity' });
});
export const resultSchema = z.strictObject({
  id: identifier, run_id: identifier, sequence: integer.min(1), batch_id: identifier,
  source: sourceSchema, previous: sourceSchema.nullable(), completed_at: date,
  stages: z.array(stageSchema).max(100), scores: z.array(scoreSchema).max(30), artifacts: z.array(artifactSchema).max(100),
}).superRefine((value, ctx) => {
  const keys = value.artifacts.map((artifact) => artifact.key);
  if (new Set(keys).size !== keys.length || keys.some((key) => !key.startsWith(`${value.run_id}/${value.sequence}/`))) ctx.addIssue({ code: 'custom', message: 'Artifact keys must be unique and belong to result' });
  if (value.stages.some((stage) => stage.artifact && !keys.includes(stage.artifact))) ctx.addIssue({ code: 'custom', message: 'Stage artifact must be declared' });
  const scores = value.scores.map((score) => `${score.tool}/${score.benchmark}`);
  if (new Set(scores).size !== scores.length) ctx.addIssue({ code: 'custom', message: 'Duplicate score' });
});
export const batchSchema = z.strictObject({
  id: identifier, run_id: identifier, first_sequence: integer.min(1), last_sequence: integer.min(1), count: integer.min(1).max(100),
  completed_at: date, manifest_key: artifactKey,
}).refine((value) => value.last_sequence - value.first_sequence + 1 === value.count && value.manifest_key.startsWith(`${value.run_id}/`), 'Invalid batch range or manifest');

export type Run = z.infer<typeof runSchema>;
export type Live = z.infer<typeof liveSchema>;
export type Result = z.infer<typeof resultSchema>;
export type Score = z.infer<typeof scoreSchema>;
export type Batch = z.infer<typeof batchSchema>;
export type Artifact = z.infer<typeof artifactSchema>;

export interface Cohort { tool: string; benchmark: string; reference_tool: string; reference_renderer: string; count: number; broken: number; mean: number }
export interface Snapshot { live: Live | null; run: Run | null; results: Result[]; summary: Cohort[] }

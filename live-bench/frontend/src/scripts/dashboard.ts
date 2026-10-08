// SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
// SPDX-License-Identifier: AGPL-3.0-only
import type { Result, Snapshot } from '../lib/schema';
import { mountPdf } from './pdf-preview';
import { artifactUrl, connection, delayedResults, metricLines, operationName, pdfPair, scoreText, toolName } from '../lib/view-model';

const get = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;
const put = (id: string, text: string) => { get(id).textContent = text; };
const node = <K extends keyof HTMLElementTagNameMap>(tag: K, text?: string, className?: string) => {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
};
const prefix = document.body.dataset.prefix ?? '';
const evidenceUrl = (key: string) => artifactUrl(key, prefix);
const humanTime = (date: string) => new Date(date).toLocaleString([], { dateStyle: 'short', timeStyle: 'medium' });
let snapshot: Snapshot | null = null;
let failed = false;
let selectedId: string | null = null;
let historySelection: Result | undefined;
let benchmark: 'convert' | 'redline' = 'convert';
let tool = 'jubarte';
let paused = matchMedia('(prefers-reduced-motion: reduce)').matches;
let historyRows: Result[] = [];
let historyCursor: string | null = null;
let historyQuery = '';
let historyRequest = 0;
let lastDelayedId: string | undefined;
const previews = new Map<string, () => void>();

const visibleResults = () => delayedResults(snapshot?.results ?? [], Date.now());
const activeResult = () => historySelection ?? visibleResults().find((result) => result.id === selectedId) ?? visibleResults()[0];

function updateConnection() {
  const state = connection(snapshot, Date.now(), failed);
  get('connection').className = `connection ${state.state}`;
  get('connection').querySelector('span')!.textContent = state.label;
  put('heartbeat', state.age === null ? '—' : `${state.age}s ago`);
}

function renderLive() {
  updateConnection();
  const live = snapshot?.live;
  put('current-fixture', live?.fixture_id ?? 'Waiting for first fixture');
  put('phase', live ? `#${live.sequence} · ${live.phase.replaceAll('_', ' ')}` : 'No heartbeat received');
  put('completed', live ? String(live.completed) : '—');
  put('queue', live ? String(live.queue_depth) : '—');
  put('run-id', snapshot?.run?.id ?? 'No active run');
  put('cohort-context', snapshot?.run ? `Run ${snapshot.run.id}` : 'Awaiting evidence');
  put('versions', snapshot?.run ? JSON.stringify({ versions: snapshot.run.versions, config: snapshot.run.config }, null, 2) : 'No run metadata received.');
  get('cohorts').replaceChildren(...(snapshot?.summary.length ? snapshot.summary.map((cohort) => {
    const card = node('article', undefined, `cohort ${cohort.tool.startsWith('jubarte') ? 'jubarte' : ''}`);
    const heading = node('div', undefined, 'cohort-title');
    heading.append(node('b', toolName(cohort.tool)), node('span', cohort.benchmark));
    card.append(heading, node('strong', cohort.mean.toFixed(2)), node('p', `${cohort.count} measured · ${cohort.broken} broken`, `mono ${cohort.broken ? 'broken' : 'muted'}`), node('p', `Reference: ${toolName(cohort.reference_tool)} / ${cohort.reference_renderer}`, 'mono muted'));
    return card;
  }) : [node('p', 'Waiting for measured scores from this run.', 'empty')]));
  renderEvidence();
}

function syncDelayed() {
  const newest = visibleResults()[0]?.id;
  if (newest !== lastDelayedId) {
    lastDelayedId = newest;
    if (!paused) { selectedId = newest ?? null; historySelection = undefined; }
    renderEvidence();
  }
}

function renderEvidence() {
  const result = activeResult();
  // Retain the complete occurrence when paused, including before the first feed arrives.
  if (paused && result && !historySelection) historySelection = result;
  const tools = result ? [...new Set(result.scores.filter((score) => score.benchmark === benchmark).map((score) => score.tool))] : ['jubarte'];
  if (!tools.includes(tool)) tool = tools.find((vendor) => vendor.startsWith('jubarte')) ?? tools[0] ?? 'jubarte';
  get<HTMLSelectElement>('tool').replaceChildren(...tools.map((vendor) => { const option = node('option', toolName(vendor)); option.value = vendor; return option; }));
  get<HTMLSelectElement>('tool').value = tool;
  document.querySelectorAll<HTMLButtonElement>('[data-benchmark]').forEach((tab) => { const active = tab.dataset.benchmark === benchmark; tab.classList.toggle('active', active); tab.setAttribute('aria-pressed', String(active)); });
  put('display-fixture', result ? `#${result.sequence} · ${result.source.id}` : 'Waiting for completed results');
  const source = get('fixture-source'); source.replaceChildren();
  if (result) {
    if (result.source.url.startsWith('http')) { const link = node('a', result.source.url); link.href = result.source.url; link.target = '_blank'; link.rel = 'noopener'; source.append(link); }
    else source.append(node('span', result.source.url));
    source.append(node('span', ` · SHA256 ${result.source.sha256 ?? 'download failed'}`));
  } else source.textContent = 'Source URL and checksum will accompany every result.';
  put('previous-source', result?.previous ? `Previous: ${result.previous.id} · SHA256 ${result.previous.sha256 ?? 'download failed'}` : '');
  const pair = pdfPair(result, benchmark, tool);
  put('candidate-title', toolName(tool));
  put('reference-title', pair.score ? `${toolName(pair.score.reference_tool)} · ${pair.score.reference_renderer ?? 'unavailable'}` : 'Reference');
  put('result-score', pair.score ? scoreText(pair.score) : '—');
  get('result-score').className = pair.score?.status === 'broken' ? 'broken' : '';
  put('reference-note', pair.score ? `${pair.score.benchmark} · ${pair.score.status}` : 'No measured score');
  renderPdf('candidate', pair.candidate, `${toolName(tool)} candidate PDF`, pair.score?.status === 'broken' ? 'BROKEN: this candidate failed to produce a usable PDF.' : 'Candidate PDF unavailable for this measurement.');
  renderPdf('reference', pair.reference, 'Reference PDF', 'Reference PDF unavailable for this measurement.');
  const image = result?.artifacts.find((artifact) => artifact.key.endsWith(`/score-${benchmark}-${tool}.png`));
  get('score-visualization').hidden = !image;
  if (image) get<HTMLImageElement>('score-image').src = evidenceUrl(image.key);
  const metrics = metricLines(pair.score);
  get('metrics').replaceChildren(...(metrics.length ? metrics.flatMap(([key, value]) => [node('dt', key), node('dd', value)]) : [node('p', result ? 'No metrics were produced for this score.' : 'Select a completed measurement to inspect its metrics.', 'empty')]));
  get('stages').replaceChildren(...(result ? result.stages.map((stage) => {
    const li = node('li'); const row = node('div', undefined, 'stage-row');
    const target = stage.target_tool ? ` → ${toolName(stage.target_tool)}` : '';
    row.append(node('span', `${toolName(stage.tool)}${target} / ${operationName(stage.operation)}`), node('span', `${stage.status.toUpperCase()} · ${stage.duration_ms.toFixed(0)}ms`, `status-${stage.status}`));
    li.append(row);
    if (stage.error) li.append(node('p', stage.error, 'stage-error'));
    if (stage.artifact) { const link = node('a', 'Inspect artifact ↗'); link.href = evidenceUrl(stage.artifact); link.target = '_blank'; link.rel = 'noopener'; li.append(link); }
    return li;
  }) : [node('li', 'No completed stages yet.', 'empty')]));
  put('review-metadata', result ? JSON.stringify(result, null, 2) : 'No completed review selected.');
  get('artifact-links').replaceChildren(...(result?.artifacts.map((artifact) => { const link = node('a', `${artifact.key.split('/').at(-1)} · ${artifact.size} bytes ↗`, 'artifact-link'); link.href = evidenceUrl(artifact.key); link.target = '_blank'; link.rel = 'noopener'; return link; }) ?? []));
  get<HTMLButtonElement>('previous-result').disabled = !visibleResults().length;
  get<HTMLButtonElement>('next-result').disabled = !visibleResults().length;
}

function renderPdf(side: string, key: string | undefined, title: string, empty: string) {
  const slot = get(`${side}-pdf`); const link = get<HTMLAnchorElement>(`${side}-open`);
  link.hidden = !key; if (key) link.href = evidenceUrl(key);
  if (slot.dataset.key === (key ?? 'empty') && (key || slot.textContent === empty)) return;
  previews.get(side)?.(); previews.delete(side);
  slot.dataset.key = key ?? 'empty';
  if (key) previews.set(side, mountPdf(slot, evidenceUrl(key), title, prefix, () => { paused = true; updateRotation(); }));
  else slot.replaceChildren(node('p', empty));
}

function selectResult(result: Result) {
  selectedId = result.id; historySelection = result; paused = true; updateRotation(); renderResults(); renderEvidence(); get('comparison').scrollIntoView({ behavior: 'instant' });
}

function renderResults() {
  if (!historyRows.length) { const row = node('tr'); const cell = node('td', historyQuery ? 'No reviews match this search.' : 'No completed reviews yet.', 'empty'); cell.colSpan = 5; row.append(cell); get('results').replaceChildren(row); return; }
  get('results').replaceChildren(...historyRows.map((result) => {
    const tr = node('tr', undefined, activeResult()?.id === result.id ? 'selected' : '');
    const fixture = node('td'); const button = node('button', result.source.id); button.addEventListener('click', () => selectResult(result)); fixture.append(button);
    const identity = node('td', result.id); identity.className = 'review-id'; identity.title = `Run ${result.run_id} / sequence ${result.sequence}`;
    tr.append(identity, fixture, node('td', humanTime(result.completed_at)));
    for (const cohort of ['convert', 'redline']) {
      const cell = node('td');
      for (const score of result.scores.filter((item) => item.benchmark === cohort)) cell.append(node('span', `${toolName(score.tool)} ${scoreText(score)}`, `table-score status-${score.status}`));
      if (!cell.childNodes.length) cell.textContent = 'No measurements';
      tr.append(cell);
    }
    return tr;
  }));
}

async function loadHistory(reset: boolean, quiet = false) {
  const version = ++historyRequest;
  const query = new URLSearchParams({ limit: '30' });
  if (historyQuery) query.set('q', historyQuery);
  if (!reset && historyCursor) query.set('cursor', historyCursor);
  if (!quiet) put('history-status', 'Loading reviewed fixtures…');
  get<HTMLButtonElement>('history-more').disabled = true;
  try {
    const response = await fetch(`${prefix}/api/results?${query}`, { cache: 'no-store' });
    if (!response.ok) throw new Error('History request failed');
    const data: { results: Result[]; next_cursor: string | null } = await response.json();
    if (version !== historyRequest) return;
    historyRows = reset ? data.results : [...historyRows, ...data.results];
    historyCursor = data.next_cursor;
    renderResults();
    put('history-status', `${historyRows.length} reviews shown${historyCursor ? ' · more available' : ' · end of history'}${historyQuery ? ` · search: ${historyQuery}` : ''}`);
    get('history-more').hidden = !historyCursor;
  } catch { if (version === historyRequest) put('history-status', 'History unavailable. Retry search or Latest reviews.'); }
  finally { if (version === historyRequest) get<HTMLButtonElement>('history-more').disabled = false; }
}

function rotate(direction = 1) {
  const results = visibleResults(); if (!results.length) return;
  const index = Math.max(0, results.findIndex((result) => result.id === activeResult()?.id));
  selectedId = results[(index + direction + results.length) % results.length].id;
  historySelection = undefined; renderResults(); renderEvidence();
}

function rotateMeasurement() {
  const result = activeResult(); if (!result?.scores.length) return;
  const index = result.scores.findIndex((score) => score.tool === tool && score.benchmark === benchmark);
  const next = result.scores[(index + 1) % result.scores.length]; tool = next.tool; benchmark = next.benchmark;
  if (index === result.scores.length - 1) rotate();
  renderEvidence();
}

function updateRotation() {
  put('rotation', paused ? 'Resume live view' : 'Pause live view');
  get('rotation').setAttribute('aria-pressed', String(paused));
  put('rotation-status', paused ? 'Live view paused · feed stays current' : 'Following completed fixtures · 10s delay');
}

async function refresh() {
  try {
    const response = await fetch(`${prefix}/api/live`, { cache: 'no-store' });
    if (!response.ok) throw new Error('Feed unavailable');
    const next: Snapshot = await response.json();
    const newResult = next.results[0]?.id !== snapshot?.results[0]?.id;
    const changed = JSON.stringify(next) !== JSON.stringify(snapshot);
    snapshot = next; failed = false;
    if (changed) renderLive(); else updateConnection();
    syncDelayed();
    if (newResult && !historyQuery && historyRows.length <= 30) void loadHistory(true, true);
    put('last-refresh', `Feed refreshed ${new Date().toLocaleTimeString()}`);
  } catch { failed = true; updateConnection(); put('last-refresh', 'Feed unavailable · retrying every 3s'); }
}

get('rotation').addEventListener('click', () => { paused = !paused; if (!paused) { historySelection = undefined; selectedId = visibleResults()[0]?.id ?? null; } updateRotation(); renderEvidence(); });
get('previous-result').addEventListener('click', () => { paused = true; updateRotation(); rotate(-1); });
get('next-result').addEventListener('click', () => { paused = true; updateRotation(); rotate(); });
get<HTMLSelectElement>('tool').addEventListener('change', (event) => { tool = (event.target as HTMLSelectElement).value; paused = true; updateRotation(); renderEvidence(); });
document.querySelectorAll<HTMLButtonElement>('[data-benchmark]').forEach((button) => button.addEventListener('click', () => { benchmark = button.dataset.benchmark as 'convert' | 'redline'; paused = true; updateRotation(); renderEvidence(); }));
get<HTMLFormElement>('history-search').addEventListener('submit', (event) => { event.preventDefault(); historyQuery = get<HTMLInputElement>('history-query').value.trim(); historyCursor = null; void loadHistory(true); });
get('history-reset').addEventListener('click', () => { historyQuery = ''; get<HTMLInputElement>('history-query').value = ''; historyCursor = null; void loadHistory(true); });
get('history-more').addEventListener('click', () => void loadHistory(false));
updateRotation();
void refresh(); void loadHistory(true);
async function poll() { await refresh(); window.setTimeout(() => void poll(), 3000); }
window.setTimeout(() => void poll(), 3000);
window.setInterval(() => { if (!paused && !document.hidden && !failed) rotateMeasurement(); }, 6000);
window.setInterval(() => { updateConnection(); syncDelayed(); }, 1000);

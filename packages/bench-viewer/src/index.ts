export type {
  Headline,
  HomeBar,
  HomeGroup,
  MethodPoint,
  Row,
  Scores,
  StateCell,
  StateRow,
  Table,
} from "./types.ts";

import type { Headline, HomeGroup, MethodPoint, Row, Scores, StateCell, Table } from "./types.ts";

export function parseScores(json: unknown): Scores {
  throw new Error("not implemented");
}

export function esc(s: string): string {
  throw new Error("not implemented");
}

export function renderRow(r: Row): string {
  throw new Error("not implemented");
}

export function renderTable(t: Table): string {
  throw new Error("not implemented");
}

export function renderHeadlines(h: Headline[]): string {
  throw new Error("not implemented");
}

export function renderStates(s: StateCell[], label?: (name: string) => string): string {
  throw new Error("not implemented");
}

export function renderBars(groups: HomeGroup[]): string {
  throw new Error("not implemented");
}

export function renderMethod(m: MethodPoint[]): string {
  throw new Error("not implemented");
}

export function renderBadge(s: Scores, tag?: string): string {
  throw new Error("not implemented");
}

export function renderLegend(): string {
  throw new Error("not implemented");
}

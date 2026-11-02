export interface Row {
  rank: string;
  tool: string;
  pin: string;
  median: number;
  mean: number;
  docs: number;
  failed: number;
  note: string;
  ours?: boolean;
}

export interface Table {
  id: string;
  title: string;
  meta: string;
  desc: string;
  rows: Row[];
}

export interface Headline {
  label: string;
  value: string;
  vs: string;
  sub: string;
}

export interface StateRow {
  tool: string;
  median: number;
  ours?: boolean;
}

export interface StateCell {
  name: string;
  n: string;
  rows: StateRow[];
  table?: string | null;
}

export interface RenderStatesOptions {
  heading?: string;
  label?: (name: string) => string;
  table?: string;
}

export interface HomeBar {
  name: string;
  v: number;
  ours?: boolean;
}

export interface HomeGroup {
  title: string;
  meta: string;
  rows: HomeBar[];
  note?: string | null;
}

export interface MethodPoint {
  t: string;
  d: string;
}

export interface Scores {
  version: string;
  generated: string;
  repo: string;
  viewer: string;
  provenance: Record<string, string[]>;
  tables: Table[];
  headlines: Headline[];
  states: StateCell[];
  home_groups: HomeGroup[];
  method: MethodPoint[];
}

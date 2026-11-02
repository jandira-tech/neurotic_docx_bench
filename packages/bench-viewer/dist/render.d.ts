import type { Headline, HomeGroup, MethodPoint, RenderStatesOptions, Row, Scores, StateCell, Table } from "./types.ts";
/** The page's name for a corpus state. */
export declare const stateLabel: (name: string) => string;
/** One row of a leaderboard table. */
export declare function renderRow(r: Row): string;
/** One leaderboard table, with its heading and its note. */
export declare function renderTable(t: Table): string;
/** The headline cells above the tables. */
export declare function renderHeadlines(h: Headline[]): string;
/** The conversion sample, split by corpus state. */
export declare function renderStates(s: StateCell[], opts?: RenderStatesOptions): string;
/** The bar groups of the home page: one group per sample, one bar per tool. */
export declare function renderBars(groups: HomeGroup[]): string;
/** The method: what the numbers mean, one card each. */
export declare function renderMethod(m: MethodPoint[]): string;
/** The badge: which bench version, generated when. */
export declare function renderBadge(s: Scores, tag?: string): string;
/** What the two marks in the tables mean. */
export declare function renderLegend(): string;

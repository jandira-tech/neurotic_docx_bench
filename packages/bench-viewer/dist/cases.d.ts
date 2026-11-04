/**
 * The case browsers: the conversion browser and the redline browser.
 *
 * The data is the release's, not a copy of it. `cases/index.json` holds the
 * shard directory, the engine list and the public asset base; one shard per
 * group is fetched when the group is opened, so a page opens on one group
 * instead of the whole corpus.
 *
 * Two layers live here. The **render layer** is pure: a function from data to
 * an HTML string, with every data string through `esc()` (the case id, the
 * group name, the version label, the error message, the asset path — data is
 * not markup). The **wiring** (`mountCasesPage`) fetches, keeps the state and
 * puts the strings where they belong. The tests drive the first layer without
 * a browser.
 *
 * The contract is `bench_ops.models` (CasesIndex, CaseShard, Case): the
 * release writes it, this module reads it.
 */
/** The two kinds of case group the release holds. */
export type Kind = "conversion" | "redline";
/** The metric names a case's scores may carry. */
export type MetricName = "pixel" | "jaccard" | "ssim" | "text_boundary";
/** One engine lane: the key the data uses, the label the page shows. */
export interface Engine {
    key: string;
    label: string;
}
/** One group in the index: where its shard is and how many cases it holds. */
export interface ShardRef {
    kind: Kind;
    group: string;
    count: number;
    path: string;
}
/** `cases/index.json`: the shard directory, the engine list, the asset base. */
export interface CasesIndex {
    version: string;
    generated: string;
    repo: string;
    assets_base: string;
    engines: Engine[];
    groups: ShardRef[];
    /**
     * The public base the case's `files` paths resolve against (the record on
     * Hugging Face). Absent when the release publishes no files.
     */
    files_base?: string;
}
/** The per-lane page diagnostics the release carries. */
export interface MetricDiagnostics {
    ref_pages: number;
    pages: number;
    scored_pages: number;
    max_break_drift: number;
}
/** One case row: the pages, the scores, the versions, the lanes left out. */
export interface Case {
    kind: Kind;
    group: string;
    case: string;
    pages: Record<string, (string | null)[]>;
    page_counts: Record<string, number>;
    scores: Record<string, Partial<Record<MetricName, number | null>>>;
    times: Record<string, number>;
    versions: Record<string, string>;
    dropped: string[];
    reference_app: string;
    pdfs?: Record<string, string>;
    errors?: Record<string, string>;
    metric_diagnostics?: Record<string, MetricDiagnostics>;
    shown?: number[] | null;
    stem?: string | null;
    lang?: string | null;
    type?: string | null;
    set?: string | null;
    sets?: string | null;
    state?: string | null;
    pair?: string | null;
    not_applicable?: string[];
    unavailable?: string[];
    /**
     * One score per shown page, per lane (null = that page could not be
     * scored). Never longer than the lane's shown pages; absent when the
     * release publishes no per-page scores.
     */
    page_scores?: Record<string, (number | null)[]>;
    /**
     * The case's files, per lane, relative to the index's `files_base` (the
     * `~/` sentinel, as in the published data).
     */
    files?: Record<string, string>;
}
/** One group's shard: `cases/<kind>/<group>.json`. */
export interface CaseShard {
    kind: Kind;
    group: string;
    cases: Case[];
}
/** The index: the shard directory, the engine list and the asset base. */
export declare function parseCasesIndex(value: unknown): CasesIndex;
/** One shard: the group's cases, in the order the release wrote them. */
export declare function parseCaseShard(value: unknown): CaseShard;
/** One case row. */
export declare function parseCase(value: unknown, path: string, kind?: Kind, group?: string): Case;
/** What a lane holds for one case. */
export type LaneState = "measured" | "no-pages" | "failed" | "unavailable" | "not-applicable" | "dropped";
/** The label each lane state wears on the page. */
export declare const LANE_LABEL: Record<LaneState, string>;
/** What a lane holds for one case. */
export declare function laneState(c: Case, key: string): LaneState;
/** The lanes of one case, in the order the page draws them (Word first). */
export declare function lanesForCase(c: Case, engines: Engine[]): {
    engine: Engine;
    state: LaneState;
}[];
/**
 * The lanes a group's cases mention: the page's kind's lanes, as far as this
 * group shows them. The release writes every lane of the page's kind into
 * each of its cases — a lane it did not run for a case is `dropped`, a cohort
 * lane without a published measurement is `unavailable` — while a lane of the
 * *other* kind is mentioned by no case of this one (no pages, no score, not
 * even dropped). So the union of what the cases mention is exactly the set a
 * page of that kind may show, and a conversion page never shows a
 * redline-only lane (jubarte-rust, superdoc, stemma, docxodus-12.6.5,
 * jubarte-093, …) unless it has data in a conversion case.
 *
 * The index's engine list is sorted by key: that is **storage order, not
 * display order** — `orderLanes` decides which lanes a page shows and in
 * which order.
 */
export declare function mentionedLanes(cases: Case[], engines: Engine[]): Engine[];
/**
 * The display order of a group's lanes: Word first, then by the number of
 * cases in the group where the lane has a score (descending), ties by label —
 * compared by code points, so the order never depends on the runtime's
 * collation. Lanes with no data in the group sort last (they have no score);
 * the bar folds them behind "+N more".
 */
export declare function orderLanes(cases: Case[], engines: Engine[]): Engine[];
/**
 * The lanes with data in the group: everything the cases give a lane besides
 * dropping it — pages, a score, a time, an error, `unavailable`,
 * `not applicable` — in at least one case. These stay out of the "+N more"
 * fold; the kind's lanes without data (dropped in every case) are folded.
 */
export declare function lanesWithData(cases: Case[]): Set<string>;
/**
 * The lane the page puts beside Word by default: the first non-reference
 * lane in the display order — the group's own numbers decide, no product
 * preference.
 */
export declare function defaultComparisonLane(lanes: Engine[]): Engine | undefined;
/**
 * The lane the overlay puts over Word by default: the second non-reference
 * lane in the display order, for the same reason.
 */
export declare function defaultOverlayLane(lanes: Engine[]): Engine | undefined;
/**
 * The public URL of one asset. The release stores the path relative to the
 * asset base with a `~/` sentinel; anything that is not an http(s) URL is
 * refused rather than put in an `src`.
 */
export declare function resolveAssetUrl(assetsBase: string, path: string | null | undefined): string;
/** The URL of an asset, or the empty string when it is not safe to use. */
export declare function safeAssetUrl(assetsBase: string, path: string | null | undefined): string;
/**
 * The URL of a case file: the files base + the path without its `~/`
 * prefix. A path that is not relative to the base is refused — a file link
 * stays inside the record it names.
 */
export declare function resolveFileUrl(filesBase: string, path: string | null | undefined): string;
/** The URL of a case file, or the empty string when it is not safe to use. */
export declare function safeFileUrl(filesBase: string, path: string | null | undefined): string;
/**
 * The case's own folder on the files base: the longest folder its lanes'
 * files share (the case's folder, the lanes' files hang under it). The
 * empty string when the case publishes no files or the base is unknown.
 */
export declare function caseFilesUrl(filesBase: string | undefined, c: Case): string;
/**
 * The URL of a shard, resolved against the release the index came from. The
 * shard path is relative to the release root (`cases/<kind>/<group>.json`);
 * the index sits in `cases/`, so the root is its directory's parent.
 */
export declare function shardUrl(indexUrl: string, path: string, base?: string): string;
/** The hash of one case: `#<group>/<case>`. */
export declare function caseHash(group: string, name: string): string;
/**
 * The case a hash names, or null. The group may hold slashes (`v1/clean`), so
 * the known groups are tried first; without them the last slash splits.
 */
export declare function parseCaseHash(hash: string, groups?: string[]): {
    group: string;
    case: string;
} | null;
/** The metrics the score table shows, in the published order. */
export declare const METRICS: MetricName[];
/** The short label each metric wears in a table header. */
export declare const METRIC_LABEL: Record<MetricName, string>;
/** What each metric means; the tooltip on its header cell. */
export declare const METRIC_INFO: Record<MetricName, string>;
/** The metrics a score table shows, time last. */
export type ScoreColumn = MetricName | "time";
/** The label each score column wears in a table header. */
export declare const SCORE_LABEL: Record<ScoreColumn, string>;
/** The palette the lane colours come from, in the published order. */
export declare const LANE_COLORS: string[];
/** The colour of one lane, by its position in the engine list. */
export declare function laneColor(engines: Engine[], key: string): string;
/** A score as the page shows it: one decimal and a percent sign. */
export declare function formatScore(value: number | null | undefined): string;
/**
 * A page score as the page shows it: one decimal, or a dash when the page
 * could not be scored.
 */
export declare function formatPageScore(value: number | null | undefined): string;
/** A duration as the page shows it: seconds with two decimals. */
export declare function formatTime(value: number | null | undefined): string;
/** One lane's column of pages. */
export interface CaseStripOptions {
    /** The case the strip belongs to. */
    case: Case;
    /** The lane the strip shows. */
    engine: Engine;
    /** The public base every `~/` asset path resolves against. */
    assetsBase: string;
    /** How many pages to show (the "more pages" step). */
    limit?: number;
    /** The page numbers the slots stand for (the case's own `shown`). */
    shown?: number[] | null;
    /** The mobile layout: crop the page to its top half. */
    half?: boolean;
}
/**
 * One lane's column of pages: the images, or the label that says why there
 * are none. The pages come from the release; the label comes from the lane's
 * state.
 */
export declare function renderCaseStrip(opts: CaseStripOptions): string;
/** One lane's header: the name, the version, the page count, the scores. */
export interface CaseHeadOptions {
    case: Case;
    engine: Engine;
    assetsBase: string;
    /** The engine list, for the lane's colour. */
    engines?: Engine[];
    /** The compact header the mobile layout wears. */
    compact?: boolean;
    /** The public base the case's files resolve against (Hugging Face). */
    filesBase?: string;
}
/** One lane's header. */
export declare function renderCaseHead(opts: CaseHeadOptions): string;
/** The whole grid: every lane's header, then every lane's column. */
export interface CaseGridOptions {
    case: Case;
    /** The lanes to draw, in order. */
    lanes: {
        engine: Engine;
        state: LaneState;
    }[];
    assetsBase: string;
    /** The engine list, for the lane colours. */
    engines?: Engine[];
    /** How many pages to show. */
    limit?: number;
    /** The compact headers the mobile layout wears. */
    compact?: boolean;
    /** The mobile layout: crop the page to its top half. */
    half?: boolean;
    /** The public base the case's files resolve against (Hugging Face). */
    filesBase?: string;
}
/** The whole grid. */
export declare function renderCaseGrid(opts: CaseGridOptions): string;
/** The overlay: one page of Word with one page of an engine over it. */
export interface OverlayOptions {
    case: Case;
    /** The lane under. */
    under: Engine;
    /** The lane over. */
    over: Engine;
    assetsBase: string;
    /** How many pages to show. */
    limit?: number;
    /** The blend mode ("normal", "difference", "multiply"). */
    blend?: string;
    /** The opacity of the lane over, in percent. */
    alpha?: number;
}
/** The overlay. */
export declare function renderOverlay(opts: OverlayOptions): string;
/**
 * Apply every `data-css` under `root` through the CSSOM. The renderers never
 * write a `style="…"` attribute: a host whose CSP is `style-src 'self'`
 * (benchmarks.law) drops those, and with them the overlay's opacity and blend
 * and the engine colours (#158). CSSOM writes are not governed by style-src.
 */
export declare function applyInlineCss(root: ParentNode | null | undefined): void;
/** The case list in the side panel. */
export interface CaseListOptions {
    cases: Case[];
    /** The selected case: its key (`caseKey`), or its bare id. */
    selected?: string;
    /** The text filter, already applied by the caller. */
    filter?: string;
}
/**
 * A case's identity: its group and its id. One id can sit in several groups
 * (the same document in two corpora), so "all groups" needs both.
 */
export declare function caseKey(c: Pick<Case, "group" | "case">): string;
/** The case list. */
export declare function renderCaseList(opts: CaseListOptions): string;
/** The group picker: one option per group of this kind. */
export declare function renderGroupOptions(groups: ShardRef[], selected?: string): string;
/** The group picker's value for every group of the browser at once. */
export declare const ALL_GROUPS = "*";
/** The engine toggles: one per lane, the ones without data folded away. */
export interface EngineToggleOptions {
    /** Every lane of the release — the lane colours come from its order. */
    engines: Engine[];
    /**
     * The lanes to draw, in display order (`orderLanes` of the group on
     * screen). Defaults to `engines`, storage order and all.
     */
    lanes?: Engine[];
    /** Which lanes are on. */
    on: Record<string, boolean>;
    /** The lanes that have data in the group on screen. */
    active?: Set<string>;
    /** The version each lane wears (the case's own, or the group's). */
    versions?: Record<string, string>;
    /** What each lane holds for the case on screen. */
    states?: Record<string, LaneState>;
}
/** The engine toggles. */
export declare function renderEngineToggles(opts: EngineToggleOptions): string;
/** The score table: one row per case, one column per lane and metric. */
export interface ScoresTableOptions {
    cases: Case[];
    /** Every lane of the release — the lane colours come from its order. */
    engines: Engine[];
    /**
     * The lanes that get columns, in display order (`orderLanes` of the group
     * on screen). Defaults to `engines`.
     */
    lanes?: Engine[];
    /** The selected case's id. */
    selected?: string;
    /** The column the table is sorted by, and the way. */
    sort?: {
        col: number;
        dir: number;
    };
}
/** The score table. */
export declare function renderScoresTable(opts: ScoresTableOptions): string;
/** The legend: what the scores mean, as an accordion of notes. */
export interface CasesLegendOptions {
    kind: Kind;
    /** The number of cases the release holds. */
    count?: number;
}
/** The legend. */
export declare function renderCasesLegend(opts: CasesLegendOptions): string;
/** The page the browsers wear. */
export interface CasesPageOptions {
    /** Which browser this is. */
    kind: Kind;
    /** The index the page fetches, relative to the page. */
    indexUrl: string;
    /** The module the page imports, relative to the page. */
    moduleUrl: string;
    /** The stylesheet the page links, relative to the page. */
    stylesheet?: string;
    /** The page's title. */
    title?: string;
    /** The page's meta description. */
    description?: string;
    /** The link to the conversion browser. */
    conversionHref?: string;
    /** The link to the redline browser. */
    redlinesHref?: string;
    /** The link to the speed page. */
    speedHref?: string;
    /** The link to the leaderboard. */
    indexHref?: string;
}
/** The whole page: the shell the wiring fills in. No data in it. */
export declare function renderCasesPage(opts: CasesPageOptions): string;
/** How the wiring is told which browser it is. */
export interface MountCasesOptions {
    /** Which browser this is. */
    kind: Kind;
    /** The index the page fetches. */
    indexUrl: string;
    /** The other browser's URL, for the mode picker. */
    modeUrl?: string;
    /** The document the page lives in. */
    root?: Document;
    /**
     * The source of the random draw (the random case on open, the random
     * button). `Math.random` by default; a seeded generator makes the page
     * deterministic under test.
     */
    random?: () => number;
    /**
     * Fetch one page image ahead of time (#159). The next case's shown pages go
     * through it after each case renders, so "next" paints from the cache. A
     * detached `Image` by default; tests pass a recorder.
     */
    preload?: (url: string) => void;
}
/** At most this many pages are requested ahead for one next case. */
export declare const PRELOAD_STEP = 12;
/**
 * How many pages the grid shows before "more pages". The release shows up
 * to 12 pages of a case (the producer's own cap), so the page opens on all
 * of them.
 */
export declare const PAGE_STEP = 12;
/**
 * The index a random draw lands on, for a list of `length` items. -1 when
 * the list is empty; a draw outside [0, 1) lands on the first item.
 */
export declare function randomIndex(length: number, random?: () => number): number;
/**
 * A random item of the list, or undefined when the list is empty. The
 * random source is a parameter, so a seeded generator makes the choice
 * reproducible (the old viewer's `pickRandom`).
 */
export declare function pickRandomCase<T>(cases: T[], random?: () => number): T | undefined;
/**
 * Wire the page: fetch the index, open one group, and keep the page in step
 * with the state. The render layer does the markup; this does the fetching,
 * the events and the hash.
 */
export declare function mountCasesPage(opts: MountCasesOptions): Promise<void>;

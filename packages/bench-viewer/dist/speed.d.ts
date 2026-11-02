/**
 * The speed page: the 10,000-input speed benchmark, as the release holds it.
 *
 * `speed.json` is the page's view of the per-pair rows: the tasks, their
 * coverage, their tables and their notes. The notes are plain text, and a
 * `backtick` span in them means inline code — so every string is escaped
 * first and the backticks are read afterwards, never the other way round.
 *
 * The render layer is pure (`renderSpeed`): data in, HTML out. The wiring
 * (`mountSpeedPage`) fetches the file and puts the string on the page.
 */
/** How much of a lane's plan it covered. */
export interface SpeedCoverage {
    tool: string;
    completed: number;
    planned: number;
}
/** One tool's timings in one bucket. */
export interface SpeedRow {
    tool: string;
    bucket: string;
    n: number;
    ok: number;
    failed: number;
    median_ms: number | null;
    mean_ms: number | null;
    p95_ms: number | null;
    p99_ms: number | null;
    max_ms: number | null;
    ok_total_s: number | null;
}
/** One table: a bucket per tool. */
export interface SpeedTable {
    id: string;
    title: string;
    bucket_header: string;
    rows: SpeedRow[];
}
/** One note: a heading, paragraphs and bullets, all plain text. */
export interface SpeedNote {
    heading: string;
    paragraphs: string[];
    bullets: string[];
}
/** One measured task (redlines, DOCX to PDF). */
export interface SpeedTask {
    id: string;
    title: string;
    description: string;
    available: boolean;
    planned?: number | null;
    timeout_ms?: number | null;
    quartile_cuts_bytes: number[];
    coverage: SpeedCoverage[];
    tables: SpeedTable[];
    notes: SpeedNote[];
}
/** `speed.json`: the whole page. */
export interface Speed {
    version: string;
    generated: string;
    repo: string;
    title: string;
    intro: string;
    tasks: SpeedTask[];
}
/** The speed release, validated field by field. */
export declare function parseSpeed(value: unknown): Speed;
/**
 * One text value, escaped, with its `backtick` spans read as inline code.
 * The escaping happens first: the backticks are the contract's, and what is
 * between them is still data.
 */
export declare function inlineCode(text: string): string;
/** A number as the speed page shows it: one decimal, or a dash. */
export declare function formatMs(value: number | null | undefined): string;
/** The coverage of one lane, as the page words it. */
export declare function renderCoverage(coverage: SpeedCoverage): string;
/** One table of timings. */
export declare function renderSpeedTable(table: SpeedTable): string;
/**
 * The paragraph the common table wears: a failed call is counted apart and
 * left out of every statistic, so each tool's sample is its own `ok` count.
 */
export declare function renderSampleNote(table: SpeedTable): string;
/** One note: its heading, its paragraphs and its bullets. */
export declare function renderSpeedNote(note: SpeedNote): string;
/** One task: its heading, its description, its coverage, its tables, its notes. */
export declare function renderSpeedTask(task: SpeedTask): string;
/** The whole speed page's body. */
export declare function renderSpeed(speed: Speed): string;
/** The page the speed view wears. */
export interface SpeedPageOptions {
    /** The file the page fetches, relative to the page. */
    speedUrl: string;
    /** The module the page imports, relative to the page. */
    moduleUrl: string;
    /** The stylesheet the page links, relative to the page. */
    stylesheet?: string;
    /** The page's title. */
    title?: string;
    /** The page's meta description. */
    description?: string;
    /** The links in the breadcrumb. */
    links?: {
        href: string;
        label: string;
    }[];
}
/** The whole speed page: the shell the wiring fills in. No data in it. */
export declare function renderSpeedPage(opts: SpeedPageOptions): string;
/** How the speed page is told where its data is. */
export interface MountSpeedOptions {
    /** The file the page fetches. */
    speedUrl: string;
    /** The document the page lives in. */
    root?: Document;
}
/** Fetch the speed release and put it on the page. */
export declare function mountSpeedPage(opts: MountSpeedOptions): Promise<void>;

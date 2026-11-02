/**
 * The arthur-law page: the scores, ranked.
 *
 * benchmarks.law shows what the bench measured, not what one product sells.
 * So this page has none of jubarte's framing: no headline cells (they are
 * "jubarte vs X"), no "ours" rows, no affiliation dagger, no legend about
 * them. Every tool is in every table, in the order the bench ranked it, and
 * the leader of each table is named above it.
 *
 * What stays: the badge, the corpus states, the method, the provenance and
 * the footer. What moves: the tables come in two groups — the full-corpus
 * tables first, the release's own samples after them, under their own
 * heading.
 */
import type { Scores } from "./types.ts";
/** The heading over the tables scored on the release's own samples. */
export declare const SAMPLES_HEADING = "600-document samples";
/** The id of the samples group's heading. */
export declare const SAMPLES_HEADING_ID = "lb-samples";
export interface LeaderboardPageOptions {
    /** The badge's version tag; the scores' own version by default. */
    tag?: string;
    /** The heading over the sample tables. */
    samplesHeading?: string;
    /** The page's title. */
    title?: string;
    /** The page's meta description. */
    description?: string;
}
/** Drop the affiliation mark: this page ranks tools, not owners. */
export declare function stripAffiliation(name: string): string;
/**
 * The whole leaderboard page. Every text value goes through esc().
 *
 * The tables come in two groups: the full-corpus ones first, the release's
 * own samples after them under their own heading.
 */
export declare function buildLeaderboardPage(scores: Scores, opts?: LeaderboardPageOptions): string;

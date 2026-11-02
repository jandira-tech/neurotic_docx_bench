import type { Scores } from "./types.ts";
/** Validate an absolute HTTP(S) URL before it can reach an href attribute. */
export declare function requireHttpUrl(value: unknown, path: string): string;
/** Validate a parsed `scores.json` document and return it as `Scores`. */
export declare function parseScores(json: unknown): Scores;

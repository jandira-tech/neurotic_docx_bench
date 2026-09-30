import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { TimedEngine } from "./lib/timed_engine.ts";

const SPIN = resolve("scripts/fixtures/spin_engine.mjs");
const b = (...xs: number[]) => new Uint8Array(xs);

describe("TimedEngine (one engine per child process, per-call timeout)", () => {
	it("times a call inside the worker and returns the output size", async () => {
		const eng = new TimedEngine({ module: SPIN }, 5_000);
		try {
			const r = await eng.call(b(1, 0), b(9, 9, 9));
			expect(r.ok).toBe(true);
			expect(r.outBytes).toBe(3);
			expect(r.ms).toBeGreaterThanOrEqual(95);
			expect(r.ms).toBeLessThan(2_000);
		} finally {
			await eng.close();
		}
	});

	it("kills a call stuck in synchronous code at the timeout and keeps working after it", async () => {
		const eng = new TimedEngine({ module: SPIN }, 500);
		try {
			const t0 = performance.now();
			const stuck = await eng.call(b(255, 0), b(1));
			expect(performance.now() - t0).toBeLessThan(5_000);
			expect(stuck).toMatchObject({ ok: false, timedOut: true, ms: 500 });
			expect(stuck.error).toMatch(/timeout/);
			expect(eng.restarts).toBe(1);
			const after = await eng.call(b(0, 0), b(7, 7));
			expect(after).toMatchObject({ ok: true, outBytes: 2 });
		} finally {
			await eng.close();
		}
	}, 20_000);

	it("a timeout also kills the helper processes the engine started", async () => {
		const helpers = () =>
			execFileSync("ps", ["-Ao", "command"], { encoding: "utf8" })
				.split("\n")
				.filter((l) => l.trim() === "sleep 3601").length;
		const before = helpers();
		const eng = new TimedEngine({ module: SPIN }, 800);
		try {
			const r = await eng.call(b(255, 2), b(1));
			expect(r.timedOut).toBe(true);
			await new Promise((ok) => setTimeout(ok, 300));
			expect(helpers()).toBe(before);
		} finally {
			await eng.close();
		}
	}, 20_000);

	it("reports an engine error as a failed call, not a timeout", async () => {
		const eng = new TimedEngine({ module: SPIN }, 5_000);
		try {
			const r = await eng.call(b(0, 1), b(1));
			expect(r).toMatchObject({ ok: false, timedOut: false });
			expect(r.error).toMatch(/refused/);
			expect(eng.restarts).toBe(0);
		} finally {
			await eng.close();
		}
	});
});

// Test engine for scripts/lib/timed_engine.ts: spins synchronously (as a WASM compare does) for
// base[0] * 100 ms, then returns `next`. base[0] = 255 is a call that never finishes in a test.
// base[1] = 1 throws; base[1] = 2 first starts a helper process (`sleep 3601`), as an engine
// with a long-lived CLI worker does.
import { spawn } from "node:child_process";

export default function load() {
	return async (base, next) => {
		if (base[1] === 2) spawn("sleep", ["3601"], { stdio: "ignore" });
		const until = Date.now() + base[0] * 100;
		while (Date.now() < until) {
			/* busy, like a compare stuck in WASM: no await, so no timer can interrupt it */
		}
		if (base[1] === 1) throw new Error("engine refused the pair");
		return next;
	};
}

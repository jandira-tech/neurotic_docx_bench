/**
 * Child-process side of TimedEngine: loads one redline engine on this process's main thread
 * (as the in-process speed lanes always ran), then answers `{ id, base, next }` over IPC with
 * `{ id, ok, ms, outBytes | error }`, the call timed in here so the IPC copy is not counted.
 * `{ type: "close" }` shuts the engine's long-lived helper processes down and exits.
 * Spec: argv[2] is JSON, `{ module }` (a test engine) or `{ engId, dist }`.
 */
import { performance } from "node:perf_hooks";
import { pathToFileURL } from "node:url";

type Engine = (base: Uint8Array, next: Uint8Array) => Promise<Uint8Array>;
const spec = JSON.parse(process.argv[2]!) as {
	module?: string;
	engId?: string;
	dist?: string;
};
const send = (m: unknown) => process.send!(m);

let engine: Engine;
let shutdown = () => {};
if (spec.module) {
	const mod = await import(pathToFileURL(spec.module).href);
	engine = mod.default();
} else {
	const gen = await import("../generate-native-redlines.ts");
	engine = await gen.loadEngine(spec.engId!, spec.dist!);
	shutdown = gen.shutdownAllLongLivedWorkers;
}
send({ type: "ready" });

process.on(
	"message",
	async (m: {
		type?: string;
		id: number;
		base: Uint8Array;
		next: Uint8Array;
	}) => {
		if (m.type === "close") {
			shutdown();
			process.exit(0);
		}
		const s = performance.now();
		try {
			const out = await engine(m.base, m.next);
			send({
				id: m.id,
				ok: true,
				ms: performance.now() - s,
				outBytes: out.byteLength,
			});
		} catch (e) {
			send({
				id: m.id,
				ok: false,
				ms: performance.now() - s,
				error: (e as Error)?.message || String(e),
			});
		}
	},
);

/**
 * TimedEngine: one redline engine in its own child process, so a single call can be stopped.
 *
 * An in-process engine (docxodus's .NET WASM, jubarte-wasm) computes synchronously once it
 * starts, so a timer on the same thread never fires and `Promise.race` cannot end the call.
 * Here the engine runs on the main thread of a child Node process (the same kind of thread
 * the speed lanes always used; a worker thread measured docxodus about 1.5x slower). The
 * parent waits at most `timeoutMs` per call, then SIGKILLs the child's process group (the
 * engine and any helper process it spawned), records a timeout and starts a fresh child for
 * the next call. Process start and engine init are never timed.
 */
import { type ChildProcess, fork } from "node:child_process";
import { performance } from "node:perf_hooks";
import { fileURLToPath } from "node:url";

export type EngineSpec = { module: string } | { engId: string; dist: string };
export type CallResult = {
	ok: boolean;
	timedOut: boolean;
	ms: number;
	outBytes?: number;
	error?: string;
};

const ENTRY = fileURLToPath(
	new URL("./timed_engine_child.ts", import.meta.url),
);

type Reply = {
	type?: string;
	id?: number;
	ok?: boolean;
	ms?: number;
	outBytes?: number;
	error?: string;
};

function killGroup(child: ChildProcess): void {
	try {
		process.kill(-child.pid!, "SIGKILL");
	} catch {
		child.kill("SIGKILL");
	}
}

export class TimedEngine {
	/** Children replaced after a timeout or a crash. */
	restarts = 0;
	/** Process start + engine init, one entry per child started (ms). */
	initMs: number[] = [];
	private child: ChildProcess | null = null;
	private seq = 0;

	constructor(
		private readonly spec: EngineSpec,
		private readonly timeoutMs: number,
	) {}

	/** Start the child and wait until the engine is loaded (untimed for calls). */
	async start(): Promise<void> {
		if (this.child) return;
		const t0 = performance.now();
		const c = fork(ENTRY, [JSON.stringify(this.spec)], {
			execArgv: ["--import", "tsx"],
			serialization: "advanced", // Uint8Array crosses IPC as bytes, not JSON
			detached: true, // own process group, so a timeout also kills its helpers
			stdio: ["ignore", "ignore", "inherit", "ipc"],
		});
		await new Promise<void>((ok, fail) => {
			const onMsg = (m: Reply) => {
				if (m.type !== "ready") return;
				c.off("message", onMsg);
				c.off("exit", onExit);
				ok();
			};
			const onExit = (code: number | null) =>
				fail(new Error(`engine process exited during init (code ${code})`));
			c.on("message", onMsg);
			c.once("exit", onExit);
		});
		this.initMs.push(performance.now() - t0);
		this.child = c;
	}

	async call(base: Uint8Array, next: Uint8Array): Promise<CallResult> {
		await this.start();
		const c = this.child!;
		const id = ++this.seq;
		const sent = performance.now();
		return new Promise<CallResult>((resolve) => {
			const done = (r: CallResult) => {
				clearTimeout(timer);
				c.off("message", onMsg);
				c.off("exit", onExit);
				resolve(r);
			};
			const onMsg = (m: Reply) => {
				if (m.id !== id) return;
				done({
					ok: m.ok!,
					timedOut: false,
					ms: m.ms!,
					...(m.ok ? { outBytes: m.outBytes } : { error: m.error }),
				});
			};
			const onExit = (code: number | null, signal: string | null) => {
				this.child = null;
				this.restarts++;
				done({
					ok: false,
					timedOut: false,
					ms: performance.now() - sent,
					error: `engine process died (code ${code}, signal ${signal})`,
				});
			};
			const timer = setTimeout(() => {
				c.off("exit", onExit);
				this.child = null;
				this.restarts++;
				killGroup(c);
				done({
					ok: false,
					timedOut: true,
					ms: this.timeoutMs,
					error: `timeout after ${this.timeoutMs} ms`,
				});
			}, this.timeoutMs);
			c.on("message", onMsg);
			c.once("exit", onExit);
			c.send({ id, base, next });
		});
	}

	async close(): Promise<void> {
		const c = this.child;
		this.child = null;
		if (!c || c.exitCode !== null) return;
		const exited = new Promise((r) => c.once("exit", r));
		c.send({ type: "close" });
		const t = setTimeout(() => killGroup(c), 5_000);
		await exited;
		clearTimeout(t);
	}
}

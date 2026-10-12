/**
 * Pre-leg machine check for the speed benches: wait until CPU load and memory are
 * decently quiet and steady before a lane starts, and record what was measured.
 *
 * A desktop is never silent (WindowServer, Spotlight, power daemons), so the gate asks
 * for "decently quiet": moderate CPU over a short window, enough free memory that does
 * not drift, and no swapping. A machine that never settles does not block the run; the
 * leg proceeds and its row carries `stable: false` with the processes that held it.
 */
import { spawnSync } from "node:child_process";
import { cpus, loadavg } from "node:os";

export interface StabilityLimits {
	/** Sampling window, seconds (one sample per second). */
	windowS: number;
	/** Mean busy share of all cores over the window, percent. */
	maxCpuMean: number;
	/** Busiest one-second sample, percent. */
	maxCpuPeak: number;
	/** Lowest acceptable macOS "memory free percentage". */
	minMemFree: number;
	/** Largest swing of that percentage within the window, points. */
	maxMemDrift: number;
	/** Pages swapped out during the window. */
	maxSwapouts: number;
	/** Give up waiting after this long and run anyway (flagged). */
	timeoutS: number;
}

export const DEFAULT_LIMITS: StabilityLimits = {
	windowS: 10,
	maxCpuMean: 25,
	maxCpuPeak: 45,
	minMemFree: 20,
	maxMemDrift: 5,
	maxSwapouts: 256,
	timeoutS: 600,
};

export interface MachineState {
	stable: boolean;
	waited_s: number;
	attempts: number;
	cpu_busy_mean: number;
	cpu_busy_peak: number;
	mem_free_min: number | null;
	mem_free_max: number | null;
	swapouts: number | null;
	load1: number;
	/** Why the last window failed (empty when stable). */
	reasons: string[];
	/** Busiest processes when the last window failed. */
	top: string[];
	limits: StabilityLimits;
}

function cpuTotals(): { idle: number; total: number } {
	let idle = 0;
	let total = 0;
	for (const c of cpus()) {
		const t = c.times;
		idle += t.idle;
		total += t.user + t.nice + t.sys + t.idle + t.irq;
	}
	return { idle, total };
}

/** macOS `memory_pressure -Q` free percentage; null elsewhere. */
function memFreePct(): number | null {
	const r = spawnSync("memory_pressure", ["-Q"], { encoding: "utf8" });
	const m = /free percentage:\s*(\d+)%/.exec(r.stdout ?? "");
	return m ? Number(m[1]) : null;
}

/** Cumulative `vm_stat` swapouts; null elsewhere. */
function swapouts(): number | null {
	const r = spawnSync("vm_stat", { encoding: "utf8" });
	const m = /Swapouts:\s*(\d+)/.exec(r.stdout ?? "");
	return m ? Number(m[1]) : null;
}

function topProcesses(n = 4): string[] {
	const r = spawnSync("ps", ["-Ao", "pcpu=,rss=,comm=", "-r"], { encoding: "utf8" });
	return (r.stdout ?? "")
		.split("\n")
		.map((l) => l.trim())
		.filter(Boolean)
		.slice(0, n)
		.map((l) => {
			const [pcpu, rss, ...cmd] = l.split(/\s+/);
			const name = cmd.join(" ").split("/").at(-1);
			return `${name} ${pcpu}% ${Math.round(Number(rss) / 1024)}M`;
		});
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
const round1 = (x: number) => Math.round(x * 10) / 10;

async function sampleWindow(limits: StabilityLimits): Promise<Omit<MachineState, "waited_s" | "attempts" | "limits" | "top">> {
	const busy: number[] = [];
	const mem: number[] = [];
	const swap0 = swapouts();
	let prev = cpuTotals();
	for (let i = 0; i < limits.windowS; i++) {
		await sleep(1000);
		const cur = cpuTotals();
		const dt = cur.total - prev.total;
		busy.push(dt > 0 ? 100 * (1 - (cur.idle - prev.idle) / dt) : 0);
		prev = cur;
		const m = memFreePct();
		if (m !== null) mem.push(m);
	}
	const swap1 = swapouts();
	const mean = busy.reduce((a, b) => a + b, 0) / busy.length;
	const peak = Math.max(...busy);
	const memMin = mem.length ? Math.min(...mem) : null;
	const memMax = mem.length ? Math.max(...mem) : null;
	const swapped = swap0 !== null && swap1 !== null ? swap1 - swap0 : null;
	const reasons: string[] = [];
	if (mean > limits.maxCpuMean) reasons.push(`cpu mean ${round1(mean)}% > ${limits.maxCpuMean}%`);
	if (peak > limits.maxCpuPeak) reasons.push(`cpu peak ${round1(peak)}% > ${limits.maxCpuPeak}%`);
	if (memMin !== null && memMin < limits.minMemFree) reasons.push(`mem free ${memMin}% < ${limits.minMemFree}%`);
	if (memMin !== null && memMax !== null && memMax - memMin > limits.maxMemDrift) {
		reasons.push(`mem drift ${memMax - memMin} pts > ${limits.maxMemDrift}`);
	}
	if (swapped !== null && swapped > limits.maxSwapouts) reasons.push(`swapouts +${swapped} > ${limits.maxSwapouts}`);
	return {
		stable: reasons.length === 0,
		cpu_busy_mean: round1(mean),
		cpu_busy_peak: round1(peak),
		mem_free_min: memMin,
		mem_free_max: memMax,
		swapouts: swapped,
		load1: round1(loadavg()[0]),
		reasons,
	};
}

/** Wait for a decently quiet, steady machine; never throws, never blocks past `timeoutS`. */
export async function waitForStableMachine(
	label: string,
	limits: StabilityLimits = DEFAULT_LIMITS,
	log: (s: string) => void = (s) => process.stdout.write(s),
): Promise<MachineState> {
	const t0 = Date.now();
	let attempts = 0;
	for (;;) {
		attempts++;
		const w = await sampleWindow(limits);
		const waited = round1((Date.now() - t0) / 1000);
		const summary =
			`cpu ${w.cpu_busy_mean}% (peak ${w.cpu_busy_peak}%), mem free ${w.mem_free_min ?? "?"}–${w.mem_free_max ?? "?"}%, ` +
			`swapouts +${w.swapouts ?? "?"}, load ${w.load1}`;
		if (w.stable) {
			log(`  machine ${label}: steady after ${waited}s — ${summary}\n`);
			return { ...w, waited_s: waited, attempts, top: [], limits };
		}
		const top = topProcesses();
		if (waited >= limits.timeoutS) {
			log(`  machine ${label}: NOT steady after ${waited}s, running anyway — ${w.reasons.join("; ")}; top: ${top.join(", ")}\n`);
			return { ...w, waited_s: waited, attempts, top, limits };
		}
		if (attempts === 1 || attempts % 6 === 0) {
			log(`  machine ${label}: waiting (${w.reasons.join("; ")}); top: ${top.join(", ")}\n`);
		}
	}
}

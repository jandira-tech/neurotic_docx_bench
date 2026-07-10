import { defineConfig } from "vitest/config";

// Scope vitest to the bench's own driver tests. Without this, `vitest run` globs the whole
// tree — including the git-ignored `.old/` SuperDoc/docs monorepos — and runs thousands of
// unrelated tests.
export default defineConfig({
	test: {
		include: ["scripts/**/*.test.ts"],
		exclude: [
			"**/node_modules/**",
			".old/**",
			"dist/**",
			"corpus/**",
			"runs/**",
		],
	},
});

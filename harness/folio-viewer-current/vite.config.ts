import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Harness dev server for the folio Playwright renderer.
// `bench run` starts this via the run's `harness.server` shell command and
// polls `harness.url`; the renderer uploads each DOCX through #fileInput.
export default defineConfig({
	plugins: [react()],
	server: {
		host: "127.0.0.1",
		port: 5176,
	},
});

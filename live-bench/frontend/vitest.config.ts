// SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
// SPDX-License-Identifier: AGPL-3.0-only
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    include: ['tests/**/*.test.ts'],
    coverage: {
      provider: 'v8', include: ['src/lib/**/*.ts'], reporter: ['text', 'json-summary', 'html'], reportOnFailure: true,
      thresholds: { lines: 90, branches: 85, functions: 90, statements: 90 },
    },
  },
});

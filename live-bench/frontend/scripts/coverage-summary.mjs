// SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
// SPDX-License-Identifier: AGPL-3.0-only
import { readFileSync } from 'node:fs';

const { total } = JSON.parse(readFileSync(new URL('../coverage/coverage-summary.json', import.meta.url), 'utf8'));
console.log(`Coverage: ${total.lines.pct}% lines, ${total.branches.pct}% branches`);

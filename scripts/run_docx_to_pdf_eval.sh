#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
#
# SPDX-License-Identifier: AGPL-3.0-only
#
# The scheduled 30-minute DOCX→PDF visual test. Same command as one-shot verify:
# convert the pinned 100 fixtures with jubarte, score soffice-vs-self and
# converter-vs-soffice via the shipped visual pipeline.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
JUBARTE="${JUBARTE:-$ROOT/../jubarte-redlines/target/release/jubarte}"
OUT="${1:-$ROOT/results/docx_to_pdf.json}"
cd "$ROOT"
exec uv run bench docx-to-pdf --converter "$JUBARTE" --json "$OUT" --jobs 8

#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
#
# SPDX-License-Identifier: AGPL-3.0-only
#
# Score the pinned 500 Word-oracle DOCX→PDF set with the four named converters.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$ROOT/results/docx_to_pdf_500.json}"
cd "$ROOT"
exec uv run bench docx-to-pdf \
  --tool jubarte --tool rdocx --tool office2pdf --tool pdfitdown --tool doxx \
  --json "$OUT" --jobs 8

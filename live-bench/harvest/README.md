# D1 live-bench harvest

Follow-up tooling for the live benchmark worker (`../backend`): it watches the remote
D1 database `jubarte-live-bench`, downloads the fixtures that failed (Word convert or
redline render), and drives a local Word over them to sort genuinely broken DOCX from
worker-side noise. The verdicts land in the repo's `really_broken/` manifest, which the
Word-driver work consumes.

Everything here talks to Cloudflare through **wrangler** (`npx wrangler d1 execute
jubarte-live-bench --remote --json`) and to the worker's public artifact URLs
(`https://jubarte.pro/live/artifacts/…`). See `docs/PUBLISHING.md` (top-level repo) for
the account, resources and login.

## Workflow (`harvest.py`)

```
uv run --no-project --python 3.14 --with httpx python -I harvest.py prepare
uv run --no-project --python 3.14 python -I harvest.py collect <run_dir>
```

- `prepare` — new `bench_results` rows since the watermark (remote D1) → unseen failing
  fixtures and tool redlines → download (sha256-checked) → the word-endpoint guard and
  the pure-XML gate → unsafe files deleted → the rest staged in `<run>/word_in/`.
  Files are never modified.
- `collect` — parse Word's verdicts for the run (`word*.stdout`, PDFs under `word_pdf*`),
  copy broken files into `really_broken/<fixtures|tool_redlines>/<category>/`, append to
  `really_broken/manifest.csv`, advance `seen.csv` and the watermark, delete Word PDFs.

State lives in `../.work/harvest/` (git-ignored): `seen.csv` (every sha256 already
harvested, with its verdict) and `watermark.txt` (the last `completed_at` handled).
`NDB_LIVE_WORK` moves the whole work dir. The first run without `seen.csv` bootstraps
from the pre-2026-10-15 analysis tree (`NDB_LIVE_WORK_LEGACY`, default
`~/temp/T/d1_jubarte_live_bench`, deleted after migration; the migrated `seen.csv`
already carries its state).

## Helpers

| script | what it does |
|---|---|
| `fetch_and_guard.py` | download refused fixtures (sha256-checked), re-run the word-endpoint guard |
| `fetch_tool_redlines.py` | download failed tool redline DOCX from the artifact store, guard them |
| `purexml_gate.py` | the local pure-XML gate over a directory |
| `stage_chunks.py` | stage `really_broken/` chunks for a Word batch |
| `word_singles.py` / `word_rejections.py` | drive Word over single files / analyze rejections |
| `join_word_verdicts.py` / `join_tool_redlines.py` | fold verdicts into the analysis CSVs |
| `logger_coverage.py` | cross-check the screen log against the logger captures |

The Word side itself uses the repo's `scripts/word_pdf.py` driver (one `osascript`,
watchdog, `[retry]` rules — see AGENTS.md "Gotchas"); `NDB_WORD_ENDPOINT` points at the
word-endpoint checkout the guard imports (default `~/T/word-endpoint`).

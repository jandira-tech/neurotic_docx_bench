# Word endpoint

Three POST endpoints use the Microsoft Word already installed on this machine.

| Endpoint | Upload | Result |
| --- | --- | --- |
| `POST /v1/compare` | `original` and `revised` `.docx` files | A `.docx` blackline with tracked changes |
| `POST /v1/compare-pdf` | `original` and `revised` `.docx` files | A PDF of the comparison, including markup |
| `POST /v1/convert` | one `document` `.docx` file | A PDF |

The service listens on `127.0.0.1` only. Callers must send `Authorization: Bearer <token>`. The token is created in `.env` the first time the service starts. The public address is `WORD_PUBLIC_URL` in that file.

Run this from an interactive Windows session. Word cannot automate from a Windows service.

## Start and stop

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start.ps1
powershell -ExecutionPolicy Bypass -File scripts\stop.ps1
```

`start.ps1` registers a logon task named `WordEndpoint`. The task keeps the service running after you close this terminal, and it starts again the next time this Windows user logs on. Disconnecting Remote Desktop leaves it running. Signing out stops it until the next logon. `stop.ps1` turns the task off until `start.ps1` is run again.

A second, independent watchdog (`scripts\public-watchdog.ps1`, registered as the `WordEndpointWatchdog` scheduled task, running as SYSTEM every 5 minutes) checks the public URL. After two consecutive failures it restarts the `cloudflared` service when only the tunnel is down (or, without the service, replaces or starts the named-tunnel process `start.ps1` launched), or starts the `WordEndpoint` task when the local service is down too. It logs to `logs\public-watchdog.log`. The task checks the service every 15 seconds and starts it again when it is down.

The public address is `https://docx.rodrigues.ai`. The local address stays `http://127.0.0.1:8787`. `start.ps1` keeps `WORD_PUBLIC_URL` when it is a stable `https://` address, and it does not start a second tunnel.

On a machine without that hostname, leave `WORD_PUBLIC_URL` unset. `start.ps1` then opens a temporary `trycloudflare.com` address and records it. You can instead set `CLOUDFLARE_TUNNEL_TOKEN` so the script runs a named tunnel; put it in `.env` (or a machine environment variable), because the watchdog runs as SYSTEM and cannot see your user environment. cloudflared gets the token through its environment, not its command line. You can put Cloudflare Access in front of the named hostname as a second lock.

`.env` holds the API token. `start.ps1` creates it on first run, readable and writable by you and readable by SYSTEM (for the watchdog), and nobody else. On every start it refuses a `.env` that inherits its folder's permissions or grants anyone other than SYSTEM, Administrators and you, and prints the `icacls` command that fixes it. `WORD_API_TOKEN` must be 32 to 256 characters of letters, digits and `- . _ ~ + /`, optionally ending in `=` (an RFC 6750 bearer token); the service refuses to start with any other token.

## Call

```powershell
$token = (Get-Content .env | Where-Object { $_ -like 'WORD_API_TOKEN=*' }).Split('=', 2)[1]

curl.exe -sS -X POST "http://127.0.0.1:8787/v1/convert" `
  -H "Authorization: Bearer $token" `
  -F "document=@C:\path\file.docx" `
  -o C:\path\file.pdf

curl.exe -sS -X POST "http://127.0.0.1:8787/v1/compare" `
  -H "Authorization: Bearer $token" `
  -F "original=@C:\path\original.docx" `
  -F "revised=@C:\path\revised.docx" `
  -o C:\path\comparison.docx
```

Use the public URL the same way. Send the token only in the `Authorization` header. Query strings are rejected so the token is not written to tunnel logs.

To get a comparison PDF directly, upload `original` and `revised` to `/v1/compare-pdf`. Word exports its live comparison result without saving and reopening an intermediate DOCX. This uses the existing comparison worker; the independent PDF conversion worker stays available for `/v1/convert`. You can still send an existing `comparison.docx` to `/v1/convert`.

```powershell
curl.exe -sS -X POST "http://127.0.0.1:8787/v1/compare-pdf" `
  -H "Authorization: Bearer $token" `
  -F "original=@C:\path\original.docx" `
  -F "revised=@C:\path\revised.docx" `
  -o C:\path\comparison.pdf
```

Worker startup disables automatic spelling and grammar checking once per Word process and logs the resulting settings. Screen updating is also disabled. These settings do not accept revisions or hide comments.

From Administrator PowerShell, run `.tools\python\python.exe -B tests\live_check.py` for live Word verification. Synthetic PDF outputs are saved under `artifacts\performance-verification`. Run `.tools\python\python.exe -B scripts\benchmark-word.py` to compare the separate and combined workflows on identical synthetic documents; the first pair warms Word and the next three pairs are measured.

For Windows maintenance, `powershell -ExecutionPolicy Bypass -File scripts\tune-windows.ps1` audits the existing settings. Add `-Apply` to move scheduled Defender scans to 03:00 local time and disable Server Manager launching at logon. `-ScanHour` changes that hour; scan frequency and real-time protection are preserved. Previous values are saved to `reports\windows-settings-before-*.json`. `-RecordDefender` records 60 seconds of Defender activity and saves a performance report; send endpoint requests during that interval. The script requires Administrator privileges. No antivirus exclusions are added.

## What the service refuses

Template references on uploaded copies are detached before Word opens them. Internal package relationships such as ../customXml/item1.xml are resolved relative to their source part and accepted when they point to an existing part inside the package. ZIP entry names still cannot contain traversal. Static SVG images are accepted; scripts, event handlers, animation, and external SVG references are rejected.

Word opens the file only after these checks pass. The service keeps two Word processes open: one compares documents, and the other exports PDFs. Later requests reuse those processes. Macros stay forced off, and fields stay locked so they are not updated. A second request of the same kind waits until the first finishes, up to 180 seconds. The service accepts 300 POSTs a minute. A job that runs longer than its budget is killed, including the Word process it was using, and the next job starts a fresh one. The budget is 120 seconds plus 20 seconds per uploaded megabyte above 2 MB (capped at 300 seconds total), so heavy but valid documents are not cut off mid-export. Other Word windows are left alone.

Rejected uploads:

- Anything that is not a `.docx` package, including macro-enabled files
- Encrypted or password-protected documents
- Macros, ActiveX, and macro form fields
- DDE, `INCLUDETEXT`, `INCLUDEPICTURE`, `LINK`, `MACROBUTTON`, and similar fields
- Mail merge, subdocuments, and external relationships other than HTTP, HTTPS, or mailto hyperlinks (template references are detached)
- Embedded executables, scripts, HTML, or active SVG
- Zip bombs, path traversal, and files over 20 MB

The client cannot send a path, a URL, or a Word option. PDF export omits document properties so this machine's file path is not copied into the PDF. Comparison files have Word's local template stamp removed before they are returned.

PDF export includes tracked-change markup and fails if that export fails; it never silently falls back to a clean PDF. Every PDF export (both comparison workflows and conversions) uses the review view of the Word for Mac that made the bench's oracle: all markup, insertions, deletions and formatting changes inline, comments printed in the margin, no "Formatted:" balloons. Each Word start also sets Word's revision marks and colours to that Mac's (underline, strikethrough, red changed-line bar, colours by author). Both are set in code, so a restart, a reset profile or another machine exports the same view; see [docs/review-view.md](docs/review-view.md).

## Updates, readiness and diagnostics

After source changes, run powershell -ExecutionPolicy Bypass -File scripts\restart.ps1 from the existing Windows user's interactive session. It runs the tests, restarts the existing logon task, waits for both Word workers, and checks actual comparisons and PDF exports. Cloudflare stays running.

Add `-Benchmark` to the restart command to measure the separate and combined comparison PDF workflows after verification. Live verification checks that deleted/inserted amounts and both synthetic comment texts remain in the PDFs. Inline revisions still print comment bodies in the margin.

Package limits are 20 MB compressed per upload, 128 MB expanded in total, 64 MB per member, 32 MB per XML part, and 4,096 entries. Highly compressed repetitive XML is accepted within these limits.

XML parts are parsed with `purexml` 1.0.1, with DTDs, declared entities and external resolution forbidden. Element nesting is capped at 1,000 and attributes at 256 per element. The dependency is installed from the offline wheel in `vendor/`; `vendor/purexml-provenance.json` records the reviewed upstream commit and wheel hash. Run `scripts/bootstrap.ps1` to install dependencies on an existing checkout before restarting it.

To compare a separately installed Python runtime, install this checkout's `requirements.txt` into that interpreter and run `.tools\python\python.exe -B scripts\benchmark-python.py --candidate C:\path\to\candidate\python.exe`. It measures sequential and four-thread synthetic DOCX validation and checks native Word-module imports, without launching Word or changing the service runtime. Results are saved to `reports/python-runtime-benchmark.json`; actual Word comparison/PDF testing is still required before switching runtimes.

As of October 13, 2026, published `pywin32` 312 wheels support ordinary Python 3.15 but have no `cp315t` wheel. The isolated `.tools\python315t-bench` environment can benchmark the guard with the local `purexml` wheel; it cannot run the existing Word workers with the published native dependency.

`python-runtime.json` selects the service runtime. Version `3.15` uses `.tools\python315-bench\Scripts\python.exe`, which passed all 75 application tests and actual Word redline, PDF and comment-preservation checks. Startup, supervision and restart verification use this same interpreter. Run `scripts/restart.ps1` from the interactive Windows session to apply the selection. The existing 3.12 installation is retained for rollback: set `version` to `3.12` in `python-runtime.json` and run `scripts/restart.ps1` again. Install `uv` before using `scripts/bootstrap.ps1` to set up a missing 3.15 environment.

MAX_CONCURRENT defaults to four admitted uploads/jobs, including queued jobs. Admission happens before reading uploads. Additional requests receive 503 with Retry-After: 5. There is also a separate cap on HTTP handler threads; comparison and conversion still each use one Word instance.

GET /ready reports Word readiness and returns 503 during worker startup or recovery. GET /health preserves HTTP liveness for existing supervisors and includes a ready flag and both worker states. GET /live checks HTTP liveness; new supervisors use it. Recovering one worker does not restart the healthy lane. Idle workers are pinged every 15 seconds and replaced when unresponsive. Running jobs retain their timeout.

Rejection logs include a rule (reason), package part and request ID, without retaining uploaded files or printing their text. Stage timings cover validation, queue wait, input preparation, Word opening/comparison/export and output processing. Server and worker logs rotate at 2 MB with three backups. Successful health polls are omitted from request logs.

To diagnose a saved document without launching Word, run .tools\python\python.exe scripts\audit-docx.py C:\path\document.docx. It reports the rejecting rule and package part, without printing document contents.

Temporary copies live under `work\` and are deleted after the response. `.env` is the only secret. Do not commit it, and do not open port 8787 in the Windows Firewall.

# Watches the public URL and heals the chain when it goes dark.
# Runs as a SYSTEM scheduled task (no Word automation here, so Session 0 is
# fine). Two layers below it can fail without this noticing otherwise:
#   - the interactive keep-alive/session dies  -> restart the WordEndpoint task
#   - the cloudflared tunnel service dies      -> restart the cloudflared service
# Recovery is conservative: it acts only after N consecutive failures and
# never while a previous action has not had time to take effect.

param(
    [int]$FailuresBeforeAction = 2,
    [int]$TimeoutSec = 20,
    [switch]$CheckOnly
)

$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
$Log = Join-Path $Root "logs\public-watchdog.log"
$StateFile = Join-Path $Root "logs\public-watchdog.state"
$envFile = Join-Path $Root ".env"

$port = 8787
$PublicUrl = $null
if (Test-Path $envFile) {
    foreach ($line in Get-Content $envFile) {
        if ($line -match '^PORT=(\d+)$') { $port = [int]$Matches[1] }
        if ($line -match '^WORD_PUBLIC_URL=(https://.+)$') { $PublicUrl = $Matches[1].Trim().TrimEnd('/') }
    }
}
if (-not $PublicUrl) { $PublicUrl = "https://docx.rodrigues.ai" }

function Write-Log([string] $Message) {
    $line = "{0} (utc {1}) {2}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"),
        (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd HH:mm:ss'Z'"), $Message
    Add-Content -Path $Log -Value $line -Encoding ascii
    if ((Test-Path $Log) -and (Get-Item $Log).Length -gt 1000000) {
        $tail = Get-Content $Log -Tail 200
        Set-Content -Path $Log -Value $tail -Encoding ascii
    }
}

function Test-Url([string] $Url) {
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSec
        return ($response.StatusCode -eq 200 -and $response.Content -like '*"status":"ok"*')
    } catch {
        return $false
    }
}

$fails = 0
if (Test-Path $StateFile) {
    $raw = (Get-Content $StateFile | Select-Object -First 1).Trim()
    if ($raw -match '^\d+$') { $fails = [int]$raw }
}

$publicOk = Test-Url "$PublicUrl/live"
if ($publicOk) {
    if ($fails -gt 0) { Write-Log "public recovered after $fails failure(s): $PublicUrl" }
    if (-not $CheckOnly) { Set-Content -Path $StateFile -Value "0" -Encoding ascii }
    exit 0
}

$fails++
if (-not $CheckOnly) { Set-Content -Path $StateFile -Value "$fails" -Encoding ascii }
$localOk = Test-Url "http://127.0.0.1:$port/live"
Write-Log "public check failed ($fails): $PublicUrl/live local=$localOk"

if ($CheckOnly) { exit 1 }

if ($fails -ge $FailuresBeforeAction) {
    if ($localOk) {
        Write-Log "local healthy but public down: restarting the cloudflared service"
        Restart-Service -Name "cloudflared" -Force -ErrorAction SilentlyContinue
    } else {
        # Stop+Start: a plain /Run is a no-op while the task still shows
        # Running (a wedged keep-alive in a backoff sleep must be replaced).
        Write-Log "local down too: restarting the WordEndpoint task"
        Stop-ScheduledTask -TaskName WordEndpoint -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 3
        Start-ScheduledTask -TaskName WordEndpoint -ErrorAction SilentlyContinue
    }
    # Give the recovery attempt a full window before counting toward the next one.
    if (-not $CheckOnly) { Set-Content -Path $StateFile -Value "0" -Encoding ascii }
}
exit 1

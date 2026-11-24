# Apply source changes through the existing interactive logon task.
# Leaves Cloudflare running and verifies the real Word endpoints afterwards.
param([switch]$SkipTests, [switch]$Benchmark)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'python-runtime.ps1')
$Python = Get-EndpointPython
$Serve = Join-Path $Root "serve.py"
Set-Location $Root
Write-Host "Selected Python: $Python"
if (-not $SkipTests) {
    & $Python -B -m unittest discover -s tests -t .
    if ($LASTEXITCODE -ne 0) { throw "Tests failed. The running service was left up." }
}
# Verify access before stopping anything.
$task = Get-ScheduledTask -TaskName "WordEndpoint" -ErrorAction Stop
$port = 8787
$secret = $null
foreach ($line in Get-Content -LiteralPath (Join-Path $Root ".env")) {
    if ($line -match '^PORT=(\d+)$') { $port = [int]$Matches[1] }
    if ($line -match '^WORD_API_TOKEN=(.+)$') { $secret = $Matches[1] }
}
if (-not $secret) { throw "No API token found. The running service was left up." }
Stop-ScheduledTask -TaskName $task.TaskName
Start-Sleep -Seconds 2
$pidFile = Join-Path $Root "logs\server.pid"
if (Test-Path -LiteralPath $pidFile) {
    $recorded = (Get-Content -LiteralPath $pidFile -Raw).Trim()
    if ($recorded -match '^\d+$') {
        $process = Get-CimInstance Win32_Process -Filter "ProcessId=$recorded"
        if ($process -and $process.Name -eq "python.exe" -and $process.CommandLine -like "*$Serve*") {
            & taskkill.exe /F /T /PID $recorded | Out-Null
            if ($LASTEXITCODE -ne 0) { throw "Could not stop the recorded server." }
        }
    }
}
Enable-ScheduledTask -TaskName $task.TaskName | Out-Null
Start-ScheduledTask -TaskName $task.TaskName
$ready = $false
foreach ($attempt in 1..150) {
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:$port/ready" -UseBasicParsing -TimeoutSec 3
        $state = $response.Content | ConvertFrom-Json
        if ($state.status -eq "ok" -and $state.workers.compare.state -eq "ready" -and $state.workers.convert.state -eq "ready") {
            $ready = $true
            break
        }
    } catch { }
    Start-Sleep -Seconds 1
}
if (-not $ready) { throw "Word workers did not become ready. Check logs\server.log and worker logs." }
$previousToken = $env:WORD_API_TOKEN
$previousBase = $env:WORD_BASE_URL
try {
    $env:WORD_API_TOKEN = $secret
    $env:WORD_BASE_URL = "http://127.0.0.1:$port"
    & $Python -B (Join-Path $Root "tests\live_check.py")
    if ($LASTEXITCODE -ne 0) { throw "Live Word verification failed. The service is running; check logs." }
    if ($Benchmark) {
        & $Python -B (Join-Path $Root "scripts\benchmark-word.py")
        if ($LASTEXITCODE -ne 0) { throw "Benchmark failed. The service is running; check logs." }
    }
} finally {
    $env:WORD_API_TOKEN = $previousToken
    $env:WORD_BASE_URL = $previousBase
}
Write-Host "Updated service is ready; live comparison and PDF checks passed."

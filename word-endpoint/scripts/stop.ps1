$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

# Disable first so the babysitter cannot start a new server while we stop it.
schtasks.exe /Change /TN "WordEndpoint" /DISABLE 2>$null | Out-Null
schtasks.exe /End /TN "WordEndpoint" 2>$null | Out-Null
Start-Sleep -Seconds 2

. (Join-Path $PSScriptRoot "process-hold.ps1")

# Windows reuses a pid once its process is gone, so the recorded process is
# one matching $match ($name, when given, is its executable's name) that
# already existed when the record was written: the server writes server.pid
# when it starts, and Start-Tunnel writes tunnel.pid just after cloudflared
# started. A process with that pid created later took the number over. The
# hold (process-hold.ps1) keeps the number on the process checked here until
# taskkill has stopped it.
function Stop-Recorded($pidFile, $match, $name) {
    if (-not (Test-Path -LiteralPath $pidFile -PathType Leaf)) { return }
    $written = (Get-Item -LiteralPath $pidFile).LastWriteTime
    $procId = "$(Get-Content -LiteralPath $pidFile | Select-Object -First 1)".Trim()
    if ($procId -notmatch '^\d+$') { return }
    $hold = Open-ProcessHold $procId
    try {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$procId" -ErrorAction SilentlyContinue
        if ($null -eq $proc) {
            Remove-Item $pidFile -ErrorAction SilentlyContinue
            return
        }
        if ($proc.CommandLine -notlike "*$match*" -or ($name -and $proc.Name -ne $name) -or
                -not $proc.CreationDate -or $proc.CreationDate -gt $written) {
            Write-Host "Refusing to stop pid $procId because it is not the $match that was recorded"
            return
        }
        if (-not $hold) {
            # It is the recorded process and it is still running: as with a
            # failed taskkill, keep the record and leave Word and the job
            # folders alone.
            throw "Could not stop $match ($procId): it could not be opened to keep its number until it is stopped"
        }
        & taskkill.exe /F /T /PID $procId | Out-Null
        if ($LASTEXITCODE -ne 0 -and (Get-CimInstance Win32_Process -Filter "ProcessId=$procId" -ErrorAction SilentlyContinue)) {
            # Keep the record and stop here: cleaning up Word and the job folders
            # under a server that is still running would break its jobs.
            throw "Could not stop $match ($procId): taskkill exit $LASTEXITCODE"
        }
        Remove-Item $pidFile -ErrorAction SilentlyContinue
        Write-Host "Stopped $match ($procId)"
    } finally {
        Close-ProcessHold $hold
    }
}

Stop-Recorded (Join-Path $Root "logs\server.pid") "serve.py"
Stop-Recorded (Join-Path $Root "logs\tunnel.pid") "cloudflared" "cloudflared.exe"

$Work = Join-Path $Root "work"

. (Join-Path $PSScriptRoot "word-pid.ps1")

function Stop-OurWord($pidFile) {
    $word = Get-RecordedWord $pidFile
    if ($word -and $word.Unheld) {
        # Our Word, still running: keep its record (and its job folder) for the next stop.
        throw "Could not stop WINWORD $($word.ProcessId): $($word.Reason); kept $pidFile"
    }
    if ($word -and $word.Foreign) {
        Write-Host "Left pid $($word.ProcessId) ($($word.Name)) running: $($word.Reason)"
    } elseif ($word) {
        try {
            Stop-Process -Id $word.ProcessId -Force
            # Stop-Process only starts the termination; the job folder is
            # deleted next, so wait until Word has let go of it.
            if (-not (Wait-ProcessHoldExit $word.Hold 10)) {
                throw "Could not stop WINWORD $($word.ProcessId): still running 10 s after Stop-Process; kept $pidFile"
            }
        } finally { Close-ProcessHold $word.Hold }
        Write-Host "Stopped WINWORD $($word.ProcessId)"
    }
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

foreach ($name in @("compare.word.pid", "convert.word.pid")) {
    Stop-OurWord (Join-Path $Work $name)
}
Get-ChildItem $Work -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^[0-9a-f]{32}$' } | ForEach-Object {
    Stop-OurWord (Join-Path $_.FullName "word.pid")
    Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
}

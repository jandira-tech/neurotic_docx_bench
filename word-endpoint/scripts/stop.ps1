$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

# Disable first so the babysitter cannot start a new server while we stop it.
schtasks.exe /Change /TN "WordEndpoint" /DISABLE 2>$null | Out-Null
schtasks.exe /End /TN "WordEndpoint" 2>$null | Out-Null
Start-Sleep -Seconds 2

function Stop-Recorded($pidFile, $match) {
    if (-not (Test-Path $pidFile)) { return }
    $procId = (Get-Content $pidFile | Select-Object -First 1).Trim()
    if ($procId -notmatch '^\d+$') { return }
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$procId" -ErrorAction SilentlyContinue
    if ($null -eq $proc) {
        Remove-Item $pidFile -ErrorAction SilentlyContinue
        return
    }
    if ($proc.CommandLine -notlike "*$match*") {
        Write-Host "Refusing to stop pid $procId because it is not $match"
        return
    }
    & taskkill.exe /F /T /PID $procId | Out-Null
    Remove-Item $pidFile -ErrorAction SilentlyContinue
    Write-Host "Stopped $match ($procId)"
}

Stop-Recorded (Join-Path $Root "logs\server.pid") "serve.py"
Stop-Recorded (Join-Path $Root "logs\tunnel.pid") "cloudflared"

$Work = Join-Path $Root "work"

function Stop-OurWord($pidFile) {
    if (-not (Test-Path $pidFile)) { return }
    $wordPid = (Get-Content $pidFile | Select-Object -First 1).Trim()
    if ($wordPid -match '^\d+$') {
        $word = Get-Process -Id $wordPid -ErrorAction SilentlyContinue
        if ($word -and $word.ProcessName -eq "WINWORD") {
            Stop-Process -Id $wordPid -Force
            Write-Host "Stopped WINWORD $wordPid"
        }
    }
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

foreach ($name in @("compare.word.pid", "convert.word.pid")) {
    Stop-OurWord (Join-Path $Work $name)
}
Get-ChildItem $Work -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^[0-9a-f]{32}$' } | ForEach-Object {
    $wordPidFile = Join-Path $_.FullName "word.pid"
    if (Test-Path $wordPidFile) {
        $wordPid = (Get-Content $wordPidFile | Select-Object -First 1).Trim()
        if ($wordPid -match '^\d+$') {
            $word = Get-Process -Id $wordPid -ErrorAction SilentlyContinue
            if ($word -and $word.ProcessName -eq "WINWORD") {
                Stop-Process -Id $wordPid -Force
                Write-Host "Stopped WINWORD $wordPid"
            }
        }
    }
    Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
}

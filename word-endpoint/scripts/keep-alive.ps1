# Keeps the loopback Word service running in this interactive desktop session.
# Task Scheduler launches this script. It is not a Windows service: Word cannot
# automate from Session 0. Closing the terminal that installed the task does
# not stop this process.

$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
New-Item -ItemType Directory -Force -Path (Join-Path $Root "logs"), (Join-Path $Root "work") | Out-Null

. (Join-Path $PSScriptRoot 'python-runtime.ps1')
$Python = Get-EndpointPython
$Serve = Join-Path $Root "serve.py"
$PidFile = Join-Path $Root "logs\server.pid"
$SupervisePid = Join-Path $Root "logs\supervise.pid"
$Log = Join-Path $Root "logs\supervise.log"
$env:PYTHONUNBUFFERED = "1"

$port = 8787
$envFile = Join-Path $Root ".env"
if (Test-Path $envFile) {
    foreach ($line in Get-Content $envFile) {
        if ($line -match '^PORT=(\d+)$') { $port = [int]$Matches[1] }
    }
}

function Write-Log([string] $Message) {
    $line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -Path $Log -Value $line -Encoding ascii
    if ((Test-Path $Log) -and (Get-Item $Log).Length -gt 1000000) {
        $tail = Get-Content $Log -Tail 200
        Set-Content -Path $Log -Value $tail -Encoding ascii
    }
}

function Test-Health {
    try {
        # Word workers recover independently. Restart the entire HTTP server
        # only if HTTP liveness fails, not during a lane's recovery.
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:$port/live" -UseBasicParsing -TimeoutSec 5
        return ($response.StatusCode -eq 200 -and $response.Content -like '*"status":"ok"*')
    } catch {
        return $false
    }
}

function Get-ServerPid {
    # The venv launcher spawns a child python that owns the port; the pid file
    # records the launcher. The process listening on the port is the server.
    try {
        $conn = Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort $port -State Listen -ErrorAction Stop |
            Select-Object -First 1
        if ($conn) {
            $listener = Get-CimInstance Win32_Process -Filter "ProcessId=$($conn.OwningProcess)" -ErrorAction SilentlyContinue
            if ($listener -and $listener.Name -eq "python.exe" -and $listener.CommandLine -notlike "*keep-alive*") {
                return [int]$conn.OwningProcess
            }
        }
    } catch { }
    if (-not (Test-Path $PidFile)) { return $null }
    $procId = (Get-Content $PidFile | Select-Object -First 1).Trim()
    if ($procId -notmatch '^\d+$') { return $null }
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$procId" -ErrorAction SilentlyContinue
    if ($null -eq $proc) { return $null }
    if ($proc.Name -ne "python.exe" -or $proc.CommandLine -notlike "*serve.py*") { return $null }
    return [int]$procId
}

. (Join-Path $PSScriptRoot "word-pid.ps1")

# $false when the record names our Word, still running, which could not be
# held to stop it: the record (and the job folder holding it) stays.
function Stop-OurWord([string] $Path) {
    $word = Get-RecordedWord $Path
    if ($word -and $word.Unheld) {
        Write-Log "could not stop WINWORD $($word.ProcessId): $($word.Reason); kept $Path"
        return $false
    }
    if ($word -and $word.Foreign) {
        Write-Log "left pid $($word.ProcessId) ($($word.Name), started $($word.CreationDate.ToString('o'))) running: $($word.Reason) (recorded at $($word.Written.ToString('o')))"
    } elseif ($word) {
        try { Stop-Process -Id $word.ProcessId -Force -ErrorAction SilentlyContinue } finally { Close-ProcessHold $word.Hold }
        Write-Log "stopped WINWORD $($word.ProcessId)"
    }
    Remove-Item $Path -Force -ErrorAction SilentlyContinue
    return $true
}

function Stop-AllServers {
    $procs = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like "*$Serve*" }
    foreach ($proc in $procs) {
        # The list was read before the hold (process-hold.ps1), so the pid is
        # this server only if, held, it still names the process listed.
        $hold = Open-ProcessHold "$($proc.ProcessId)"
        try {
            $now = Get-CimInstance Win32_Process -Filter "ProcessId=$($proc.ProcessId)" -ErrorAction SilentlyContinue
            if (-not $now -or $now.CreationDate -ne $proc.CreationDate -or $now.CommandLine -ne $proc.CommandLine) { continue }
            if (-not $hold) {
                Write-Log "could not stop serve.py $($proc.ProcessId): it could not be opened to keep its number until it is stopped"
                continue
            }
            & taskkill.exe /F /T /PID $proc.ProcessId | Out-Null
            Write-Log "stopped serve.py $($proc.ProcessId)"
        } finally {
            Close-ProcessHold $hold
        }
    }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    $work = Join-Path $Root "work"
    foreach ($name in @("compare.word.pid", "convert.word.pid")) {
        [void](Stop-OurWord (Join-Path $work $name))
    }
    Get-ChildItem $work -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match '^[0-9a-f]{32}$' } |
        ForEach-Object {
            if (Stop-OurWord (Join-Path $_.FullName "word.pid")) {
                Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
            }
        }
    Start-Sleep -Seconds 1
}

function Start-Server {
    $outLog = Join-Path $Root "logs\server.out.log"
    $errLog = Join-Path $Root "logs\server.err.log"
    for ($try = 1; $try -le 3; $try++) {
        try {
            $proc = Start-Process -FilePath $Python -ArgumentList "`"$Serve`"" -WorkingDirectory $Root -WindowStyle Hidden -RedirectStandardOutput $outLog -RedirectStandardError $errLog -PassThru
            Set-Content -Path $PidFile -Value $proc.Id -Encoding ascii
            Write-Log "started serve.py $($proc.Id) python=$Python"
            return
        } catch {
            Write-Log "start failed try $try $($_.Exception.Message)"
            Start-Sleep -Seconds 2
        }
    }
}

function Wait-Health([int] $Seconds) {
    foreach ($i in 1..$Seconds) {
        if (Test-Health) { return $true }
        Start-Sleep -Seconds 1
    }
    return $false
}

function Test-OtherKeepAlive {
    if (-not (Test-Path $SupervisePid)) { return $false }
    $old = (Get-Content $SupervisePid | Select-Object -First 1).Trim()
    if ($old -notmatch '^\d+$' -or [int]$old -eq $PID) { return $false }
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$old" -ErrorAction SilentlyContinue
    return ($null -ne $proc -and $proc.CommandLine -like "*keep-alive.ps1*")
}

if (Test-OtherKeepAlive) {
    Write-Log "keep-alive already running"
    exit 0
}
Set-Content -Path $SupervisePid -Value $PID -Encoding ascii

$parentId = (Get-CimInstance Win32_Process -Filter "ProcessId=$PID").ParentProcessId
$parent = Get-CimInstance Win32_Process -Filter "ProcessId=$parentId" -ErrorAction SilentlyContinue
$parentName = if ($parent) { $parent.Name } else { "unknown" }
Write-Log "keep-alive pid $PID session $((Get-Process -Id $PID).SessionId) parent $parentName $parentId"

Stop-AllServers
Start-Server
if (Wait-Health 60) {
    Write-Log "health ok pid=$(Get-ServerPid)"
} else {
    Write-Log "initial health failed"
}

$misses = 0
$restartStreak = 0
$lastRestart = [datetime]::MinValue
$nextBeat = (Get-Date).AddMinutes(10)
while ($true) {
    try {
        $procId = Get-ServerPid
        $healthy = Test-Health
        if ($healthy -and $procId) {
            $misses = 0
            $restartStreak = 0
        } else {
            $misses++
            if (-not $procId -or $misses -ge 3) {
                $skipRestart = $false
                $sinceRestart = ((Get-Date) - $lastRestart).TotalSeconds
                if ($sinceRestart -lt 300 -and $restartStreak -gt 0) {
                    $backoff = [Math]::Min(120, 30 * [Math]::Pow(2, $restartStreak))
                    Write-Log "restart backoff ${backoff}s (streak $restartStreak, last restart ${sinceRestart}s ago)"
                    Start-Sleep -Seconds $backoff
                    # Someone may have healed the service during the sleep
                    # (manual fix or watchdog); never kill a healthy server.
                    if ((Test-Health) -and (Get-ServerPid)) {
                        Write-Log "service recovered during backoff, skipping restart"
                        $skipRestart = $true
                        $misses = 0
                        $restartStreak = 0
                    }
                }
                if (-not $skipRestart) {
                    $lastRestart = Get-Date
                    $restartStreak++
                    Write-Log "restarting healthy=$healthy pid=$procId misses=$misses streak=$restartStreak"
                    Stop-AllServers
                    Start-Server
                    if (Wait-Health 60) {
                        Write-Log "health ok pid=$(Get-ServerPid)"
                        $misses = 0
                    } else {
                        Write-Log "health failed after restart"
                    }
                }
            }
        }
        if ((Get-Date) -ge $nextBeat) {
            $utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd HH:mm:ss'Z'")
            Write-Log "heartbeat pid=$(Get-ServerPid) healthy=$healthy utc=$utc"
            $nextBeat = (Get-Date).AddMinutes(10)
        }
    } catch {
        Write-Log "loop error $($_.Exception.Message)"
    }
    Start-Sleep -Seconds 15
}

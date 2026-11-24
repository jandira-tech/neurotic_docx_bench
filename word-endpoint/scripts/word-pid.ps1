# Which Word a worker's PID file names. Windows reuses a pid after a crash or
# reboot, and a stale file can outlive its Word, so the number alone is not
# enough to force-stop a process. The worker writes the file just after COM
# started Word, so ours is an automation Word (-Embedding) that already
# existed when the file was written.

function Get-RecordedWord([string] $PidFile) {
    if (-not (Test-Path -LiteralPath $PidFile)) { return $null }
    $written = (Get-Item -LiteralPath $PidFile).LastWriteTime
    $wordPid = (Get-Content -LiteralPath $PidFile | Select-Object -First 1).Trim()
    if ($wordPid -notmatch '^\d+$') { return $null }
    $word = Get-CimInstance Win32_Process -Filter "ProcessId=$wordPid" -ErrorAction SilentlyContinue
    if ($null -eq $word) { return $null }
    if ($word.Name -eq "WINWORD.EXE" -and $word.CommandLine -match '(?i)[-/]Embedding\b' -and $word.CreationDate -le $written) {
        return $word
    }
    return [pscustomobject]@{ Foreign = $true; ProcessId = $word.ProcessId; Name = $word.Name; CreationDate = $word.CreationDate; Written = $written }
}

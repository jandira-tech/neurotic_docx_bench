# Which Word a worker's PID file names. Windows reuses a pid after a crash or
# reboot, and a stale file can outlive its Word, so the number alone is not
# enough to force-stop a process. The worker writes the file just after COM
# started Word, so ours is an automation Word (-Embedding) that already
# existed when the file was written. Every caller stops the Word this returns,
# so it comes with a hold (process-hold.ps1) on its pid, taken before the
# check: the caller stops it by number and then closes .Hold. Ours but not
# holdable comes back with .Unheld: it is still running and still ours, so the
# caller must not stop it and must keep its record. A process query that fails
# throws (with the hold closed): a Word that cannot be looked up is not a Word
# that is gone, and a caller that took it for one would delete its record.

. (Join-Path $PSScriptRoot "process-hold.ps1")

function Get-RecordedWord([string] $PidFile) {
    if (-not (Test-Path -LiteralPath $PidFile)) { return $null }
    $written = (Get-Item -LiteralPath $PidFile).LastWriteTime
    $wordPid = (Get-Content -LiteralPath $PidFile | Select-Object -First 1).Trim()
    if ($wordPid -notmatch '^\d+$') { return $null }
    $hold = Open-ProcessHold $wordPid
    try {
        $word = Get-CimInstance Win32_Process -Filter "ProcessId=$wordPid" -ErrorAction Stop
        if ($null -eq $word) {
            Close-ProcessHold $hold
            return $null
        }
        $ours = $word.Name -eq "WINWORD.EXE" -and $word.CommandLine -match '(?i)[-/]Embedding\b' -and $word.CreationDate -le $written
        if ($ours -and $hold) {
            $word | Add-Member -NotePropertyName Hold -NotePropertyValue $hold -Force
            return $word
        }
    } catch {
        # The caller never got the handle, so it is closed here.
        Close-ProcessHold $hold
        throw
    }
    Close-ProcessHold $hold
    $found = @{ ProcessId = $word.ProcessId; Name = $word.Name; CreationDate = $word.CreationDate; Written = $written }
    if ($ours) {
        return [pscustomobject]($found + @{ Unheld = $true; Reason = "it could not be opened to keep its number until it is stopped" })
    }
    return [pscustomobject]($found + @{ Foreign = $true; Reason = "not the Word $PidFile recorded" })
}

# The tunnel start.ps1 launches itself when cloudflared is not a Windows service
# (a quick tunnel, or a named tunnel from CLOUDFLARE_TUNNEL_TOKEN). The public
# watchdog uses the same functions to replace a tunnel process that went dark.

. (Join-Path $PSScriptRoot "process-hold.ps1")

# Windows reuses a pid once its process is gone, and the record outlives its
# tunnel, so the number alone does not say which process it is. Start-Tunnel
# writes the record just after cloudflared started: ours is a cloudflared.exe
# created before the record was written. Anything with that pid created later
# took the number over. With -Hold, a caller about to stop the tunnel gets it
# with .Hold, a handle (process-hold.ps1) taken before the check that keeps the
# number on this process until the caller closes it; .Hold is $null when the
# process could not be opened.
function Get-RecordedTunnel([string] $Root, [switch] $Hold) {
    $pidFile = Join-Path $Root "logs\tunnel.pid"
    if (-not (Test-Path -LiteralPath $pidFile -PathType Leaf)) { return $null }
    $written = (Get-Item -LiteralPath $pidFile).LastWriteTime
    $old = "$(Get-Content -LiteralPath $pidFile | Select-Object -First 1)".Trim()
    if ($old -notmatch '^\d+$') { return $null }
    $handle = if ($Hold) { Open-ProcessHold $old } else { $null }
    try {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$old" -ErrorAction SilentlyContinue
        if ($proc -and $proc.Name -eq "cloudflared.exe" -and $proc.CreationDate -and $proc.CreationDate -le $written) {
            if ($Hold) { $proc | Add-Member -NotePropertyName Hold -NotePropertyValue $handle -Force }
            return $proc
        }
    } catch {
        # The caller never got the handle, so it is closed here.
        Close-ProcessHold $handle
        throw
    }
    Close-ProcessHold $handle
    return $null
}

# The named tunnel's token: .env's CLOUDFLARE_TUNNEL_TOKEN, else this process's
# environment. start.ps1 and the public watchdog both read it here; the
# watchdog runs as SYSTEM, so a variable only in an administrator's user
# environment is invisible to it: keep the token in .env or a machine variable.
function Get-TunnelToken($DotEnv) {
    if ($DotEnv -and $DotEnv['CLOUDFLARE_TUNNEL_TOKEN']) { return $DotEnv['CLOUDFLARE_TUNNEL_TOKEN'] }
    return $env:CLOUDFLARE_TUNNEL_TOKEN
}

function Start-Tunnel([string] $Root, [string] $Port, [string] $Token) {
    $cloud = Join-Path $Root ".tools\cloudflared.exe"
    $saved = $env:TUNNEL_TOKEN
    try {
        if ($Token) {
            # cloudflared reads TUNNEL_TOKEN from its environment. On the command
            # line the token would show in process listings and in
            # process-creation audit logs.
            $env:TUNNEL_TOKEN = $Token
            $tunnelArgs = @("tunnel", "--no-autoupdate", "run")
        } else {
            Remove-Item Env:TUNNEL_TOKEN -ErrorAction SilentlyContinue
            $tunnelArgs = @("tunnel", "--no-autoupdate", "--url", "http://127.0.0.1:$Port")
        }
        Remove-Item (Join-Path $Root "logs\tunnel.log"), (Join-Path $Root "logs\tunnel.err.log") -ErrorAction SilentlyContinue
        # Stop on errors here even when the caller runs with "Continue" (the public
        # watchdog does): a launch that failed must not leave an empty pid record.
        $proc = Start-Process -FilePath $cloud -ArgumentList $tunnelArgs -WorkingDirectory $Root -WindowStyle Hidden -RedirectStandardOutput (Join-Path $Root "logs\tunnel.log") -RedirectStandardError (Join-Path $Root "logs\tunnel.err.log") -PassThru -ErrorAction Stop
        if (-not $proc -or -not $proc.Id) { throw "cloudflared did not start" }
        try {
            Set-Content -Path (Join-Path $Root "logs\tunnel.pid") -Value $proc.Id -Encoding ascii -ErrorAction Stop
        } catch {
            # Without its record no later run finds this tunnel to replace or
            # stop it, and the next start would run a second one beside it.
            $reason = $_.Exception.Message
            & taskkill.exe /F /T /PID $proc.Id | Out-Null
            $code = $LASTEXITCODE
            if ($code -eq 0) { throw "Could not record tunnel process $($proc.Id) ($reason); stopped it." }
            if (Get-Process -Id $proc.Id -ErrorAction SilentlyContinue) {
                throw "Could not record tunnel process $($proc.Id) ($reason), and could not stop it (taskkill exit $code): stop it by hand."
            }
            # taskkill found nothing to stop: cloudflared exited by itself, so
            # its own failure (tunnel.err.log) is the one to look at.
            throw "Could not record tunnel process $($proc.Id) ($reason); it had already exited (see logs\tunnel.err.log)."
        }
        return $proc
    } finally {
        if ($null -eq $saved) { Remove-Item Env:TUNNEL_TOKEN -ErrorAction SilentlyContinue } else { $env:TUNNEL_TOKEN = $saved }
    }
}

# What the public watchdog does when the local service answers but the public
# URL does not. Returns the lines to log.
function Restore-Tunnel([string] $Root, [string] $Port, [string] $Token) {
    if (Get-Service -Name "cloudflared" -ErrorAction SilentlyContinue) {
        "local healthy but public down: restarting the cloudflared service"
        try { Restart-Service -Name "cloudflared" -Force -ErrorAction Stop }
        catch { "cloudflared service restart failed: $($_.Exception.Message)" }
        return
    }
    $recorded = Get-RecordedTunnel $Root -Hold
    try {
        if (-not $Token) {
            if ($recorded) {
                "local healthy but public down on a quick tunnel: a new one gets a new URL, so run scripts\start.ps1 to publish it"
            } else {
                "local healthy but public down, and there is no cloudflared service or tunnel token to start one with"
            }
            return
        }
        # A named tunnel (token): start.ps1 ran it as a process. Replace a dark one;
        # start one when none is running, which also retries a replacement that died.
        if ($recorded) {
            if (-not $recorded.Hold) {
                "could not open tunnel process $($recorded.ProcessId) to keep its number until it is stopped; not starting a second one"
                return
            }
            "local healthy but public down: replacing tunnel process $($recorded.ProcessId)"
            & taskkill.exe /F /T /PID $recorded.ProcessId | Out-Null
            $code = $LASTEXITCODE
            if ($code -ne 0 -and (Get-Process -Id $recorded.ProcessId -ErrorAction SilentlyContinue)) {
                "could not stop tunnel process $($recorded.ProcessId) (taskkill exit $code); not starting a second one"
                return
            }
        } else {
            "local healthy but public down and no tunnel process is running: starting one"
        }
    } finally {
        if ($recorded) { Close-ProcessHold $recorded.Hold }
    }
    try {
        $proc = Start-Tunnel $Root $Port $Token
        "started tunnel process $($proc.Id)"
    } catch {
        "could not start the tunnel: $($_.Exception.Message)"
    }
}

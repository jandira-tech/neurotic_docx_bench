# The tunnel start.ps1 launches itself when cloudflared is not a Windows service
# (a quick tunnel, or a named tunnel from CLOUDFLARE_TUNNEL_TOKEN). The public
# watchdog uses the same functions to replace a tunnel process that went dark.

function Get-RecordedTunnel([string] $Root) {
    $pidFile = Join-Path $Root "logs\tunnel.pid"
    if (-not (Test-Path $pidFile)) { return $null }
    $old = (Get-Content $pidFile | Select-Object -First 1).Trim()
    if ($old -notmatch '^\d+$') { return $null }
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$old" -ErrorAction SilentlyContinue
    if ($proc -and $proc.CommandLine -like "*cloudflared*") { return $proc }
    return $null
}

function Start-Tunnel([string] $Root, [string] $Port, [string] $Token) {
    $cloud = Join-Path $Root ".tools\cloudflared.exe"
    if ($Token) {
        $tunnelArgs = @("tunnel", "--no-autoupdate", "run", "--token", $Token)
    } else {
        $tunnelArgs = @("tunnel", "--no-autoupdate", "--url", "http://127.0.0.1:$Port")
    }
    Remove-Item (Join-Path $Root "logs\tunnel.log"), (Join-Path $Root "logs\tunnel.err.log") -ErrorAction SilentlyContinue
    $proc = Start-Process -FilePath $cloud -ArgumentList $tunnelArgs -WorkingDirectory $Root -WindowStyle Hidden -RedirectStandardOutput (Join-Path $Root "logs\tunnel.log") -RedirectStandardError (Join-Path $Root "logs\tunnel.err.log") -PassThru
    Set-Content -Path (Join-Path $Root "logs\tunnel.pid") -Value $proc.Id -Encoding ascii
    return $proc
}

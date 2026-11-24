# Dependency-free regression test for the public watchdog's tunnel recovery
# (scripts\tunnel.ps1, Restore-Tunnel). Every cmdlet that would touch a service,
# a process or cloudflared is a local stub; nothing on the machine changes.
param([string]$Script = (Join-Path (Split-Path -Parent $PSScriptRoot) 'scripts\tunnel.ps1'))
$ErrorActionPreference = 'Stop'
. $Script
$root = Join-Path ([IO.Path]::GetTempPath()) ("tunnel-check-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path (Join-Path $root 'logs') -Force | Out-Null
$pidFile = Join-Path $root 'logs\tunnel.pid'

$script:service = $false; $script:running = $null; $script:launchFails = $false
$script:killExit = 0; $script:aliveAfterKill = $false
$script:launched = 0; $script:killed = 0; $script:restarted = 0
function Get-Service { [CmdletBinding()] param($Name) if ($script:service) { [pscustomobject]@{ Name = $Name } } }
function Restart-Service { [CmdletBinding()] param($Name, [switch]$Force) $script:restarted++ }
function Get-CimInstance { [CmdletBinding()] param($ClassName, $Filter) $script:running }
function Get-Process { [CmdletBinding()] param($Id) if ($script:aliveAfterKill) { [pscustomobject]@{ Id = $Id } } }
function taskkill.exe { $script:killed++; $script:killedPid = $args[-1]; $global:LASTEXITCODE = $script:killExit }
function Start-Process {
    [CmdletBinding()]
    param($FilePath, $ArgumentList, $WorkingDirectory, $WindowStyle, $RedirectStandardOutput, $RedirectStandardError, [switch]$PassThru)
    if ($script:launchFails) { Write-Error 'cloudflared could not be launched (stub)'; return }
    $script:launched++
    $script:launchArgs = @($ArgumentList); $script:launchEnv = $env:TUNNEL_TOKEN
    [pscustomobject]@{ Id = 4242 }
}
function Reset { param([switch]$Service, $Running, [switch]$LaunchFails, [int]$KillExit = 0, [switch]$AliveAfterKill)
    $script:service = [bool]$Service; $script:running = $Running; $script:launchFails = [bool]$LaunchFails
    $script:killExit = $KillExit; $script:aliveAfterKill = [bool]$AliveAfterKill
    $script:launched = 0; $script:killed = 0; $script:killedPid = $null; $script:restarted = 0; $script:launchArgs = @(); $script:launchEnv = $null
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    if ($Running) { Set-Content -Path $pidFile -Value $Running.ProcessId -Encoding ascii }
}
# The watchdog runs with "Continue", so a launch error is not terminating unless the code makes it so.
function Recover { $ErrorActionPreference = 'Continue'; @(Restore-Tunnel $root '8787' $args[0] 2>$null) }
$failures = @()
try {
    # Created before Reset writes its record, as Start-Tunnel's own tunnel is.
    $tunnel = [pscustomobject]@{ ProcessId = 777; Name = 'cloudflared.exe'; CreationDate = (Get-Date).AddMinutes(-5); CommandLine = 'cloudflared.exe tunnel --no-autoupdate run' }

    # 1. Token tunnel, no service, nothing running (a replacement died): start one.
    #    The token reaches cloudflared through TUNNEL_TOKEN, never its command
    #    line, and this process's environment is left as it was.
    Reset
    $lines = Recover 'tok-secret-7'
    if ($script:launched -ne 1) { $failures += "1: nothing running was not restarted: $($lines -join ' | ')" }
    if ((Get-Content $pidFile -ErrorAction SilentlyContinue) -ne '4242') { $failures += "1: pid file does not hold the new tunnel" }
    if (($script:launchArgs -join ' ') -match 'tok-secret-7') { $failures += "1: the token is on the command line: $($script:launchArgs -join ' ')" }
    if ($script:launchEnv -ne 'tok-secret-7') { $failures += "1: cloudflared did not get TUNNEL_TOKEN" }
    if ($null -ne $env:TUNNEL_TOKEN) { $failures += "1: TUNNEL_TOKEN was left in this process" }

    # 1b. A quick tunnel never inherits a TUNNEL_TOKEN this process happens to hold.
    Reset
    $env:TUNNEL_TOKEN = 'stale'
    try { Start-Tunnel $root '8787' '' | Out-Null } finally { $leftover = $env:TUNNEL_TOKEN; Remove-Item Env:TUNNEL_TOKEN -ErrorAction SilentlyContinue }
    if ($script:launchEnv) { $failures += "1b: a quick tunnel launched with TUNNEL_TOKEN set" }
    if (($script:launchArgs -join ' ') -notmatch '--url http://127.0.0.1:8787') { $failures += "1b: quick tunnel args: $($script:launchArgs -join ' ')" }
    if ($leftover -ne 'stale') { $failures += "1b: the caller's TUNNEL_TOKEN was not restored" }

    # 1c. Where the token comes from: .env first, then the environment.
    $env:CLOUDFLARE_TUNNEL_TOKEN = 'from-env'
    try {
        if ((Get-TunnelToken ([ordered]@{ CLOUDFLARE_TUNNEL_TOKEN = 'from-file' })) -ne 'from-file') { $failures += "1c: .env's token did not win" }
        if ((Get-TunnelToken ([ordered]@{})) -ne 'from-env') { $failures += "1c: the environment's token was not used" }
    } finally { Remove-Item Env:CLOUDFLARE_TUNNEL_TOKEN -ErrorAction SilentlyContinue }

    # 2. The launch fails: reported as a failure, never as started, and no empty pid record.
    Reset -LaunchFails
    $lines = Recover 'tok'
    if (-not ($lines -match 'could not start')) { $failures += "2: launch failure not reported: $($lines -join ' | ')" }
    if ($lines -match 'started tunnel') { $failures += "2: a failed launch was logged as started: $($lines -join ' | ')" }
    if (Test-Path $pidFile) { $failures += "2: a pid file was written for a launch that failed" }

    # 2b. Replacing a running tunnel whose new launch fails: not "started", and the
    #     pid record is not overwritten with an empty value.
    Reset -Running $tunnel -LaunchFails
    $lines = Recover 'tok'
    if ($lines -match 'started tunnel') { $failures += "2b: a failed launch was logged as started: $($lines -join ' | ')" }
    if (-not ($lines -match 'could not start')) { $failures += "2b: launch failure not reported: $($lines -join ' | ')" }
    if (-not "$(Get-Content $pidFile -ErrorAction SilentlyContinue)".Trim()) { $failures += "2b: the pid record was emptied" }

    # 2c. The launch works but its pid cannot be recorded (a read-only
    #     tunnel.pid): the new process is stopped, since nothing could find it
    #     later, and the launch is reported as failed.
    Reset
    Set-Content -Path $pidFile -Value '1' -Encoding ascii
    Set-ItemProperty -LiteralPath $pidFile -Name IsReadOnly -Value $true
    $lines = Recover 'tok'
    if ($script:launched -ne 1) { $failures += "2c: no launch to roll back (launched $($script:launched))" }
    if ("$($script:killedPid)" -ne '4242') { $failures += "2c: the unrecorded tunnel was left running: $($lines -join ' | ')" }
    if ($lines -match 'started tunnel') { $failures += "2c: an unrecorded launch was logged as started: $($lines -join ' | ')" }
    if (-not ($lines -match 'could not start')) { $failures += "2c: the failure was not reported: $($lines -join ' | ')" }
    if (-not ($lines -match 'stopped it')) { $failures += "2c: the rollback did not say it stopped the tunnel: $($lines -join ' | ')" }

    # 2d. As 2c, but cloudflared exited by itself (a bad token) before the
    #     rollback: taskkill finds nothing, and the message says so instead of
    #     claiming the rollback stopped it.
    Reset -KillExit 128
    Set-Content -Path $pidFile -Value '1' -Encoding ascii
    Set-ItemProperty -LiteralPath $pidFile -Name IsReadOnly -Value $true
    $lines = Recover 'tok'
    if ($lines -match 'stopped it') { $failures += "2d: a tunnel that had exited by itself was reported as stopped: $($lines -join ' | ')" }
    if (-not ($lines -match 'already exited')) { $failures += "2d: the tunnel's own exit was not reported: $($lines -join ' | ')" }
    if ($lines -match 'started tunnel') { $failures += "2d: an unrecorded launch was logged as started: $($lines -join ' | ')" }
    Set-ItemProperty -LiteralPath $pidFile -Name IsReadOnly -Value $false

    # 3. A recorded tunnel still running: replaced.
    Reset -Running $tunnel
    $lines = Recover 'tok'
    if ($script:killed -ne 1 -or $script:launched -ne 1) { $failures += "3: running tunnel not replaced (killed $($script:killed), launched $($script:launched))" }

    # 4. taskkill fails and the process is still there: no second tunnel beside it.
    Reset -Running $tunnel -KillExit 1 -AliveAfterKill
    $lines = Recover 'tok'
    if ($script:launched -ne 0) { $failures += "4: launched a second tunnel beside one that would not stop" }
    if (-not ($lines -match 'could not stop')) { $failures += "4: the failed stop was not reported: $($lines -join ' | ')" }

    # 5. A cloudflared service: restart it, launch nothing.
    Reset -Service
    $lines = Recover 'tok'
    if ($script:restarted -ne 1 -or $script:launched -ne 0) { $failures += "5: service not restarted alone (restarted $($script:restarted), launched $($script:launched))" }

    # 7. The recorded pid now belongs to another program whose command line
    #    happens to say cloudflared: Windows reused the number. It is not
    #    killed; the tunnel is gone, so a new one is started.
    Reset -Running $tunnel
    $script:running = [pscustomobject]@{ ProcessId = 777; Name = 'notepad.exe'; CreationDate = (Get-Date).AddMinutes(-5); CommandLine = 'notepad.exe C:\notes\cloudflared.txt' }
    $lines = Recover 'tok'
    if ($script:killed -ne 0) { $failures += "7: killed another program that took the tunnel's pid" }
    if ($script:launched -ne 1) { $failures += "7: no tunnel started in place of the gone one: $($lines -join ' | ')" }

    # 7b. A cloudflared.exe created after the record was written is a later
    #     process with the same pid, not the recorded tunnel.
    Reset -Running $tunnel
    $script:running = [pscustomobject]@{ ProcessId = 777; Name = 'cloudflared.exe'; CreationDate = (Get-Date).AddMinutes(5); CommandLine = 'cloudflared.exe tunnel run' }
    $lines = Recover 'tok'
    if ($script:killed -ne 0) { $failures += "7b: killed a cloudflared started after the record was written" }

    # 6. Quick tunnel (no token): never replaced here, since a new one gets a new URL.
    Reset -Running $tunnel
    $lines = Recover ''
    if ($script:launched -ne 0 -or $script:killed -ne 0) { $failures += "6: a quick tunnel was touched" }

} finally {
    Remove-Item $root -Recurse -Force -ErrorAction SilentlyContinue
}
if ($failures) { $failures | ForEach-Object { Write-Output "FAIL $_" }; exit 1 }
Write-Output 'tunnel recovery checks passed (13 cases)'

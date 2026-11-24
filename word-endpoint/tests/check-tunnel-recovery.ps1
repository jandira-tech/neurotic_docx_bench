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
function taskkill.exe { $script:killed++; $global:LASTEXITCODE = $script:killExit }
function Start-Process {
    [CmdletBinding()]
    param($FilePath, $ArgumentList, $WorkingDirectory, $WindowStyle, $RedirectStandardOutput, $RedirectStandardError, [switch]$PassThru)
    if ($script:launchFails) { Write-Error 'cloudflared could not be launched (stub)'; return }
    $script:launched++
    [pscustomobject]@{ Id = 4242 }
}
function Reset { param([switch]$Service, $Running, [switch]$LaunchFails, [int]$KillExit = 0, [switch]$AliveAfterKill)
    $script:service = [bool]$Service; $script:running = $Running; $script:launchFails = [bool]$LaunchFails
    $script:killExit = $KillExit; $script:aliveAfterKill = [bool]$AliveAfterKill
    $script:launched = 0; $script:killed = 0; $script:restarted = 0
    Remove-Item $pidFile -ErrorAction SilentlyContinue
    if ($Running) { Set-Content -Path $pidFile -Value $Running.ProcessId -Encoding ascii }
}
# The watchdog runs with "Continue", so a launch error is not terminating unless the code makes it so.
function Recover { $ErrorActionPreference = 'Continue'; @(Restore-Tunnel $root '8787' $args[0] 2>$null) }
$failures = @()
try {
    $tunnel = [pscustomobject]@{ ProcessId = 777; CommandLine = 'cloudflared.exe tunnel --no-autoupdate run --token x' }

    # 1. Token tunnel, no service, nothing running (a replacement died): start one.
    Reset
    $lines = Recover 'tok'
    if ($script:launched -ne 1) { $failures += "1: nothing running was not restarted: $($lines -join ' | ')" }
    if ((Get-Content $pidFile -ErrorAction SilentlyContinue) -ne '4242') { $failures += "1: pid file does not hold the new tunnel" }

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

    # 6. Quick tunnel (no token): never replaced here, since a new one gets a new URL.
    Reset -Running $tunnel
    $lines = Recover ''
    if ($script:launched -ne 0 -or $script:killed -ne 0) { $failures += "6: a quick tunnel was touched" }

} finally {
    Remove-Item $root -Recurse -Force -ErrorAction SilentlyContinue
}
if ($failures) { $failures | ForEach-Object { Write-Output "FAIL $_" }; exit 1 }
Write-Output 'tunnel recovery checks passed (7 cases)'

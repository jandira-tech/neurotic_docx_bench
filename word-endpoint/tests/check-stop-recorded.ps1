# Regression test for stop.ps1's Stop-Recorded, which force-stops the process a
# pid record names. stop.ps1 acts as soon as it runs, so this loads only that
# function from it (through the PowerShell parser) and stubs every command that
# would look at or stop a real process.
param([string]$Script = (Join-Path (Split-Path -Parent $PSScriptRoot) 'scripts\stop.ps1'))
$ErrorActionPreference = 'Stop'
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($Script, [ref]$null, [ref]$parseErrors)
if ($parseErrors) { throw "Could not parse ${Script}: $($parseErrors[0].Message)" }
$definition = $ast.Find({ param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Stop-Recorded' }, $true)
if (-not $definition) { throw "Stop-Recorded is not defined in $Script" }
. ([scriptblock]::Create($definition.Extent.Text))

$dir = Join-Path ([IO.Path]::GetTempPath()) ("stop-check-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $dir -Force | Out-Null
$pidFile = Join-Path $dir 'tunnel.pid'
$script:proc = $null; $script:killed = @(); $script:events = @(); $script:holdOpens = $true
$script:cimCalls = 0; $script:cimFailsAt = 0; $script:killExit = 0; $script:goneAfterKill = $false
# The hold (process-hold.ps1) is stubbed too; check-process-hold.ps1 checks the
# real one. Every step is logged, so the order can be checked.
function Open-ProcessHold { param($ProcId) $script:events += "hold $ProcId"; if ($script:holdOpens) { [IntPtr]101 } }
function Close-ProcessHold { param($Handle) if ($Handle) { $script:events += 'release' } }
# A query that fails writes an error, as Get-CimInstance does when WMI does not
# answer: -ErrorAction decides whether the caller sees it or an empty result.
function Get-CimInstance { [CmdletBinding()] param($ClassName, $Filter)
    $script:events += 'check'; $script:cimCalls++
    if ($script:cimCalls -eq $script:cimFailsAt) { Write-Error 'WMI is not answering'; return }
    $script:proc }
function taskkill.exe {
    $script:events += "kill $($args[-1])"; $script:killed += "$($args[-1])"
    if ($script:goneAfterKill) { $script:proc = $null }
    $global:LASTEXITCODE = $script:killExit }
function Write-Host { }
function Check([string] $Case, $Proc, [string] $Match, [string] $Name, [bool] $Stopped, [bool] $HoldOpens = $true, [bool] $Throws = $false,
        [int] $CimFailsAt = 0, [int] $KillExit = 0, [bool] $GoneAfterKill = $false, [string] $Events = 'hold 777,check,kill 777,release') {
    Set-Content -Path $pidFile -Value '777' -Encoding ascii
    $script:proc = $Proc; $script:killed = @(); $script:events = @(); $script:holdOpens = $HoldOpens
    $script:cimCalls = 0; $script:cimFailsAt = $CimFailsAt; $script:killExit = $KillExit; $script:goneAfterKill = $GoneAfterKill
    $threw = $false
    try { Stop-Recorded $pidFile $Match $Name } catch { $threw = $true }
    if ($Throws -and -not $threw) { $script:failures += "${Case}: returned normally, so stop.ps1 would go on to clean up under a process still running" }
    if (-not $Throws -and $threw) { $script:failures += "${Case}: threw" }
    if ($Throws -and -not (Test-Path -LiteralPath $pidFile)) { $script:failures += "${Case}: the record of a process still running was deleted" }
    if (-not $Throws -and $Stopped -and (Test-Path -LiteralPath $pidFile)) { $script:failures += "${Case}: the record of a stopped process was kept" }
    if ($Stopped -and $script:killed -notcontains '777') { $script:failures += "${Case}: the recorded process was not stopped" }
    if (-not $Stopped -and $script:killed) { $script:failures += "${Case}: stopped pid $($script:killed -join ',') that is not the recorded process" }
    # The pid is held from before the identity check until after the stop.
    if ($Stopped -and ($script:events -join ',') -ne $Events) { $script:failures += "${Case}: hold, check, stop and release ran as $($script:events -join ', ')" }
    if ($HoldOpens -and $script:events -contains 'hold 777' -and $script:events -notcontains 'release') { $script:failures += "${Case}: the hold was left open: $($script:events -join ', ')" }
}
$script:failures = @()
$before = (Get-Date).AddMinutes(-5); $after = (Get-Date).AddMinutes(5)
try {
    # 1. The recorded tunnel, started before its record was written: stopped.
    Check '1' ([pscustomobject]@{ ProcessId = 777; Name = 'cloudflared.exe'; CreationDate = $before; CommandLine = 'cloudflared.exe tunnel run' }) 'cloudflared' 'cloudflared.exe' $true
    # 2. Another program took the pid and its command line says cloudflared.
    Check '2' ([pscustomobject]@{ ProcessId = 777; Name = 'notepad.exe'; CreationDate = $before; CommandLine = 'notepad.exe C:\notes\cloudflared.txt' }) 'cloudflared' 'cloudflared.exe' $false
    # 3. A cloudflared.exe created after the record: a later process, same pid.
    Check '3' ([pscustomobject]@{ ProcessId = 777; Name = 'cloudflared.exe'; CreationDate = $after; CommandLine = 'cloudflared.exe tunnel run' }) 'cloudflared' 'cloudflared.exe' $false
    # 4. The server's record: a serve.py started after the record is not it.
    Check '4' ([pscustomobject]@{ ProcessId = 777; Name = 'python.exe'; CreationDate = $after; CommandLine = 'python.exe serve.py' }) 'serve.py' $null $false
    # 5. The server that wrote its own record: stopped.
    Check '5' ([pscustomobject]@{ ProcessId = 777; Name = 'python.exe'; CreationDate = $before; CommandLine = 'python.exe serve.py' }) 'serve.py' $null $true
    # 6. The recorded tunnel, but its pid cannot be held (opening it is
    #    refused): not stopped, since nothing would keep the number on it, and
    #    stop.ps1 stops there with the record kept, as for a failed taskkill.
    Check '6' ([pscustomobject]@{ ProcessId = 777; Name = 'cloudflared.exe'; CreationDate = $before; CommandLine = 'cloudflared.exe tunnel run' }) 'cloudflared' 'cloudflared.exe' $false $false $true
    $tunnel = [pscustomobject]@{ ProcessId = 777; Name = 'cloudflared.exe'; CreationDate = $before; CommandLine = 'cloudflared.exe tunnel run' }
    # 7. The query of the recorded pid fails: that says nothing about whether
    #    the process runs, so stop.ps1 stops there with the record kept, and
    #    nothing is stopped.
    Check '7' $tunnel 'cloudflared' 'cloudflared.exe' $false -Throws $true -CimFailsAt 1
    # 8. taskkill fails and the query that would say whether the process is
    #    gone fails too: counted as still running.
    Check '8' $tunnel 'cloudflared' 'cloudflared.exe' $true -Throws $true -CimFailsAt 2 -KillExit 1 -Events 'hold 777,check,kill 777,check,release'
    # 9. taskkill fails and the process is still there: stop.ps1 stops there.
    Check '9' $tunnel 'cloudflared' 'cloudflared.exe' $true -Throws $true -KillExit 1 -Events 'hold 777,check,kill 777,check,release'
    # 10. taskkill fails because the process has already gone: its record goes.
    Check '10' $tunnel 'cloudflared' 'cloudflared.exe' $true -KillExit 128 -GoneAfterKill $true -Events 'hold 777,check,kill 777,check,release'
} finally {
    Remove-Item $dir -Recurse -Force -ErrorAction SilentlyContinue
}
if ($script:failures) { $script:failures | ForEach-Object { Write-Output "FAIL $_" }; exit 1 }
Write-Output 'stop-recorded checks passed (10 cases)'

# Checks with real processes that the stops acting on a pid record keep the
# recorded pid from going to another process between their identity check and
# the stop: stop.ps1's Stop-Recorded, tunnel.ps1's Restore-Tunnel and
# word-pid.ps1's Get-RecordedWord (whose callers stop the Word it returns).
# Windows frees a pid only when the process has exited and the last handle to
# it is closed. Each stand-in process is started through WMI, so this script
# holds no handle to it, and taskkill is replaced by a function that stops the
# process for real and then opens its number: if that still reaches the exited
# process, the stop under test holds the pid, and no other process can have it.
param([string]$Scripts = (Join-Path (Split-Path -Parent $PSScriptRoot) 'scripts'))
$ErrorActionPreference = 'Stop'
Add-Type -Namespace HoldCheck -Name Native -MemberDefinition @'
[DllImport("kernel32.dll", SetLastError = true)]
public static extern IntPtr OpenProcess(uint access, bool inherit, uint processId);
[DllImport("kernel32.dll", SetLastError = true)]
public static extern bool GetExitCodeProcess(IntPtr process, out uint exitCode);
[DllImport("kernel32.dll", SetLastError = true)]
public static extern bool CloseHandle(IntPtr handle);
'@
$holdScript = Join-Path $Scripts 'process-hold.ps1'
if (Test-Path -LiteralPath $holdScript) { . $holdScript }

# Whether $ProcId still names the exited process (STILL_ACTIVE is 259).
function Test-Pinned([uint32] $ProcId) {
    $handle = [HoldCheck.Native]::OpenProcess(0x1000, $false, $ProcId)
    if ($handle -eq [IntPtr]::Zero) { return $false }
    try {
        $code = [uint32]0
        [void][HoldCheck.Native]::GetExitCodeProcess($handle, [ref]$code)
        return $code -ne 259
    } finally { [void][HoldCheck.Native]::CloseHandle($handle) }
}

$dir = Join-Path ([IO.Path]::GetTempPath()) ("hold-check-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path (Join-Path $dir 'logs') -Force | Out-Null
$standIn = Join-Path $dir 'cloudflared.exe'
Copy-Item -LiteralPath (Join-Path $env:SystemRoot 'System32\PING.EXE') -Destination $standIn
function Start-StandIn {
    $result = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = "`"$standIn`" -n 120 127.0.0.1" }
    if ($result.ReturnValue -ne 0) { throw "could not start the stand-in (Win32_Process.Create returned $($result.ReturnValue))" }
    Start-Sleep -Milliseconds 300
    return [uint32]$result.ProcessId
}
$realTaskkill = (Get-Command taskkill.exe -CommandType Application | Select-Object -First 1).Source
$script:pinned = $null
function taskkill.exe {
    $target = [uint32]$args[-1]
    & $realTaskkill /F /PID $target | Out-Null
    Start-Sleep -Milliseconds 500
    $script:pinned = Test-Pinned $target
    $global:LASTEXITCODE = 0
}
function Write-Host { }

$failures = @()
$started = @()
try {
    # 1. stop.ps1's Stop-Recorded. stop.ps1 acts as soon as it runs, so only
    #    the function is loaded from it.
    $parseErrors = $null
    $ast = [System.Management.Automation.Language.Parser]::ParseFile((Join-Path $Scripts 'stop.ps1'), [ref]$null, [ref]$parseErrors)
    if ($parseErrors) { throw "Could not parse stop.ps1: $($parseErrors[0].Message)" }
    $definition = $ast.Find({ param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Stop-Recorded' }, $true)
    . ([scriptblock]::Create($definition.Extent.Text))
    $procId = Start-StandIn; $started += $procId
    $pidFile = Join-Path $dir 'logs\tunnel.pid'
    Set-Content -Path $pidFile -Value $procId -Encoding ascii
    $script:pinned = $null
    Stop-Recorded $pidFile 'cloudflared' 'cloudflared.exe'
    if ($null -eq $script:pinned) { $failures += "1: Stop-Recorded did not stop the recorded process" }
    elseif (-not $script:pinned) { $failures += "1: Stop-Recorded let pid $procId go while it stopped the process it checked" }

    # 2. tunnel.ps1's Restore-Tunnel replacing a named tunnel. No service, and
    #    the replacement launch is a stub.
    . (Join-Path $Scripts 'tunnel.ps1')
    function Get-Service { [CmdletBinding()] param($Name) }
    function Start-Tunnel { param($Root, $Port, $Token) [pscustomobject]@{ Id = 1 } }
    $procId = Start-StandIn; $started += $procId
    Set-Content -Path $pidFile -Value $procId -Encoding ascii
    $script:pinned = $null
    $lines = @(Restore-Tunnel $dir '8787' 'tok')
    if ($null -eq $script:pinned) { $failures += "2: Restore-Tunnel did not stop the recorded tunnel: $($lines -join ' | ')" }
    elseif (-not $script:pinned) { $failures += "2: Restore-Tunnel let pid $procId go while it stopped the tunnel it checked" }

    # 3. word-pid.ps1's Get-RecordedWord: the Word it returns stays pinned until
    #    the caller closes .Hold. WMI's view is a stub here, since the stand-in
    #    is not an automation Word; the pid and the hold are real.
    . (Join-Path $Scripts 'word-pid.ps1')
    $procId = Start-StandIn; $started += $procId
    $wordFile = Join-Path $dir 'word.pid'
    Set-Content -Path $wordFile -Value $procId -Encoding ascii
    & {
        function Get-CimInstance { [CmdletBinding()] param($ClassName, $Filter)
            [pscustomobject]@{ ProcessId = $procId; Name = 'WINWORD.EXE'; CommandLine = 'WINWORD.EXE -Embedding'; CreationDate = (Get-Date).AddMinutes(-5) } }
        $word = Get-RecordedWord $wordFile
        if (-not $word -or $word.Foreign) { $script:failures += "3: Get-RecordedWord did not return the recorded Word"; return }
        & $realTaskkill /F /PID $procId | Out-Null
        Start-Sleep -Milliseconds 500
        if (-not (Test-Pinned $procId)) { $script:failures += "3: Get-RecordedWord returned Word $procId without holding its pid" }
        if ($word.PSObject.Properties['Hold']) { Close-ProcessHold $word.Hold }
        Start-Sleep -Milliseconds 500
        if (Test-Pinned $procId) { $script:failures += "3: closing .Hold did not let pid $procId go" }
    }
} finally {
    $ErrorActionPreference = 'Continue'
    foreach ($procId in $started) {
        $left = Get-CimInstance Win32_Process -Filter "ProcessId=$procId" -ErrorAction SilentlyContinue
        if ($left -and $left.ExecutablePath -eq $standIn) { & $realTaskkill /F /PID $procId | Out-Null }
    }
    Start-Sleep -Milliseconds 300
    Remove-Item $dir -Recurse -Force -ErrorAction SilentlyContinue
}
if ($failures) { $failures | ForEach-Object { Write-Output "FAIL $_" }; exit 1 }
Write-Output 'process hold checks passed (3 cases)'

# Checks with real processes that the stops acting on a pid record keep the
# recorded pid from going to another process between their identity check and
# the stop: stop.ps1's Stop-Recorded, tunnel.ps1's Restore-Tunnel and
# word-pid.ps1's Get-RecordedWord (whose callers stop the Word it returns), and
# keep-alive.ps1's Stop-AllServers. Cases 5 to 7 stub the hold to check the
# paths where it is refused or the check throws.
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
function Start-StandIn([string] $Exe = $standIn) {
    $result = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = "`"$Exe`" -n 120 127.0.0.1" }
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

# A function from a script that acts as soon as it runs, loaded on its own
# (through the PowerShell parser), under $As when given.
function Get-FunctionText([string] $File, [string] $Name, [string] $As = $Name) {
    $parseErrors = $null
    $tree = [System.Management.Automation.Language.Parser]::ParseFile((Join-Path $Scripts $File), [ref]$null, [ref]$parseErrors)
    if ($parseErrors) { throw "Could not parse ${File}: $($parseErrors[0].Message)" }
    $found = $tree.Find({ param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $Name }, $true)
    if (-not $found) { throw "$Name is not defined in $File" }
    return $found.Extent.Text -replace "^function $Name", "function $As"
}

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

    # 4. keep-alive.ps1's Stop-AllServers, which lists every python.exe running
    #    serve.py and stops each. The stand-in is a python.exe whose path holds
    #    this run's serve.py path, so the list can only find it, never the real
    #    server.
    $Root = $dir
    $Serve = Join-Path $dir 'serve.py'
    $PidFile = Join-Path $dir 'logs\server.pid'
    $fakeServer = Join-Path $dir 'serve.py-stand-in\python.exe'
    New-Item -ItemType Directory -Path (Split-Path -Parent $fakeServer) -Force | Out-Null
    Copy-Item -LiteralPath $standIn -Destination $fakeServer
    function Write-Log { }
    . ([scriptblock]::Create((Get-FunctionText 'keep-alive.ps1' 'Stop-OurWord')))
    . ([scriptblock]::Create((Get-FunctionText 'keep-alive.ps1' 'Stop-AllServers')))
    $procId = Start-StandIn $fakeServer; $started += $procId
    $listed = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like "*$Serve*" })
    if ($listed.Count -ne 1 -or $listed[0].ProcessId -ne $procId) {
        $failures += "4: the server list would hold $($listed.ProcessId -join ',') and not only the stand-in $procId; not run"
    } else {
        $script:pinned = $null
        Stop-AllServers
        if ($null -eq $script:pinned) { $failures += "4: Stop-AllServers did not stop the listed server" }
        elseif (-not $script:pinned) { $failures += "4: Stop-AllServers let pid $procId go while it stopped the server it listed" }
    }

    # 5. A check that throws after the hold was taken: the getter closes the
    #    hold itself, since its caller never received it.
    & {
        $script:closed = @()
        function Open-ProcessHold { param($ProcId) [IntPtr]77 }
        function Close-ProcessHold { param($Handle) if ($Handle) { $script:closed += [int64]$Handle } }
        function Get-CimInstance { [CmdletBinding()] param($ClassName, $Filter) throw 'WMI is not answering' }
        Set-Content -Path $wordFile -Value 4321 -Encoding ascii
        Set-Content -Path $pidFile -Value 4321 -Encoding ascii
        foreach ($getter in @({ Get-RecordedWord $wordFile }, { Get-RecordedTunnel $dir -Hold })) {
            $script:closed = @()
            $threw = $false
            try { [void](& $getter) } catch { $threw = $true }
            if (-not $threw) { $script:failures += "5: $getter did not pass the check's error on" }
            if ($script:closed -notcontains 77) { $script:failures += "5: $getter left its hold open when the check threw" }
        }
    }

    # 6. Our Word, still running, whose pid cannot be held: not stopped, and
    #    its record stays. stop.ps1 stops there (as for a failed stop);
    #    keep-alive.ps1 keeps the record and the job folder holding it.
    & {
        function Open-ProcessHold { param($ProcId) $null }
        function Get-CimInstance { [CmdletBinding()] param($ClassName, $Filter)
            [pscustomobject]@{ ProcessId = 4321; Name = 'WINWORD.EXE'; CommandLine = 'WINWORD.EXE -Embedding'; CreationDate = (Get-Date).AddMinutes(-5) } }
        function Stop-Process { $script:failures += "6: Stop-Process ran on a Word whose pid was not held" }
        $job = Join-Path $dir ('work\' + ('a' * 32))
        New-Item -ItemType Directory -Path $job -Force | Out-Null
        $jobWord = Join-Path $job 'word.pid'
        Set-Content -Path $jobWord -Value 4321 -Encoding ascii
        $word = Get-RecordedWord $jobWord
        if (-not $word.Unheld -or $word.Foreign) { $script:failures += "6: Get-RecordedWord did not report our Word as unheld" }
        . ([scriptblock]::Create((Get-FunctionText 'stop.ps1' 'Stop-OurWord' 'Stop-OurWordAtStop')))
        $threw = $false
        try { Stop-OurWordAtStop $jobWord } catch { $threw = $true }
        if (-not $threw) { $script:failures += "6: stop.ps1 went on past a Word it could not stop" }
        if (-not (Test-Path -LiteralPath $jobWord)) { $script:failures += "6: stop.ps1 deleted the record of a Word still running" }
        Stop-AllServers
        if (-not (Test-Path -LiteralPath $jobWord)) { $script:failures += "6: keep-alive.ps1 deleted the record (or the job folder) of a Word still running" }
    }

    # 7. keep-alive.ps1's Stop-AllServers with a server whose pid cannot be
    #    held: not stopped.
    $procId = Start-StandIn $fakeServer; $started += $procId
    & {
        function Open-ProcessHold { param($ProcId) $null }
        $script:pinned = $null
        Stop-AllServers
        if ($null -ne $script:pinned) { $script:failures += "7: Stop-AllServers stopped a server whose pid it could not hold" }
    }
} finally {
    $ErrorActionPreference = 'Continue'
    foreach ($procId in $started) {
        $left = Get-CimInstance Win32_Process -Filter "ProcessId=$procId" -ErrorAction SilentlyContinue
        if ($left -and $left.ExecutablePath -like "$dir\*") { & $realTaskkill /F /PID $procId | Out-Null }
    }
    Start-Sleep -Milliseconds 300
    Remove-Item $dir -Recurse -Force -ErrorAction SilentlyContinue
}
if ($failures) { $failures | ForEach-Object { Write-Output "FAIL $_" }; exit 1 }
Write-Output 'process hold checks passed (7 cases)'

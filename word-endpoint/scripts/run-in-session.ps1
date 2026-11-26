# Run scripts\review-view-probe.py once in this user's interactive session and print its output.
#     powershell -ExecutionPolicy Bypass -File scripts\run-in-session.ps1 -ProbeArgs "dump C:\path\a.docx"
# Word started from an ssh shell (session 0) cannot open documents; a one-shot scheduled task
# with an Interactive principal runs in the logged-on session instead. The task is removed after.
param([Parameter(Mandatory)][string]$ProbeArgs, [int]$TimeoutSeconds = 900)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'python-runtime.ps1')
$Python = Get-EndpointPython
$Probe = Join-Path $PSScriptRoot 'review-view-probe.py'
$Log = Join-Path $env:TEMP 'review-view-probe.out.txt'
Remove-Item -LiteralPath $Log -ErrorAction SilentlyContinue
$Name = 'WordEndpointReviewViewProbe'
$me = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$cmd = "/c `"`"$Python`" -B `"$Probe`" $ProbeArgs > `"$Log`" 2>&1`""
$action = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument $cmd -WorkingDirectory $Root
$principal = New-ScheduledTaskPrincipal -UserId $me -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Seconds $TimeoutSeconds) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $Name -Action $action -Principal $principal -Settings $settings -Force | Out-Null
try {
    Start-ScheduledTask -TaskName $Name
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds + 30)
    do { Start-Sleep -Seconds 2 } while ((Get-ScheduledTask -TaskName $Name).State -eq 'Running' -and (Get-Date) -lt $deadline)
    "task result: " + (Get-ScheduledTaskInfo -TaskName $Name).LastTaskResult
} finally {
    Unregister-ScheduledTask -TaskName $Name -Confirm:$false
}
if (Test-Path -LiteralPath $Log) { Get-Content -LiteralPath $Log }

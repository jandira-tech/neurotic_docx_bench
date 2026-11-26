# Registers the logon task that babysits the Word endpoint, then starts it.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$TaskName = "WordEndpoint"
$me = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$powershell = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$script = Join-Path $PSScriptRoot "keep-alive.ps1"

$port = 8787
if ($env:PORT -match '^\d+$') { $port = [int]$env:PORT }

$action = New-ScheduledTaskAction -Execute $powershell -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`"" -WorkingDirectory $Root
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $me
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero)
$settings.ExecutionTimeLimit = "PT0S"
$settings.DisallowStartIfOnBatteries = $false
$settings.StopIfGoingOnBatteries = $false
$settings.IdleSettings.StopOnIdleEnd = $false
$settings.RunOnlyIfIdle = $false
$principal = New-ScheduledTaskPrincipal -UserId $me -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
schtasks.exe /Change /TN $TaskName /ENABLE | Out-Null

$info = Get-ScheduledTask -TaskName $TaskName
if ($info.State -ne "Running") {
    # Drop a server that belongs to this terminal before the task starts its own.
    Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like "*$(Join-Path $Root 'serve.py')*" } |
        ForEach-Object { & taskkill.exe /F /T /PID $_.ProcessId | Out-Null }
    schtasks.exe /Run /TN $TaskName | Out-Null
}

$ready = $false
foreach ($try in 1..90) {
    Start-Sleep -Seconds 1
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:$port/ready" -UseBasicParsing -TimeoutSec 3
        if ($response.StatusCode -eq 200 -and $response.Content -like '*"status":"ok"*') {
            $ready = $true
            break
        }
    } catch { }
}
if (-not $ready) {
    throw "WordEndpoint task did not become healthy. See logs\supervise.log"
}
Write-Host "WordEndpoint task is healthy on http://127.0.0.1:$port"

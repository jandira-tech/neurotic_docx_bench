# Run in Administrator PowerShell. Default is an audit; -Apply changes two settings.
param(
    [switch]$Apply,
    [ValidateRange(0,23)][int]$ScanHour = 3,
    [switch]$RecordDefender
)
$ErrorActionPreference = 'Stop'

function Get-ScanTimeMinutes([object]$Value) {
    # WMI interval properties can be TimeSpan even though Set-MpPreference
    # accepts DateTime. A TimeSpan has no TimeOfDay property.
    if ($null -eq $Value) { throw 'Defender returned an empty scan time.' }
    if ($Value -is [TimeSpan]) { $minutes = $Value.TotalMinutes }
    elseif ($Value -is [DateTime]) { $minutes = $Value.TimeOfDay.TotalMinutes }
    elseif ($Value -is [string]) {
        $duration = [TimeSpan]::Zero
        if (-not [TimeSpan]::TryParse($Value, [ref]$duration)) {
            throw "Unrecognized Defender scan time: $Value"
        }
        $minutes = $duration.TotalMinutes
    } else { throw "Unrecognized Defender scan time type: $($Value.GetType().FullName)" }
    if ($minutes -lt 0 -or $minutes -ge 1440) { throw "Scan time is outside one day: $Value" }
    return $minutes
}

$Root = Split-Path -Parent $PSScriptRoot
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run this script in Administrator PowerShell; no settings were changed.'
}
$Reports = Join-Path $Root 'reports'
New-Item -ItemType Directory -Force -Path $Reports | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$policyPath = 'HKLM:\Software\Policies\Microsoft\Windows\Server\ServerManager'
$preferences = Get-MpPreference
$policy = Get-ItemProperty -LiteralPath $policyPath -ErrorAction SilentlyContinue
$before = [ordered]@{
    Timestamp = (Get-Date).ToString('o')
    TimeZone = (Get-TimeZone).Id
    ScanScheduleDay = [int]$preferences.ScanScheduleDay
    ScanScheduleOffset = $preferences.ScanScheduleOffset
    ScanScheduleTime = $preferences.ScanScheduleTime.ToString()
    ScanScheduleQuickScanTime = $preferences.ScanScheduleQuickScanTime.ToString()
    DisableRealtimeMonitoring = $preferences.DisableRealtimeMonitoring
    ServerManagerDoNotOpenAtLogon = $policy.DoNotOpenAtLogon
}
$backup = Join-Path $Reports "windows-settings-before-$stamp.json"
$before | ConvertTo-Json | Set-Content -LiteralPath $backup -Encoding UTF8
$before | ConvertTo-Json
if ($Apply) {
    # Keep scan frequency and real-time protection; move scheduled scans overnight.
    Set-MpPreference -ScanScheduleOffset 0 -ScanScheduleQuickScanTime ([datetime]::Today.AddHours($ScanHour))
    # Policy name and value verified against the installed ServerManager.admx.
    New-Item -Path $policyPath -Force | Out-Null
    New-ItemProperty -LiteralPath $policyPath -Name 'DoNotOpenAtLogon' -Value 1 -PropertyType DWord -Force | Out-Null
    Get-Process ServerManager -ErrorAction SilentlyContinue | ForEach-Object { $_.CloseMainWindow() | Out-Null }
    $after = Get-MpPreference
    $quickMinutes = Get-ScanTimeMinutes $after.ScanScheduleQuickScanTime
    $afterReport = [ordered]@{
        Timestamp = (Get-Date).ToString('o')
        TimeZone = (Get-TimeZone).Id
        ScanScheduleDay = [int]$after.ScanScheduleDay
        ScanScheduleOffset = $after.ScanScheduleOffset
        ScanScheduleTime = $after.ScanScheduleTime.ToString()
        ScanScheduleQuickScanTime = $after.ScanScheduleQuickScanTime.ToString()
        QuickScanValueType = $after.ScanScheduleQuickScanTime.GetType().FullName
        QuickScanMinutesAfterMidnight = $quickMinutes
        DisableRealtimeMonitoring = $after.DisableRealtimeMonitoring
        ServerManagerDoNotOpenAtLogon = (Get-ItemProperty -LiteralPath $policyPath).DoNotOpenAtLogon
    }
    $afterPath = Join-Path $Reports "windows-settings-after-$stamp.json"
    $afterReport | ConvertTo-Json | Set-Content -LiteralPath $afterPath -Encoding UTF8
    if ($after.DisableRealtimeMonitoring -ne $preferences.DisableRealtimeMonitoring -or [int]$after.ScanScheduleDay -ne [int]$preferences.ScanScheduleDay) {
        throw "Unexpected Defender change; review the backup at $backup."
    }
    if ($after.ScanScheduleOffset -ne 0 -or $quickMinutes -ne ($ScanHour * 60)) {
        throw "Requested $ScanHour`:00; observed offset=$($after.ScanScheduleOffset) minutes, quick scan=$quickMinutes minutes. See $afterPath."
    }
    Write-Host "Scheduled scans moved to $ScanHour`:00 local time; Server Manager automatic launch disabled. Backup: $backup"
}
if ($RecordDefender) {
    $trace = Join-Path $Reports "defender-$stamp.etl"
    Write-Host 'Recording Defender for 60 seconds. Send comparison/PDF requests during this interval.'
    New-MpPerformanceRecording -RecordTo $trace -Seconds 60
    Get-MpPerformanceReport -Path $trace -TopProcesses 10 -TopPaths 10 -TopFiles 10 -Raw |
        ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $Reports "defender-$stamp.json") -Encoding UTF8
    Write-Host "Defender performance trace saved: $trace"
}

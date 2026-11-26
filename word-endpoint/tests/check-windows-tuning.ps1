# Dependency-free regression test; does not access Defender or change Windows settings.
$ErrorActionPreference = 'Stop'
$scriptPath = Join-Path (Split-Path -Parent $PSScriptRoot) 'scripts\tune-windows.ps1'
$syntaxErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($scriptPath, [ref]$null, [ref]$syntaxErrors)
if ($syntaxErrors) { throw ($syntaxErrors | Out-String) }
$definition = $ast.Find({
    param($node)
    $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Get-ScanTimeMinutes'
}, $false)
if (-not $definition) { throw 'The scan-time conversion function is missing.' }
Invoke-Expression $definition.Extent.Text
foreach ($value in @([TimeSpan]::FromHours(3), [datetime]::Today.AddHours(3), '03:00:00')) {
    if ((Get-ScanTimeMinutes $value) -ne 180) { throw "03:00 conversion failed for $($value.GetType().FullName)." }
}
if ((Get-ScanTimeMinutes ([TimeSpan]::Zero)) -ne 0) { throw 'Midnight conversion failed.' }
if ((Get-ScanTimeMinutes ([TimeSpan]::FromMinutes(210))) -ne 210) { throw 'Minute precision was lost.' }
foreach ($value in @('invalid', [TimeSpan]::FromHours(25), [TimeSpan]::FromMinutes(-1), $null)) {
    $rejected = $false
    try { Get-ScanTimeMinutes $value | Out-Null } catch { $rejected = $true }
    if (-not $rejected) { throw 'An invalid scan time was accepted.' }
}
# Run only the scheduling command against a local stub, not Defender itself.
function Set-MpPreference([int]$ScanScheduleOffset, [datetime]$ScanScheduleQuickScanTime) {
    return [pscustomobject]@{Offset=$ScanScheduleOffset; QuickTime=$ScanScheduleQuickScanTime}
}
$command = $ast.Find({
    param($node)
    $node -is [System.Management.Automation.Language.CommandAst] -and $node.GetCommandName() -eq 'Set-MpPreference'
}, $false)
foreach ($ScanHour in @(0, 3, 23)) {
    $configured = Invoke-Expression $command.Extent.Text
    if ($configured.Offset -ne 0 -or $configured.QuickTime.TimeOfDay.TotalMinutes -ne $ScanHour * 60) {
        throw "Scheduling at hour $ScanHour adds an offset or uses the wrong quick-scan time."
    }
}
$validation = $ast.Find({
    param($node)
    $node -is [System.Management.Automation.Language.IfStatementAst] -and $node.Clauses[0].Item1.Extent.Text -like '*$after.ScanScheduleOffset -ne*'
}, $false)
$ScanHour = 3
$after = [pscustomobject]@{ScanScheduleOffset=0}
$quickMinutes = 180
if (Invoke-Expression $validation.Clauses[0].Item1.Extent.Text) { throw 'Correct settings failed validation.' }
$after.ScanScheduleOffset = 180
if (-not (Invoke-Expression $validation.Clauses[0].Item1.Extent.Text)) { throw 'A nonzero offset was accepted.' }
$after.ScanScheduleOffset = 0
$quickMinutes = 120
if (-not (Invoke-Expression $validation.Clauses[0].Item1.Extent.Text)) { throw 'The wrong quick-scan time was accepted.' }
Write-Host 'PASS scan-time conversion, zero-offset scheduling and post-configuration validation.'

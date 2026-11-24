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
$command = $ast.Find({
    param($node)
    $node -is [System.Management.Automation.Language.CommandAst] -and $node.GetCommandName() -eq 'Set-MpPreference'
}, $false)
# The stub below takes any value, so hold the command to the real cmdlet's
# metadata too: every parameter it names must exist there, and every value
# the stub receives must convert to that parameter's type. Reading the
# metadata does not touch Defender's settings.
$real = Get-Command -Name Set-MpPreference -Module Defender -ErrorAction SilentlyContinue
if ($real) {
    $named = @($command.CommandElements | Where-Object { $_ -is [System.Management.Automation.Language.CommandParameterAst] } | ForEach-Object ParameterName)
    if ($named.Count -eq 0) { throw 'Set-MpPreference names no parameters.' }
    foreach ($name in $named) {
        if (-not $real.Parameters.ContainsKey($name)) { throw "Set-MpPreference has no -$name on this machine." }
    }
    $metadata = "parameter names and the values passed checked against Defender's Set-MpPreference"
} else {
    $metadata = "SKIPPED the parameter check: the Defender module is not installed here"
}
# Run only the scheduling command against a local stub, not Defender itself.
function Set-MpPreference($ScanScheduleOffset, $ScanScheduleTime, $ScanScheduleQuickScanTime) {
    $bound = @{}
    foreach ($key in $PSBoundParameters.Keys) { $bound[$key] = $PSBoundParameters[$key] }
    return [pscustomobject]@{Offset=$ScanScheduleOffset; FullTime=$ScanScheduleTime; QuickTime=$ScanScheduleQuickScanTime; Bound=$bound}
}
foreach ($ScanHour in @(0, 3, 23)) {
    $configured = Invoke-Expression $command.Extent.Text
    if ($real) {
        foreach ($name in $configured.Bound.Keys) {
            $type = $real.Parameters[$name].ParameterType
            $value = $configured.Bound[$name]
            try { [System.Management.Automation.LanguagePrimitives]::ConvertTo($value, $type) | Out-Null }
            catch { throw "-$name takes $($type.FullName); the script passes a $($value.GetType().FullName) that does not convert to it." }
        }
    }
    if ($configured.Offset -ne 0 -or $configured.QuickTime.TimeOfDay.TotalMinutes -ne $ScanHour * 60) {
        throw "Scheduling at hour $ScanHour adds an offset or uses the wrong quick-scan time."
    }
    # The full scan has its own time; leaving it unset keeps it where it was.
    if ($null -eq $configured.FullTime -or $configured.FullTime.TimeOfDay.TotalMinutes -ne $ScanHour * 60) {
        throw "Scheduling at hour $ScanHour leaves the full scan at another time."
    }
}
$validation = $ast.Find({
    param($node)
    $node -is [System.Management.Automation.Language.IfStatementAst] -and $node.Clauses[0].Item1.Extent.Text -like '*$after.ScanScheduleOffset -ne*'
}, $false)
$ScanHour = 3
$after = [pscustomobject]@{ScanScheduleOffset=0}
$quickMinutes = 180
$fullMinutes = 180
if (Invoke-Expression $validation.Clauses[0].Item1.Extent.Text) { throw 'Correct settings failed validation.' }
$after.ScanScheduleOffset = 180
if (-not (Invoke-Expression $validation.Clauses[0].Item1.Extent.Text)) { throw 'A nonzero offset was accepted.' }
$after.ScanScheduleOffset = 0
$quickMinutes = 120
if (-not (Invoke-Expression $validation.Clauses[0].Item1.Extent.Text)) { throw 'The wrong quick-scan time was accepted.' }
$quickMinutes = 180
$fullMinutes = 840
if (-not (Invoke-Expression $validation.Clauses[0].Item1.Extent.Text)) { throw 'A full scan left at 14:00 was accepted.' }
Write-Host "PASS scan-time conversion, zero-offset scheduling of full and quick scans, and post-configuration validation; $metadata."

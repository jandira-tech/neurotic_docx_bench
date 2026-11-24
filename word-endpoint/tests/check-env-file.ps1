# Regression test for creating .env (scripts\env-file.ps1, New-RestrictedEnvFile)
# in a temporary folder. It runs icacls on its own files only.
param([string]$Script = (Join-Path (Split-Path -Parent $PSScriptRoot) 'scripts\env-file.ps1'))
$ErrorActionPreference = 'Stop'
. $Script
$dir = Join-Path ([IO.Path]::GetTempPath()) ("env-check-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $dir -Force | Out-Null
$path = Join-Path $dir '.env'
$sid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$failures = @()
try {

    # 1. icacls fails (an account it cannot resolve): refused, and no token file is
    #    left for the next start.ps1 to use without the restriction.
    $refused = $false
    try { New-RestrictedEnvFile $path @('WORD_API_TOKEN=secret-a') "NO_SUCH_DOMAIN_$(Get-Random)\nobody" } catch { $refused = $true }
    if (-not $refused) { $failures += "1: an unrestricted .env was accepted" }
    $left = @(Get-ChildItem -LiteralPath $dir -Force | Where-Object { $_.Name -like '.env*' } | ForEach-Object Name)
    if ($left) { $failures += "1: left behind after the ACL failed: $($left -join ', ')" }

    # 2. The current account, by SID as start.ps1 passes it: .env exists,
    #    inheritance is off, and that account is the only rule.
    New-RestrictedEnvFile $path @('WORD_API_TOKEN=secret-b', 'PORT=8787') "*$sid"
    if (-not (Test-Path -LiteralPath $path)) { $failures += "2: .env was not created" }
    else {
        $acl = Get-Acl -LiteralPath $path
        if (-not $acl.AreAccessRulesProtected) { $failures += "2: .env still inherits its folder's rules" }
        $who = @($acl.Access | ForEach-Object { $_.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value })
        if ($who.Count -ne 1 -or $who[0] -ne $sid) { $failures += "2: rules for $($who -join ', '), expected only $sid" }
        if ((Get-Content -LiteralPath $path)[0] -ne 'WORD_API_TOKEN=secret-b') { $failures += "2: wrong content" }
    }
    $extra = @(Get-ChildItem -LiteralPath $dir -Force | Where-Object { $_.Name -ne '.env' } | ForEach-Object Name)
    if ($extra) { $failures += "2: stray files: $($extra -join ', ')" }

} finally {
    Remove-Item $dir -Recurse -Force -ErrorAction SilentlyContinue
}
if ($failures) { $failures | ForEach-Object { Write-Output "FAIL $_" }; exit 1 }
Write-Output 'env file checks passed (2 cases)'

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
    #    inheritance is off, and that account (read and write) and SYSTEM (read,
    #    for the public watchdog) are the only rules.
    New-RestrictedEnvFile $path @('WORD_API_TOKEN=secret-b', 'PORT=8787') "*$sid"
    if (-not (Test-Path -LiteralPath $path)) { $failures += "2: .env was not created" }
    else {
        $acl = Get-Acl -LiteralPath $path
        if (-not $acl.AreAccessRulesProtected) { $failures += "2: .env still inherits its folder's rules" }
        $who = @($acl.Access | ForEach-Object { $_.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value } | Sort-Object)
        $want = @($sid, 'S-1-5-18') | Sort-Object
        if (($who -join ',') -ne ($want -join ',')) { $failures += "2: rules for $($who -join ', '), expected $($want -join ', ')" }
        $system = @($acl.Access | Where-Object { $_.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value -eq 'S-1-5-18' })
        if ($system -and ($system[0].FileSystemRights -band [System.Security.AccessControl.FileSystemRights]::WriteData)) { $failures += "2: SYSTEM can write .env" }
        try { Assert-RestrictedEnvFile $path } catch { $failures += "2: a .env it created was refused: $($_.Exception.Message)" }
        if ((Get-Content -LiteralPath $path)[0] -ne 'WORD_API_TOKEN=secret-b') { $failures += "2: wrong content" }
    }
    $extra = @(Get-ChildItem -LiteralPath $dir -Force | Where-Object { $_.Name -ne '.env' } | ForEach-Object Name)
    if ($extra) { $failures += "2: stray files: $($extra -join ', ')" }

    # 3. A .env made some other way (it inherits the folder's rules) is refused.
    $plain = Join-Path $dir 'plain.env'
    Set-Content -LiteralPath $plain -Value 'WORD_API_TOKEN=x' -Encoding ascii
    $message = ''
    try { Assert-RestrictedEnvFile $plain } catch { $message = $_.Exception.Message }
    if ($message -notmatch 'inherits') { $failures += "3: an inheriting .env was accepted" }
    # The command it prints fixes it, pasted into PowerShell as an operator would.
    $fix = ($message -split 'Restrict it with: ', 2)[1]
    Invoke-Expression $fix | Out-Null
    try { Assert-RestrictedEnvFile $plain } catch { $failures += "3: its printed fix did not fix it: $($_.Exception.Message)" }

    # 3b. A protected .env with an explicit grant to Everyone is refused, and
    #     the printed fix removes that grant (/grant:r alone would keep it).
    & icacls.exe $plain /grant '*S-1-1-0:(R)' | Out-Null
    $message = ''
    try { Assert-RestrictedEnvFile $plain } catch { $message = $_.Exception.Message }
    if (-not $message) { $failures += "3b: an explicit grant to Everyone was accepted" }
    $fix = ($message -split 'Restrict it with: ', 2)[1]
    if ($fix -notmatch '/remove:g \*S-1-1-0') { $failures += "3b: the fix does not remove Everyone: $fix" }
    Invoke-Expression $fix | Out-Null
    try { Assert-RestrictedEnvFile $plain } catch { $failures += "3b: its printed fix did not fix it: $($_.Exception.Message)" }
    Remove-Item -LiteralPath $plain -Force

    # 4. Read-DotEnv reads what word_endpoint\config.py's load_dotenv reads.
    $sample = Join-Path $dir 'sample.env'
    @('# comment', '  WORD_API_TOKEN = "abc=def"  ', 'PORT=8787', 'PORT=9999', 'lower=x',
      'EMPTY=', "QUOTED='single'", "MIXED='x`"", 'no equals sign') | Set-Content -LiteralPath $sample -Encoding UTF8
    $got = Read-DotEnv $sample
    $expected = [ordered]@{ WORD_API_TOKEN = 'abc=def'; PORT = '8787'; EMPTY = ''; QUOTED = 'single'; MIXED = "'x`"" }
    $gotText = ($got.Keys | ForEach-Object { "$_=[$($got[$_])]" }) -join ' '
    $wantText = ($expected.Keys | ForEach-Object { "$_=[$($expected[$_])]" }) -join ' '
    if ($gotText -cne $wantText) { $failures += "4: read $gotText, expected $wantText" }
    if ((Read-DotEnv (Join-Path $dir 'missing.env')).Count -ne 0) { $failures += "4: a missing file read as values" }
    Remove-Item -LiteralPath $sample -Force

    # 5. Set-DotEnvValue replaces the key however it is written, so the new
    #    value is the one read back, and keeps the other lines and the rules.
    $urls = Join-Path $dir 'urls.env'
    New-RestrictedEnvFile $urls @('WORD_API_TOKEN=x', '  WORD_PUBLIC_URL = "https://old.trycloudflare.com"', 'PORT=8787', 'WORD_PUBLIC_URL=https://older.example') "*$sid"
    Set-DotEnvValue $urls 'WORD_PUBLIC_URL' 'https://new.trycloudflare.com'
    $read = Read-DotEnv $urls
    if ($read['WORD_PUBLIC_URL'] -ne 'https://new.trycloudflare.com') { $failures += "5: read back $($read['WORD_PUBLIC_URL'])" }
    $text = @(Get-Content -LiteralPath $urls)
    if (($text -join '|') -ne 'WORD_API_TOKEN=x|WORD_PUBLIC_URL=https://new.trycloudflare.com|PORT=8787') { $failures += "5: file is $($text -join ' | ')" }
    try { Assert-RestrictedEnvFile $urls } catch { $failures += "5: the rewrite lost the access rules: $($_.Exception.Message)" }
    Set-DotEnvValue $urls 'RATE_LIMIT_PER_MINUTE' '300'
    if ((Read-DotEnv $urls)['RATE_LIMIT_PER_MINUTE'] -ne '300') { $failures += "5: a missing key was not appended" }
    Remove-Item -LiteralPath $urls -Force

} finally {
    Remove-Item $dir -Recurse -Force -ErrorAction SilentlyContinue
}
if ($failures) { $failures | ForEach-Object { Write-Output "FAIL $_" }; exit 1 }
Write-Output 'env file checks passed (6 cases)'

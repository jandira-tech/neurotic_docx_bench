# .env holds the API token. start.ps1 creates it, start.ps1 and the public
# watchdog read it, and the service reads it itself (word_endpoint\config.py).

$SystemSid = 'S-1-5-18'

# Creates .env so that it exists only once it is restricted: $Account (anything
# icacls takes, such as "*<SID>") may read and write it, and SYSTEM may read it,
# because the public watchdog runs as SYSTEM. start.ps1 creates .env only when
# it is missing, so a .env left behind by a failed icacls would be used on the
# next start with the token readable.
function New-RestrictedEnvFile([string] $Path, [string[]] $Lines, [string] $Account) {
    $staged = "$Path.new"
    Remove-Item -LiteralPath $staged -Force -ErrorAction SilentlyContinue
    $Lines | Set-Content -LiteralPath $staged -Encoding ascii -ErrorAction Stop
    # "Stop" does not cover native commands, hence the exit-code check.
    & icacls.exe $staged /inheritance:r /grant:r "${Account}:(R,W)" /grant:r "*${SystemSid}:(R)" | Out-Null
    $code = $LASTEXITCODE
    if ($code -ne 0) {
        Remove-Item -LiteralPath $staged -Force -ErrorAction SilentlyContinue
        $note = if (Test-Path -LiteralPath $staged) { " Delete $staged by hand: it holds an unused token." } else { "" }
        throw "Could not restrict $Path to $Account (icacls exit $code).$note"
    }
    # A rename keeps the restricted rules.
    Move-Item -LiteralPath $staged -Destination $Path -ErrorAction Stop
}

# A PowerShell single-quoted string that reads back as $Text. PowerShell also
# takes the typographic single quotes (U+2018 to U+201B) as quote marks, so
# each of them is doubled too.
function Format-Literal([string] $Text) { return "'" + ($Text -replace "(['\u2018\u2019\u201A\u201B])", '$1$1') + "'" }

# Refuses a .env other accounts can read: it must not inherit its folder's
# rules, and may grant access only to SYSTEM, Administrators and the account
# running this. start.ps1 checks it on every start, not only when it creates it.
function Assert-RestrictedEnvFile([string] $Path) {
    $acl = Get-Acl -LiteralPath $Path -ErrorAction Stop
    $me = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    $allowed = @($SystemSid, 'S-1-5-32-544', $me)
    $others = @()
    $remove = @()
    foreach ($rule in $acl.Access) {
        if ("$($rule.AccessControlType)" -ne 'Allow') { continue }
        $sid = $rule.IdentityReference.Value
        try { $sid = $rule.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value } catch { }
        if ($allowed -notcontains $sid) {
            $others += $rule.IdentityReference.Value
            # Inherited rules go with /inheritance:r; explicit ones need /remove:g,
            # since /grant:r replaces only the grants of the accounts it names.
            if (-not $rule.IsInherited) { $remove += $(if ($sid -like 'S-1-*') { "*$sid" } else { Format-Literal $sid }) }
        }
    }
    if (-not $acl.AreAccessRulesProtected -or $others) {
        $why = if (-not $acl.AreAccessRulesProtected) { "it inherits its folder's rules" } else { "it grants $(@($others | Select-Object -Unique) -join ', ')" }
        $removal = if ($remove) { " /remove:g $(@($remove | Select-Object -Unique) -join ' ')" } else { "" }
        # Single-quoted, so the command can be pasted into PowerShell whatever
        # the path holds ("$" included).
        throw ("$Path holds the API token, but $why. Restrict it with: " +
            "icacls $(Format-Literal $Path) /inheritance:r$removal /grant:r $(Format-Literal "*${me}:(R,W)") /grant:r $(Format-Literal "*${SystemSid}:(R)")")
    }
}

# Splits one .env line the way load_dotenv in word_endpoint\config.py does:
# blank lines, "#" comments and lines without "=" hold nothing, the line splits
# at its first "=", key and value are trimmed, one pair of matching quotes
# around the value is removed, and keys must be upper case. Returns
# @(key, value), or $null for a line that sets nothing.
function Split-DotEnvLine([string] $Raw) {
    $line = $Raw.Trim()
    if (-not $line -or $line.StartsWith('#') -or -not $line.Contains('=')) { return $null }
    $at = $line.IndexOf('=')
    $key = $line.Substring(0, $at).Trim()
    $value = $line.Substring($at + 1).Trim()
    if ($value.Length -ge 2 -and $value[0] -eq $value[$value.Length - 1] -and ($value[0] -eq '"' -or $value[0] -eq "'")) {
        $value = $value.Substring(1, $value.Length - 2)
    }
    if ($key -cnotmatch '^[A-Z][A-Z0-9_]{0,40}$') { return $null }
    return , @($key, $value)
}

# Reads .env like load_dotenv: the first line for a key wins.
function Read-DotEnv([string] $Path) {
    $values = [ordered]@{}
    if (-not (Test-Path -LiteralPath $Path)) { return $values }
    foreach ($raw in Get-Content -LiteralPath $Path -Encoding UTF8) {
        $pair = Split-DotEnvLine $raw
        if ($null -eq $pair -or $values.Contains($pair[0])) { continue }
        $values[$pair[0]] = $pair[1]
    }
    return $values
}

# Sets one key in .env so that Read-DotEnv and load_dotenv read the new value:
# the first line for that key (however it is spaced or quoted) becomes
# KEY=value, later lines for it are dropped, and a missing key is appended.
# The file is rewritten in place, so it keeps its access rules, as UTF-8
# without a byte-order mark: load_dotenv reads strict UTF-8, which would make a
# BOM part of the first key, and ASCII would turn other lines' accents into "?".
function Set-DotEnvValue([string] $Path, [string] $Key, [string] $Value) {
    $lines = @()
    if (Test-Path -LiteralPath $Path) { $lines = @(Get-Content -LiteralPath $Path -Encoding UTF8) }
    $found = $false
    $updated = New-Object System.Collections.Generic.List[string]
    foreach ($raw in $lines) {
        $pair = Split-DotEnvLine $raw
        if ($null -eq $pair -or $pair[0] -cne $Key) { $updated.Add($raw) }
        elseif (-not $found) { $found = $true; $updated.Add("$Key=$Value") }
    }
    if (-not $found) { $updated.Add("$Key=$Value") }
    $full = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Path)
    [System.IO.File]::WriteAllLines($full, $updated.ToArray(), (New-Object System.Text.UTF8Encoding $false))
}

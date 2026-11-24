# Creates .env so that it exists only once it is restricted to one account.
# start.ps1 creates .env only when it is missing, so a .env left behind by a
# failed icacls would be used on the next start with the token readable.
# $Account is anything icacls takes, such as "*<SID>".
function New-RestrictedEnvFile([string] $Path, [string[]] $Lines, [string] $Account) {
    $staged = "$Path.new"
    Remove-Item -LiteralPath $staged -Force -ErrorAction SilentlyContinue
    $Lines | Set-Content -LiteralPath $staged -Encoding ascii -ErrorAction Stop
    # "Stop" does not cover native commands, hence the exit-code check.
    & icacls.exe $staged /inheritance:r /grant:r "${Account}:(R,W)" | Out-Null
    $code = $LASTEXITCODE
    if ($code -ne 0) {
        Remove-Item -LiteralPath $staged -Force -ErrorAction SilentlyContinue
        $note = if (Test-Path -LiteralPath $staged) { " Delete $staged by hand: it holds an unused token." } else { "" }
        throw "Could not restrict $Path to $Account (icacls exit $code).$note"
    }
    # A rename keeps the restricted rules.
    Move-Item -LiteralPath $staged -Destination $Path -ErrorAction Stop
}

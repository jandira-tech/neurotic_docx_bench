$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
& (Join-Path $PSScriptRoot "bootstrap.ps1")

. (Join-Path $PSScriptRoot "env-file.ps1")
$EnvFile = Join-Path $Root ".env"
if (-not (Test-Path $EnvFile)) {
    $bytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $token = [Convert]::ToBase64String($bytes).TrimEnd("=").Replace("+", "-").Replace("/", "_")
    # By SID: over SSH on a workgroup machine USERDOMAIN is "WORKGROUP", which
    # icacls cannot resolve (exit 1332), so the name form fails for the right user.
    $me = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    New-RestrictedEnvFile $EnvFile @("WORD_API_TOKEN=$token", "PORT=8787") "*$me"
    Write-Host "Created .env"
}
Assert-RestrictedEnvFile $EnvFile

$DotEnv = Read-DotEnv $EnvFile
foreach ($key in @('WORD_API_TOKEN', 'PORT', 'CLOUDFLARE_TUNNEL_TOKEN', 'JOB_TIMEOUT_SECONDS', 'QUEUE_TIMEOUT_SECONDS', 'RATE_LIMIT_PER_MINUTE', 'MAX_CONCURRENT', 'WORD_PUBLIC_URL')) {
    if ($DotEnv.Contains($key)) { Set-Item -Path "Env:$key" -Value $DotEnv[$key] }
}
if (-not $env:PORT) { $env:PORT = "8787" }
New-Item -ItemType Directory -Force -Path (Join-Path $Root "logs"), (Join-Path $Root "work") | Out-Null

& (Join-Path $PSScriptRoot "install-task.ps1")

$public = ""
if ($env:WORD_PUBLIC_URL) { $public = $env:WORD_PUBLIC_URL.Trim().TrimEnd("/") }
if ($public -match '^https://' -and $public -notlike '*.trycloudflare.com') {
    Set-Content -Path (Join-Path $Root "logs\public_url.txt") -Value $public -Encoding ascii
    Write-Host "Local service: http://127.0.0.1:$($env:PORT)"
    Write-Host "Public URL: $public"
    exit 0
}

. (Join-Path $PSScriptRoot "tunnel.ps1")
$tunnelRunning = $null -ne (Get-RecordedTunnel $Root)
if (-not $tunnelRunning) {
    Start-Tunnel $Root $env:PORT (Get-TunnelToken $DotEnv) | Out-Null
}

if (Get-TunnelToken $DotEnv) {
    Write-Host "Named Cloudflare tunnel is running."
    Write-Host "Local service: http://127.0.0.1:$($env:PORT)"
    exit 0
}

$url = $null
$savedUrl = Join-Path $Root "logs\public_url.txt"
if ($tunnelRunning -and (Test-Path $savedUrl)) {
    $url = (Get-Content $savedUrl -Raw).Trim()
}
if (-not $url) {
    foreach ($try in 1..45) {
        Start-Sleep -Seconds 1
        $text = ""
        foreach ($name in @("tunnel.log", "tunnel.err.log")) {
            $path = Join-Path $Root "logs\$name"
            if (-not (Test-Path $path)) { continue }
            try {
                $stream = [IO.File]::Open($path, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::ReadWrite)
                $reader = New-Object IO.StreamReader($stream)
                $text += $reader.ReadToEnd()
                $reader.Dispose()
                $stream.Dispose()
            } catch { }
        }
        $match = [regex]::Match($text, "https://[a-z0-9-]+\.trycloudflare\.com")
        if ($match.Success) {
            $url = $match.Value
            break
        }
    }
}
if (-not $url) {
    throw "Cloudflare tunnel did not publish a URL. See logs\tunnel.err.log"
}
Set-Content -Path (Join-Path $Root "logs\public_url.txt") -Value $url -Encoding ascii
Set-DotEnvValue $EnvFile 'WORD_PUBLIC_URL' $url
Write-Host "Local service: http://127.0.0.1:$($env:PORT)"
Write-Host "Public URL: $url"

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Tools = Join-Path $Root ".tools"
$PythonDir = Join-Path $Tools "python"
$Python = Join-Path $PythonDir "python.exe"
New-Item -ItemType Directory -Force -Path $Tools | Out-Null

# curl.exe's exit code is not an error under "Stop", and a partial file left at
# the destination would be skipped as present on every later run. Download to a
# temporary name and move it into place only when curl reports success.
function Get-Download([string]$Url, [string]$Destination) {
    $partial = "$Destination.partial"
    Remove-Item -LiteralPath $partial -Force -ErrorAction SilentlyContinue
    curl.exe -fL --retry 3 -o $partial $Url
    if ($LASTEXITCODE -ne 0) {
        Remove-Item -LiteralPath $partial -Force -ErrorAction SilentlyContinue
        throw "Download failed ($LASTEXITCODE): $Url"
    }
    Move-Item -LiteralPath $partial -Destination $Destination -Force
}

if (-not (Test-Path $Python)) {
    $Zip = Join-Path $Tools "python-3.12.10-embed-amd64.zip"
    if (-not (Test-Path $Zip)) {
        Write-Host "Downloading Python 3.12.10"
        Get-Download "https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip" $Zip
    }
    if (Test-Path $PythonDir) { Remove-Item -Recurse -Force $PythonDir }
    Expand-Archive -Path $Zip -DestinationPath $PythonDir -Force
    $GetPip = Join-Path $Tools "get-pip.py"
    if (-not (Test-Path $GetPip)) {
        Get-Download "https://bootstrap.pypa.io/get-pip.py" $GetPip
    }
    & $Python $GetPip
    if ($LASTEXITCODE -ne 0) { throw "pip installation failed." }
}

$Pth = Join-Path $PythonDir "python312._pth"
@(
    $Root
    "python312.zip"
    "."
    "Lib\site-packages"
    "import site"
) | Set-Content -Path $Pth -Encoding ascii

& $Python -m pip install --disable-pip-version-check -r (Join-Path $Root "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }

. (Join-Path $PSScriptRoot 'python-runtime.ps1')
$SelectedPython = Get-EndpointPython -AllowMissing
if ($SelectedPython -ne $Python) {
    $uvCandidates = @(
        (Join-Path $Tools 'uv\uv.exe'),
        (Join-Path $env:USERPROFILE '.local\bin\uv.exe')
    )
    $Uv = $uvCandidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
    if (-not $Uv) { throw 'Install uv before setting up the Python 3.15 runtime.' }
    if (-not (Test-Path -LiteralPath $SelectedPython -PathType Leaf)) {
        & $Uv venv --python 3.15 (Join-Path $Tools 'python315-bench')
        if ($LASTEXITCODE -ne 0) { throw 'Python 3.15 environment creation failed.' }
    }
    & $Uv pip install --python $SelectedPython -r (Join-Path $Root 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.15 dependency installation failed.' }
}

$Cloud = Join-Path $Tools "cloudflared.exe"
if (-not (Test-Path $Cloud)) {
    Write-Host "Downloading cloudflared"
    Get-Download "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe" $Cloud
}

Remove-Item (Join-Path $Tools "python-3.12.10-amd64.exe") -ErrorAction SilentlyContinue
Write-Host "Tools ready; selected Python: $SelectedPython"

# Select the same interpreter for setup, supervision, tests and verification.
function Get-EndpointPython {
    param([switch]$AllowMissing)
    $endpointRoot = Split-Path -Parent $PSScriptRoot
    $selection = Get-Content -LiteralPath (Join-Path $endpointRoot 'python-runtime.json') -Raw -ErrorAction Stop | ConvertFrom-Json -ErrorAction Stop
    switch ($selection.version) {
        '3.15' { $relative = '.tools\python315-bench\Scripts\python.exe' }
        '3.12' { $relative = '.tools\python\python.exe' }
        default { throw 'Unsupported endpoint Python version. Select 3.15 or 3.12 in python-runtime.json.' }
    }
    $executable = Join-Path $endpointRoot $relative
    if (-not $AllowMissing -and -not (Test-Path -LiteralPath $executable -PathType Leaf)) {
        throw 'The selected Python runtime is missing. Run scripts\bootstrap.ps1 before restarting.'
    }
    return $executable
}

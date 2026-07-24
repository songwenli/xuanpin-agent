$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonCandidates = @(
    (Join-Path $projectRoot ".venv\Scripts\python.exe"),
    (Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe")
)

$python = $pythonCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $python) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        $python = $pythonCommand.Source
    }
}

if (-not $python) {
    throw "Python was not found. Install Python 3.11+ or create .venv."
}

Set-Location -LiteralPath $projectRoot
Write-Host "Local: http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "LAN:   http://192.168.0.200:8000" -ForegroundColor Green
Write-Host "Keep this window open. Press Ctrl+C to stop the server."
& $python -m webapp

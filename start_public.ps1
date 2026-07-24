$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$cloudflared = Join-Path $projectRoot "tools\cloudflared.exe"
$logPath = Join-Path $projectRoot "public-tunnel.log"

if (-not (Test-Path -LiteralPath $cloudflared)) {
    throw "tools\cloudflared.exe was not found."
}

try {
    Invoke-WebRequest -Uri "http://127.0.0.1:8000/" -UseBasicParsing -TimeoutSec 5 | Out-Null
} catch {
    throw "The local Agent is not running. Start .\start_web.ps1 first."
}

Set-Location -LiteralPath $projectRoot
Set-Content -LiteralPath $logPath -Value "" -Encoding utf8
Write-Host "Creating a public HTTPS URL..." -ForegroundColor Green
Write-Host "Keep both the Agent and Tunnel windows open."
& $cloudflared tunnel --url http://127.0.0.1:8000 --no-autoupdate `
    --loglevel info --logfile $logPath

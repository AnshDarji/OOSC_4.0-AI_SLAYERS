param(
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root 'BACKEND'
$frontend = Join-Path $root 'FRONTEND'
$url = 'http://127.0.0.1:3000'

function Test-PortOpen([int]$Port) {
    return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

function Start-ServiceProcess([string]$Name, [string]$FilePath, [string[]]$Arguments, [string]$WorkingDirectory) {
    $logDirectory = Join-Path $WorkingDirectory 'logs'
    New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null

    Start-Process -FilePath $FilePath -ArgumentList $Arguments -WorkingDirectory $WorkingDirectory -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $logDirectory "$Name.out.log") `
        -RedirectStandardError (Join-Path $logDirectory "$Name.err.log")
}

if (-not (Test-PortOpen 8000)) {
    $python = Join-Path $backend 'venv\Scripts\python.exe'
    if (-not (Test-Path $python)) {
        throw "Backend virtual environment was not found at $python."
    }
    Write-Host 'Starting backend...'
    Start-ServiceProcess 'backend' $python @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000') $backend
}

if (-not (Test-PortOpen 3000)) {
    Write-Host 'Starting frontend...'
    Start-ServiceProcess 'frontend' 'npm.cmd' @('run', 'dev', '--', '--host', '127.0.0.1') $frontend
}

$deadline = (Get-Date).AddSeconds(30)
while ((Get-Date) -lt $deadline) {
    if ((Test-PortOpen 8000) -and (Test-PortOpen 3000)) {
        Write-Host "NYAAY AI is running at $url"
        if (-not $NoBrowser) { Start-Process $url }
        exit 0
    }
    Start-Sleep -Milliseconds 500
}

throw 'NYAAY AI did not start within 30 seconds. Check BACKEND\logs and FRONTEND\logs.'

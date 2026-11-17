$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
if (-not (Test-Path "$repo/.venv/Scripts/python.exe")) { throw '请先运行 ./scripts/setup.ps1' }
if (-not (Test-Path "$repo/frontend/dist/index.html")) { throw '请先在 frontend 运行 npm run build' }
Set-Location "$repo/backend"
& "$repo/.venv/Scripts/python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000

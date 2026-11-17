param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Get-Command $Python -ErrorAction SilentlyContinue)) {
    if (Test-Path 'D:/miniconda/python.exe') { $Python = 'D:/miniconda/python.exe' }
    else { throw '请安装 Python 3.11+ 或通过 -Python 指定解释器路径。' }
}
if (-not (Test-Path '.venv/Scripts/python.exe')) {
    & $Python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw '创建虚拟环境失败' }
}
& ./.venv/Scripts/python.exe -m pip install -r backend/requirements.lock.txt
if ($LASTEXITCODE -ne 0) { throw '安装后端依赖失败' }
Push-Location frontend
try {
    npm ci --no-audit --no-fund
    if ($LASTEXITCODE -ne 0) { throw '安装前端依赖失败' }
    npm run build
    if ($LASTEXITCODE -ne 0) { throw '构建前端失败' }
} finally { Pop-Location }
Write-Output '安装完成。运行 ./scripts/start.ps1，然后打开 http://127.0.0.1:8000'

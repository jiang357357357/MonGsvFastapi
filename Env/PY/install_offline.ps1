# Python GPU 离线安装脚本
# 使用本地 wheel 包在无公网环境下创建 .venv

[CmdletBinding()]
param(
    [Parameter()]
    [string]$BundleDir = "",

    [Parameter()]
    [string]$VenvDir = "",

    [Parameter()]
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Python GPU 离线安装" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WorkspaceRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)

if ([string]::IsNullOrWhiteSpace($BundleDir)) {
    $BundleDir = $ScriptDir
}

if ([string]::IsNullOrWhiteSpace($VenvDir)) {
    $VenvDir = Join-Path $WorkspaceRoot ".venv"
}

$BundleDir = [System.IO.Path]::GetFullPath($BundleDir)
$VenvDir = [System.IO.Path]::GetFullPath($VenvDir)
$RequirementsFile = Join-Path $BundleDir "requirements.lock.txt"
$WheelDir = Join-Path $BundleDir "wheels"
$CheckGpuScript = Join-Path $BundleDir "check_gpu.py"
$VenvPythonExe = Join-Path $VenvDir "Scripts\python.exe"

Write-Host "工作区: $WorkspaceRoot" -ForegroundColor Gray
Write-Host "离线包目录: $BundleDir" -ForegroundColor Gray
Write-Host "虚拟环境目录: $VenvDir" -ForegroundColor Gray
Write-Host ""

if (-not (Test-Path $RequirementsFile)) {
    throw "未找到 requirements.lock.txt: $RequirementsFile"
}

if (-not (Test-Path $WheelDir)) {
    throw "未找到 wheels 目录: $WheelDir"
}

Write-Host "[1/4] 检查 Python..." -ForegroundColor Cyan
& $PythonExe --version
if ($LASTEXITCODE -ne 0) {
    throw "无法运行 Python: $PythonExe。请先安装 Python 3.10 x64。"
}

$pythonVersion = & $PythonExe -c "import platform, sys; print(sys.version.split()[0]); print(platform.architecture()[0])"
$pythonVersionLines = $pythonVersion -split "`r?`n"
$pythonShort = $pythonVersionLines[0]
$pythonArch = $pythonVersionLines[1]

if (-not $pythonShort.StartsWith("3.10")) {
    throw "当前 Python 版本是 $pythonShort，需要 Python 3.10.x。"
}

if ($pythonArch -ne "64bit") {
    throw "当前 Python 架构是 $pythonArch，需要 64 位 Python。"
}

Write-Host "    [✓] Python $pythonShort ($pythonArch)" -ForegroundColor Green
Write-Host ""

Write-Host "[2/4] 创建虚拟环境..." -ForegroundColor Cyan
if (Test-Path $VenvDir) {
    Write-Host "    [!] 现有 .venv 已存在，先删除旧环境" -ForegroundColor Yellow
    Remove-Item -Path $VenvDir -Recurse -Force
}

& $PythonExe -m venv $VenvDir
if ($LASTEXITCODE -ne 0) {
    throw "创建虚拟环境失败，退出码: $LASTEXITCODE"
}

Write-Host "    [✓] 虚拟环境已创建" -ForegroundColor Green
Write-Host ""

Write-Host "[3/4] 从本地 wheel 安装依赖..." -ForegroundColor Cyan
& $VenvPythonExe -m pip install --upgrade pip
& $VenvPythonExe -m pip install `
    --no-index `
    --find-links $WheelDir `
    --requirement $RequirementsFile

if ($LASTEXITCODE -ne 0) {
    throw "离线依赖安装失败，退出码: $LASTEXITCODE"
}

Write-Host "    [✓] 依赖安装完成" -ForegroundColor Green
Write-Host ""

Write-Host "[4/4] GPU 环境自检..." -ForegroundColor Cyan
if (Test-Path $CheckGpuScript) {
    & $VenvPythonExe $CheckGpuScript
} else {
    Write-Host "    [!] 未找到 check_gpu.py，跳过 GPU 自检" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  ✓ 离线安装完成" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "启动后端: .venv\\Scripts\\python.exe Code\\FastApi\\Main\\run_gateway.py" -ForegroundColor Gray
Write-Host ""

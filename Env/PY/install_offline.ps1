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

function Get-PythonInfo {
    param([string]$Exe)

    try {
        $output = & $Exe -c "import platform, sys; print(sys.executable); print(sys.version.split()[0]); print(platform.architecture()[0])" 2>$null
        if ($LASTEXITCODE -ne 0 -or $output.Count -lt 3) {
            return $null
        }

        return [PSCustomObject]@{
            Exe = $output[0]
            Version = $output[1]
            Arch = $output[2]
        }
    }
    catch {
        return $null
    }
}

function Resolve-Python310 {
    param([string]$PreferredExe)

    $info = Get-PythonInfo -Exe $PreferredExe
    if ($null -ne $info -and $info.Version.StartsWith("3.10") -and $info.Arch -eq "64bit") {
        return $info
    }

    $pyLauncher = Get-Command "py.exe" -ErrorAction SilentlyContinue
    if (-not $pyLauncher) {
        $pyLauncher = Get-Command "py" -ErrorAction SilentlyContinue
    }

    if ($pyLauncher) {
        try {
            $py310Exe = & $pyLauncher.Source -3.10 -c "import sys; print(sys.executable)" 2>$null
            if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($py310Exe)) {
                $info = Get-PythonInfo -Exe $py310Exe.Trim()
                if ($null -ne $info -and $info.Version.StartsWith("3.10") -and $info.Arch -eq "64bit") {
                    return $info
                }
            }
        }
        catch {
        }
    }

    return $info
}

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
$NltkDataDir = Join-Path $BundleDir "nltk_data"
$CheckGpuScript = Join-Path $BundleDir "check_gpu.py"
$VenvPythonExe = Join-Path $VenvDir "Scripts\python.exe"
$VenvNltkDataDir = Join-Path $VenvDir "nltk_data"

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
$pythonInfo = Resolve-Python310 -PreferredExe $PythonExe
if ($null -eq $pythonInfo) {
    throw "无法找到 Python 3.10 x64。请先安装 Python 3.10 x64。"
}

$PythonExe = $pythonInfo.Exe
$pythonShort = $pythonInfo.Version
$pythonArch = $pythonInfo.Arch

if (-not $pythonShort.StartsWith("3.10") -or $pythonArch -ne "64bit") {
    throw "当前 Python 是 $pythonShort ($pythonArch)，需要 Python 3.10.x 64bit。"
}

Write-Host "    [✓] Python $pythonShort ($pythonArch)" -ForegroundColor Green
Write-Host "    [i] $PythonExe" -ForegroundColor Gray
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
& $VenvPythonExe -m ensurepip --upgrade
& $VenvPythonExe -m pip install `
    --no-index `
    --find-links $WheelDir `
    --upgrade pip setuptools wheel

if ($LASTEXITCODE -ne 0) {
    throw "离线 pip/setuptools/wheel 初始化失败，退出码: $LASTEXITCODE"
}

& $VenvPythonExe -m pip install `
    --no-index `
    --find-links $WheelDir `
    --requirement $RequirementsFile

if ($LASTEXITCODE -ne 0) {
    throw "离线依赖安装失败，退出码: $LASTEXITCODE"
}

if (Test-Path $NltkDataDir) {
    Write-Host "    [i] 复制 NLTK 离线数据到 .venv" -ForegroundColor Gray
    New-Item -ItemType Directory -Force -Path $VenvNltkDataDir | Out-Null
    Copy-Item -Path (Join-Path $NltkDataDir "*") -Destination $VenvNltkDataDir -Recurse -Force
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

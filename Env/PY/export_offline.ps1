# Python GPU 离线依赖导出脚本
# 从当前项目锁定依赖导出 requirements，并下载离线 wheel 包

[CmdletBinding()]
param(
    [Parameter()]
    [string]$BundleDir = "",

    [Parameter()]
    [string]$DefaultIndex = "https://mirrors.aliyun.com/pypi/simple/",

    [Parameter()]
    [string]$TorchIndex = "https://mirrors.nju.edu.cn/pytorch/whl/cu128"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Python GPU 离线依赖导出" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WorkspaceRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)

if ([string]::IsNullOrWhiteSpace($BundleDir)) {
    $BundleDir = Join-Path $WorkspaceRoot "Env\OfflinePy"
}

$BundleDir = [System.IO.Path]::GetFullPath($BundleDir)
$WheelDir = Join-Path $BundleDir "wheels"
$RequirementsFile = Join-Path $BundleDir "requirements.lock.txt"
$MetadataFile = Join-Path $BundleDir "bundle-info.txt"
$UvExe = "$env:USERPROFILE\.local\bin\uv.exe"
$PythonExe = Join-Path $WorkspaceRoot ".venv\Scripts\python.exe"
$CheckGpuScript = Join-Path $ScriptDir "check_gpu.py"
$InstallScript = Join-Path $ScriptDir "install_offline.ps1"

Write-Host "工作区: $WorkspaceRoot" -ForegroundColor Gray
Write-Host "导出目录: $BundleDir" -ForegroundColor Gray
Write-Host ""

if (-not (Test-Path $UvExe)) {
    throw "未找到 UV: $UvExe"
}

if (-not (Test-Path $PythonExe)) {
    throw "未找到项目 Python: $PythonExe。请先完成 .venv 安装。"
}

if (-not (Test-Path $CheckGpuScript)) {
    throw "未找到 GPU 检查脚本: $CheckGpuScript"
}

if (-not (Test-Path $InstallScript)) {
    throw "未找到离线安装脚本: $InstallScript"
}

New-Item -ItemType Directory -Force -Path $BundleDir | Out-Null
New-Item -ItemType Directory -Force -Path $WheelDir | Out-Null

Write-Host "[1/4] 导出锁定依赖..." -ForegroundColor Cyan
& $UvExe export `
    --frozen `
    --format requirements.txt `
    --no-hashes `
    --no-emit-project `
    --output-file $RequirementsFile `
    --project $WorkspaceRoot

if ($LASTEXITCODE -ne 0) {
    throw "uv export 失败，退出码: $LASTEXITCODE"
}

Write-Host "    [✓] 已写入 $RequirementsFile" -ForegroundColor Green
Write-Host ""

Write-Host "[2/4] 下载离线 wheel 包..." -ForegroundColor Cyan
& $PythonExe -m pip download `
    --dest $WheelDir `
    --requirement $RequirementsFile `
    --index-url $DefaultIndex `
    --extra-index-url $TorchIndex `
    --only-binary=:all:

if ($LASTEXITCODE -ne 0) {
    throw "pip download 失败，退出码: $LASTEXITCODE"
}

Write-Host "    [✓] wheel 包已下载到 $WheelDir" -ForegroundColor Green
Write-Host ""

Write-Host "[3/4] 复制辅助脚本..." -ForegroundColor Cyan
Copy-Item -Path $CheckGpuScript -Destination (Join-Path $BundleDir "check_gpu.py") -Force
Copy-Item -Path $InstallScript -Destination (Join-Path $BundleDir "install_offline.ps1") -Force
Write-Host "    [✓] 已复制 install_offline.ps1 与 check_gpu.py" -ForegroundColor Green
Write-Host ""

Write-Host "[4/4] 写入环境元信息..." -ForegroundColor Cyan
$pythonVersion = & $PythonExe -c "import sys; print(sys.version.replace('\n', ' '))"
$torchInfo = & $PythonExe -c "import torch; print(f'torch={torch.__version__}'); print(f'torch_cuda={torch.version.cuda}'); print(f'cuda_available={torch.cuda.is_available()}'); print(f'gpu={torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"no gpu\"}')"
$nvidiaInfo = & nvidia-smi 2>$null

$metadata = @()
$metadata += "bundle_created_at=$(Get-Date -Format s)"
$metadata += "workspace_root=$WorkspaceRoot"
$metadata += "python=$pythonVersion"
$metadata += $torchInfo
$metadata += "default_index=$DefaultIndex"
$metadata += "torch_index=$TorchIndex"
$metadata += ""
$metadata += "nvidia_smi:"
$metadata += $nvidiaInfo

$metadata | Set-Content -Path $MetadataFile -Encoding UTF8
Write-Host "    [✓] 已写入 $MetadataFile" -ForegroundColor Green
Write-Host ""

Write-Host "========================================" -ForegroundColor Green
Write-Host "  ✓ 离线环境导出完成" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "目录: $BundleDir" -ForegroundColor Gray
Write-Host "要求: 客户机器需安装 Python 3.10 x64 和兼容的 NVIDIA 驱动" -ForegroundColor Yellow
Write-Host ""

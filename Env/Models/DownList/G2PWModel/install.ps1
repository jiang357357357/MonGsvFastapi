#Requires -Version 5.1
# G2PWModel 安装脚本
# 功能：自动查找并安装下载的模型文件

[CmdletBinding()]
param(
    [Parameter()]
    [string]$SourceFile = "",

    [Parameter()]
    [switch]$Force
)

# 设置控制台编码
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# 设置错误处理
$ErrorActionPreference = "Stop"

# 清屏并显示标题
Clear-Host
Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  G2PWModel 模型安装工具" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# 配置
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WorkspaceRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $ScriptDir)))
$TargetPath = "GPT_SoVITS\text\G2PWModel"

# 加载环境变量
$EnvFile = Join-Path $WorkspaceRoot "Env\.env"
if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^G2PW_MODEL_PATH=(.+)$') {
            $TargetPath = $matches[1]
        }
    }
}

$FullPath = Join-Path $WorkspaceRoot $TargetPath

# 如果没有指定源文件，自动查找最新的下载文件
if ([string]::IsNullOrEmpty($SourceFile)) {
    Write-Host "正在查找下载文件..." -ForegroundColor Cyan
    $tempDir = $env:TEMP
    $downloadedFiles = Get-ChildItem -Path $tempDir -Filter "G2PWModel_*.zip" -File | Sort-Object LastWriteTime -Descending

    if ($downloadedFiles.Count -eq 0) {
        Write-Host "错误: 未找到下载文件" -ForegroundColor Red
        Write-Host "请先运行 download.ps1 下载模型" -ForegroundColor Yellow
        exit 1
    }

    $SourceFile = $downloadedFiles[0].FullName
    Write-Host "找到下载文件: $SourceFile" -ForegroundColor Green
}

# 验证源文件
if (-not (Test-Path $SourceFile)) {
    Write-Host "错误: 源文件不存在: $SourceFile" -ForegroundColor Red
    exit 1
}

# 获取文件信息
$fileInfo = Get-Item $SourceFile
Write-Host ""
Write-Host "安装配置" -ForegroundColor Yellow
Write-Host "----------------------------------------------" -ForegroundColor DarkGray
Write-Host "  源文件:   $($fileInfo.FullName)" -ForegroundColor White
Write-Host "  文件大小: $([math]::Round($fileInfo.Length / 1MB, 2)) MB" -ForegroundColor White
Write-Host "  目标路径: $FullPath" -ForegroundColor White
Write-Host "----------------------------------------------" -ForegroundColor DarkGray
Write-Host ""

# 检查目标路径
if (Test-Path $FullPath) {
    if ($Force) {
        Write-Host "目标路径已存在，强制删除..." -ForegroundColor Yellow
        Remove-Item -Path $FullPath -Recurse -Force
    } else {
        Write-Host "目标路径已存在，自动删除并重新安装..." -ForegroundColor Yellow
        Remove-Item -Path $FullPath -Recurse -Force
    }
}

# 创建临时目录
$TempDir = Join-Path $env:TEMP "G2PWModel_install_$(Get-Random)"
New-Item -ItemType Directory -Path $TempDir -Force | Out-Null

try {
    # 解压文件
    Write-Host "解压文件..." -ForegroundColor Cyan
    Expand-Archive -Path $SourceFile -DestinationPath $TempDir -Force

    # 查找解压后的文件夹
    $extractedItems = Get-ChildItem -Path $TempDir

    # 移动文件到目标位置
    Write-Host "安装到目标位置..." -ForegroundColor Cyan

    # 创建目标目录
    $targetDir = Split-Path -Parent $FullPath
    if (-not (Test-Path $targetDir)) {
        New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
    }

    # 如果解压出来是一个文件夹，直接移动
    if ($extractedItems.Count -eq 1 -and $extractedItems[0].PSIsContainer) {
        Move-Item -Path $extractedItems[0].FullName -Destination $FullPath -Force
    } else {
        # 否则创建目标文件夹并移动所有内容
        New-Item -ItemType Directory -Path $FullPath -Force | Out-Null
        $extractedItems | Move-Item -Destination $FullPath -Force
    }

    # 验证安装
    if (Test-Path $FullPath) {
        $installedSize = (Get-ChildItem -Path $FullPath -Recurse -File | Measure-Object -Property Length -Sum).Sum
        Write-Host ""
        Write-Host "==================================================" -ForegroundColor Green
        Write-Host "  安装成功！" -ForegroundColor Green
        Write-Host "==================================================" -ForegroundColor Green
        Write-Host "  安装路径: $FullPath" -ForegroundColor White
        Write-Host "  占用空间: $([math]::Round($installedSize / 1MB, 2)) MB" -ForegroundColor White
        Write-Host "==================================================" -ForegroundColor Green
        Write-Host ""

        # 清理临时文件
        Remove-Item -Path $TempDir -Recurse -Force -ErrorAction SilentlyContinue

        exit 0
    } else {
        throw "安装验证失败"
    }

} catch {
    Write-Host ""
    Write-Host "==================================================" -ForegroundColor Red
    Write-Host "  安装失败！" -ForegroundColor Red
    Write-Host "==================================================" -ForegroundColor Red
    Write-Host "  错误信息: $_.Exception.Message" -ForegroundColor White
    Write-Host "==================================================" -ForegroundColor Red
    Write-Host ""

    # 清理临时文件
    if (Test-Path $TempDir) {
        Remove-Item -Path $TempDir -Recurse -Force -ErrorAction SilentlyContinue
    }

    exit 1
}

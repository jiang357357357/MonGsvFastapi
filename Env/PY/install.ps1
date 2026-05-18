﻿# Python 虚拟环境安装脚本
# 使用 UV 创建 Python 虚拟环境并安装依赖

$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Python 虚拟环境安装" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 获取脚本所在目录的父目录（工作区根目录）
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WorkspaceRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)

# 定义路径
$VENV_DIR = Join-Path $WorkspaceRoot ".venv"
$PYTHON_EXE = Join-Path $VENV_DIR "Scripts\python.exe"
$UV_EXE = "$env:USERPROFILE\.local\bin\uv.exe"
$REQUIREMENTS_FILE = Join-Path $WorkspaceRoot "requirements.txt"

Write-Host "工作区: $WorkspaceRoot" -ForegroundColor Gray
Write-Host ""

# 检查 UV 是否安装
if (-not (Test-Path $UV_EXE)) {
    Write-Host "[✗] UV 未安装" -ForegroundColor Red
    Write-Host "    请先安装 UV 包管理器" -ForegroundColor Yellow
    exit 1
}

Write-Host "[✓] UV 已安装" -ForegroundColor Green
Write-Host ""

# 检查虚拟环境是否已存在
if (Test-Path $VENV_DIR) {
    Write-Host "[!] 虚拟环境已存在，将进行重新创建" -ForegroundColor Yellow
    Write-Host "    位置: $VENV_DIR" -ForegroundColor Gray
    Write-Host ""
    Write-Host "[→] 删除旧的虚拟环境..." -ForegroundColor Cyan
    Remove-Item -Path $VENV_DIR -Recurse -Force
    Write-Host "    [✓] 旧环境已删除" -ForegroundColor Green
    Write-Host ""
}

try {
    # 1. 创建虚拟环境
    Write-Host "[→] 创建 Python 虚拟环境..." -ForegroundColor Cyan
    Write-Host "    使用 UV 创建虚拟环境..." -ForegroundColor Gray
    
    # 切换到工作区目录
    Push-Location $WorkspaceRoot
    
    # 使用 UV 创建虚拟环境（默认使用最新的 Python 版本）
    & $UV_EXE venv .venv 2>&1 | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }

    if ($LASTEXITCODE -ne 0) {
        Write-Host "    [✗] 安装失败: UV 创建虚拟环境失败 (退出码: $LASTEXITCODE)" -ForegroundColor Red
        Pop-Location
        exit 1
    }

    Write-Host "    [✓] 虚拟环境创建成功" -ForegroundColor Green
    Write-Host ""

    # 2. 验证 Python 可执行文件
    Write-Host "[→] 验证 Python 安装..." -ForegroundColor Cyan
    if (Test-Path $PYTHON_EXE) {
        $pythonVersion = & $PYTHON_EXE --version 2>&1
        Write-Host "    [✓] Python 版本: $pythonVersion" -ForegroundColor Green
    } else {
        Write-Host "    [✗] 安装失败: Python 可执行文件未找到: $PYTHON_EXE" -ForegroundColor Red
        Pop-Location
        exit 1
    }
    Write-Host ""
    
    # 3. 安装依赖
    $PYPROJECT_FILE = Join-Path $WorkspaceRoot "pyproject.toml"
    $REQUIREMENTS_FILE = Join-Path $WorkspaceRoot "requirements.txt"
    
    Write-Host "[→] 检查依赖配置文件..." -ForegroundColor Cyan
    Write-Host "    pyproject.toml: $(if (Test-Path $PYPROJECT_FILE) { '存在' } else { '不存在' })" -ForegroundColor Gray
    Write-Host "    requirements.txt: $(if (Test-Path $REQUIREMENTS_FILE) { '存在' } else { '不存在' })" -ForegroundColor Gray
    Write-Host ""
    
    if (Test-Path $PYPROJECT_FILE) {
        Write-Host "[→] 安装项目依赖..." -ForegroundColor Cyan
        Write-Host "    从 pyproject.toml 安装..." -ForegroundColor Gray
        Write-Host "    位置: $PYPROJECT_FILE" -ForegroundColor Gray
        Write-Host ""
        
        # 使用 uv sync 同步依赖（推荐方式）
        # --link-mode=copy 避免跨文件系统硬链接警告
        & $UV_EXE sync --link-mode=copy 2>&1 | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Host "    [✓] 依赖安装完成" -ForegroundColor Green
        } else {
            Write-Host ""
            Write-Host "    [!] 部分依赖安装失败" -ForegroundColor Yellow
        }
    } elseif (Test-Path $REQUIREMENTS_FILE) {
        Write-Host "[→] 安装项目依赖..." -ForegroundColor Cyan
        Write-Host "    从 requirements.txt 安装..." -ForegroundColor Gray
        Write-Host "    位置: $REQUIREMENTS_FILE" -ForegroundColor Gray
        Write-Host ""
        
        & $UV_EXE pip install -r $REQUIREMENTS_FILE --python $PYTHON_EXE 2>&1 | ForEach-Object { 
            Write-Host "    $_" -ForegroundColor Gray 
        }
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Host "    [✓] 依赖安装完成" -ForegroundColor Green
        } else {
            Write-Host ""
            Write-Host "    [!] 部分依赖安装失败" -ForegroundColor Yellow
        }
    } else {
        Write-Host "[!] 未找到依赖配置文件，跳过依赖安装" -ForegroundColor Yellow
        Write-Host "    查找位置:" -ForegroundColor Gray
        Write-Host "      - $PYPROJECT_FILE" -ForegroundColor Gray
        Write-Host "      - $REQUIREMENTS_FILE" -ForegroundColor Gray
    }
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  ✓ Python 环境安装成功!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "环境信息:" -ForegroundColor Cyan
    Write-Host "  位置: $VENV_DIR" -ForegroundColor Gray
    Write-Host "  Python: $PYTHON_EXE" -ForegroundColor Gray
    Write-Host ""
    Write-Host "激活环境:" -ForegroundColor Cyan
    Write-Host "  .venv\Scripts\activate" -ForegroundColor Gray
    Write-Host ""
    
    Pop-Location
    exit 0
    
} catch {
    Write-Host ""
    Write-Host "[✗] 安装失败: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "故障排除:" -ForegroundColor Yellow
    Write-Host "  1. 确保 UV 已正确安装" -ForegroundColor Gray
    Write-Host "  2. 检查网络连接（下载 Python 需要网络）" -ForegroundColor Gray
    Write-Host "  3. 确保有足够的磁盘空间" -ForegroundColor Gray
    Write-Host "  4. 检查防病毒软件是否阻止" -ForegroundColor Gray
    
    Pop-Location
    exit 1
}

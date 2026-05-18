# Python 虚拟环境检查脚本
# 检查 UV 创建的 Python 虚拟环境状态

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Python 虚拟环境检查" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 获取脚本所在目录的父目录（工作区根目录）
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WorkspaceRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)

# 定义路径
$VENV_DIR = Join-Path $WorkspaceRoot ".venv"
$PYTHON_EXE = Join-Path $VENV_DIR "Scripts\python.exe"
$UV_EXE = "$env:USERPROFILE\.local\bin\uv.exe"

Write-Host "工作区: $WorkspaceRoot" -ForegroundColor Gray
Write-Host ""

# 检查 UV 是否安装
if (-not (Test-Path $UV_EXE)) {
    Write-Host "[✗] UV 未安装" -ForegroundColor Red
    Write-Host "    请先安装 UV 包管理器" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

Write-Host "[✓] UV 已安装" -ForegroundColor Green
try {
    $uvVersion = & $UV_EXE --version 2>&1
    Write-Host "    版本: $uvVersion" -ForegroundColor Gray
} catch {
    Write-Host "    无法获取版本信息" -ForegroundColor Yellow
}
Write-Host ""
Write-Host ""

# 检查虚拟环境是否存在
if (Test-Path $VENV_DIR) {
    Write-Host "[✓] 虚拟环境已创建" -ForegroundColor Green
    Write-Host "    位置: $VENV_DIR" -ForegroundColor Gray
    Write-Host ""
    
    # 检查 Python 可执行文件
    if (Test-Path $PYTHON_EXE) {
        Write-Host "[✓] Python 可执行文件存在" -ForegroundColor Green
        
        # 获取 Python 版本
        try {
            $pythonVersion = & $PYTHON_EXE --version 2>&1
            Write-Host "    版本: $pythonVersion" -ForegroundColor Gray
        } catch {
            Write-Host "    无法获取 Python 版本" -ForegroundColor Yellow
        }
        
        Write-Host ""
        Write-Host ""
        
        # 检查已安装的包
        Write-Host "[→] 检查已安装的包..." -ForegroundColor Cyan
        Write-Host ""
        try {
            # 逐行输出包列表
            & $UV_EXE pip list --python $PYTHON_EXE 2>&1 | ForEach-Object {
                Write-Host $_ -ForegroundColor Gray
            }
            
            if ($LASTEXITCODE -ne 0) {
                Write-Host "    无法列出已安装的包" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "    无法列出已安装的包" -ForegroundColor Yellow
        }
        
        Write-Host ""
        Write-Host ""
        Write-Host "[✓] Python 环境检查完成 - 已配置" -ForegroundColor Green
        exit 0
    } else {
        Write-Host "[✗] Python 可执行文件不存在" -ForegroundColor Red
        Write-Host "    预期位置: $PYTHON_EXE" -ForegroundColor Gray
        Write-Host ""
        Write-Host "    虚拟环境可能已损坏，请重新安装" -ForegroundColor Yellow
        Write-Host ""
        exit 1
    }
} else {
    Write-Host "[✗] 虚拟环境未创建" -ForegroundColor Red
    Write-Host "    预期位置: $VENV_DIR" -ForegroundColor Gray
    Write-Host ""
    Write-Host "[!] 请运行安装脚本创建虚拟环境" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

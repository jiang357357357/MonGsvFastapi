# Python 虚拟环境卸载脚本
# 删除 UV 创建的 Python 虚拟环境

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Python 虚拟环境卸载" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 获取脚本所在目录的父目录（工作区根目录）
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WorkspaceRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)

# 定义路径
$VENV_DIR = Join-Path $WorkspaceRoot ".venv"

Write-Host "工作区: $WorkspaceRoot" -ForegroundColor Gray
Write-Host ""

# 检查虚拟环境是否存在
if (-not (Test-Path $VENV_DIR)) {
    Write-Host "[!] 虚拟环境不存在" -ForegroundColor Yellow
    Write-Host "    预期位置: $VENV_DIR" -ForegroundColor Gray
    Write-Host ""
    Write-Host "[✓] 无需卸载" -ForegroundColor Green
    exit 0
}

Write-Host "[!] 警告: 此操作将删除 Python 虚拟环境及所有已安装的包" -ForegroundColor Yellow
Write-Host ""
Write-Host "将要删除:" -ForegroundColor Cyan
Write-Host "  - 虚拟环境目录: $VENV_DIR" -ForegroundColor Gray
Write-Host "  - 所有已安装的 Python 包" -ForegroundColor Gray
Write-Host ""
Write-Host "[→] 开始卸载..." -ForegroundColor Cyan

try {
    # 1. 尝试结束占用虚拟环境的进程
    Write-Host ""
    Write-Host "[→] 检查并结束相关进程..." -ForegroundColor Cyan
    
    $pythonProcesses = Get-Process | Where-Object { 
        $_.Path -like "*$VENV_DIR*" 
    }
    
    if ($pythonProcesses) {
        Write-Host "    找到 $($pythonProcesses.Count) 个相关进程" -ForegroundColor Yellow
        foreach ($proc in $pythonProcesses) {
            try {
                Write-Host "    结束进程: $($proc.Name) (PID: $($proc.Id))" -ForegroundColor Gray
                Stop-Process -Id $proc.Id -Force -ErrorAction Stop
                Write-Host "    [✓] 进程已结束" -ForegroundColor Green
            } catch {
                Write-Host "    [!] 无法结束进程: $_" -ForegroundColor Yellow
            }
        }
        
        # 等待进程完全结束
        Start-Sleep -Seconds 1
    } else {
        Write-Host "    [✓] 没有发现相关进程" -ForegroundColor Green
    }
    
    # 2. 删除虚拟环境目录
    Write-Host ""
    Write-Host "[→] 删除虚拟环境目录..." -ForegroundColor Cyan
    
    # 使用 robocopy 清空目录（更可靠）
    $tempEmptyDir = Join-Path $env:TEMP "uv_empty_$(Get-Random)"
    New-Item -ItemType Directory -Path $tempEmptyDir -Force | Out-Null
    
    Write-Host "    使用 robocopy 清空目录..." -ForegroundColor Gray
    robocopy $tempEmptyDir $VENV_DIR /MIR /R:0 /W:0 /NFL /NDL /NJH /NJS | Out-Null
    
    # 删除空目录（添加 -Recurse 参数，不询问确认）
    Remove-Item -Path $VENV_DIR -Recurse -Force -ErrorAction Stop
    Remove-Item -Path $tempEmptyDir -Recurse -Force -ErrorAction SilentlyContinue
    
    Write-Host "    [✓] 虚拟环境已删除" -ForegroundColor Green
    
    # 验证删除
    Write-Host ""
    if (-not (Test-Path $VENV_DIR)) {
        Write-Host "[✓] Python 环境卸载完成!" -ForegroundColor Green
        Write-Host ""
        exit 0
    } else {
        Write-Host "[✗] 卸载验证失败 - 虚拟环境目录仍然存在" -ForegroundColor Red
        exit 1
    }
    
} catch {
    Write-Host ""
    Write-Host "[✗] 卸载失败: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "故障排除:" -ForegroundColor Yellow
    Write-Host "  1. 确保没有程序正在使用虚拟环境" -ForegroundColor Gray
    Write-Host "  2. 关闭所有 Python 进程和终端" -ForegroundColor Gray
    Write-Host "  3. 以管理员权限运行" -ForegroundColor Gray
    Write-Host "  4. 重启电脑后再试" -ForegroundColor Gray
    Write-Host "  5. 手动删除: $VENV_DIR" -ForegroundColor Gray
    exit 1
}

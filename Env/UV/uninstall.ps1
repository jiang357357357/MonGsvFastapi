# UV 包管理器卸载脚本
# 完全移除 UV 及其数据

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  UV 包管理器卸载" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 定义路径
$UV_DIR = "$env:USERPROFILE\.local\bin"
$UV_EXE = Join-Path $UV_DIR "uv.exe"
$UVX_EXE = Join-Path $UV_DIR "uvx.exe"
$UVW_EXE = Join-Path $UV_DIR "uvw.exe"

# 检查是否已安装
if (-not (Test-Path $UV_EXE)) {
    Write-Host "[!] UV 未安装" -ForegroundColor Yellow
    Write-Host "    预期位置: $UV_EXE" -ForegroundColor Gray
    Write-Host ""
    Write-Host "[✓] 无需卸载" -ForegroundColor Green
    exit 0
}

Write-Host "[!] 警告: 此操作将完全移除 UV 及其所有数据" -ForegroundColor Yellow
Write-Host ""
Write-Host "将要删除:" -ForegroundColor Cyan
Write-Host "  - UV 可执行文件 ($UV_DIR)" -ForegroundColor Gray
Write-Host "  - UV 缓存数据" -ForegroundColor Gray
Write-Host "  - UV Python 安装" -ForegroundColor Gray
Write-Host "  - UV 工具目录" -ForegroundColor Gray
Write-Host ""
Write-Host "[→] 开始卸载 UV..." -ForegroundColor Cyan

try {
    # 1. 清理缓存和数据
    Write-Host ""
    Write-Host "[→] 清理 UV 数据..." -ForegroundColor Cyan
    
    if (Test-Path $UV_EXE) {
        try {
            Write-Host "  清理缓存..." -ForegroundColor Gray
            & $UV_EXE cache clean 2>&1 | Out-Null
            Write-Host "  [✓] 缓存已清理" -ForegroundColor Green
        } catch {
            Write-Host "  [!] 缓存清理失败: $_" -ForegroundColor Yellow
        }
        
        try {
            Write-Host "  获取 Python 目录..." -ForegroundColor Gray
            $pythonDir = & $UV_EXE python dir 2>&1
            if (Test-Path $pythonDir) {
                Remove-Item -Path $pythonDir -Recurse -Force
                Write-Host "  [✓] Python 目录已删除" -ForegroundColor Green
            }
        } catch {
            Write-Host "  [!] Python 目录删除失败: $_" -ForegroundColor Yellow
        }
        
        try {
            Write-Host "  获取工具目录..." -ForegroundColor Gray
            $toolDir = & $UV_EXE tool dir 2>&1
            if (Test-Path $toolDir) {
                Remove-Item -Path $toolDir -Recurse -Force
                Write-Host "  [✓] 工具目录已删除" -ForegroundColor Green
            }
        } catch {
            Write-Host "  [!] 工具目录删除失败: $_" -ForegroundColor Yellow
        }
    }
    
    # 2. 删除可执行文件
    Write-Host ""
    Write-Host "[→] 删除 UV 可执行文件..." -ForegroundColor Cyan
    
    $filesToRemove = @($UV_EXE, $UVX_EXE, $UVW_EXE)
    foreach ($file in $filesToRemove) {
        if (Test-Path $file) {
            Remove-Item -Path $file -Force
            Write-Host "  [✓] 已删除: $(Split-Path $file -Leaf)" -ForegroundColor Green
        }
    }
    
    # 3. 从 PATH 中移除（可选）
    Write-Host ""
    Write-Host "[→] 检查 PATH 环境变量..." -ForegroundColor Cyan
    $pathEnv = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($pathEnv -like "*$UV_DIR*") {
        Write-Host "  [!] UV 目录仍在 PATH 中" -ForegroundColor Yellow
        Write-Host "  提示: 如需完全清理，请手动从 PATH 中移除: $UV_DIR" -ForegroundColor Gray
    } else {
        Write-Host "  [✓] PATH 中未找到 UV 目录" -ForegroundColor Green
    }
    
    # 验证卸载
    Write-Host ""
    if (-not (Test-Path $UV_EXE)) {
        Write-Host "[✓] UV 卸载完成!" -ForegroundColor Green
        Write-Host ""
        Write-Host "提示: 如果 PATH 中仍有 UV 目录，请重启终端" -ForegroundColor Yellow
        exit 0
    } else {
        Write-Host "[✗] 卸载验证失败 - UV 可执行文件仍然存在" -ForegroundColor Red
        exit 1
    }
    
} catch {
    Write-Host ""
    Write-Host "[✗] 卸载失败: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "故障排除:" -ForegroundColor Yellow
    Write-Host "  1. 确保 UV 进程未运行" -ForegroundColor Gray
    Write-Host "  2. 以管理员权限运行" -ForegroundColor Gray
    Write-Host "  3. 手动删除: $UV_DIR" -ForegroundColor Gray
    exit 1
}

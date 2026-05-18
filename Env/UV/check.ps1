# UV 包管理器检查脚本
# 检查 UV 是否已安装以及版本信息

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  UV 包管理器检查" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 定义 UV 安装路径
$UV_DIR = "$env:USERPROFILE\.local\bin"
$UV_EXE = Join-Path $UV_DIR "uv.exe"

# 检查 UV 是否存在
if (Test-Path $UV_EXE) {
    Write-Host "[✓] UV 已安装" -ForegroundColor Green
    Write-Host "    位置: $UV_EXE" -ForegroundColor Gray
    
    # 获取版本信息
    try {
        $version = & $UV_EXE --version 2>&1
        Write-Host "    版本: $version" -ForegroundColor Gray
    } catch {
        Write-Host "    无法获取版本信息" -ForegroundColor Yellow
    }
    
    # 检查是否在 PATH 中
    $pathEnv = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($pathEnv -like "*$UV_DIR*") {
        Write-Host "[✓] UV 已添加到 PATH" -ForegroundColor Green
    } else {
        Write-Host "[!] UV 未添加到 PATH" -ForegroundColor Yellow
        Write-Host "    建议运行安装脚本以添加到 PATH" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "[✓] UV 检查完成 - 已安装" -ForegroundColor Green
    exit 0
} else {
    Write-Host "[✗] UV 未安装" -ForegroundColor Red
    Write-Host "    预期位置: $UV_EXE" -ForegroundColor Gray
    Write-Host ""
    Write-Host "[!] 请运行安装脚本进行安装" -ForegroundColor Yellow
    exit 1
}

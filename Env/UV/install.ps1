# UV 包管理器安装脚本
# 使用本地 ZIP 文件安装 UV

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  UV 包管理器安装" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 获取脚本所在目录（Env/UV）
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# 定义路径
$UV_ZIP = Join-Path $ScriptDir "uv.zip"
$UV_EXTRACT_DIR = Join-Path $ScriptDir "uv_temp"
$UV_INSTALL_DIR = "$env:USERPROFILE\.local\bin"
$UV_EXE = Join-Path $UV_INSTALL_DIR "uv.exe"

# 检查 ZIP 文件是否存在
if (-not (Test-Path $UV_ZIP)) {
    Write-Host "[✗] 错误: 找不到 UV 安装包" -ForegroundColor Red
    Write-Host "    预期位置: $UV_ZIP" -ForegroundColor Gray
    Write-Host ""
    Write-Host "请确保 uv.zip 文件存在于 Env/UV 目录" -ForegroundColor Yellow
    exit 1
}

Write-Host "[✓] 找到 UV 安装包" -ForegroundColor Green
Write-Host "    位置: $UV_ZIP" -ForegroundColor Gray
Write-Host ""

# 检查是否已安装
if (Test-Path $UV_EXE) {
    Write-Host "[!] UV 已经安装，将进行覆盖安装" -ForegroundColor Yellow
    Write-Host "    位置: $UV_EXE" -ForegroundColor Gray
    
    # 获取当前版本
    try {
        $currentVersion = & $UV_EXE --version 2>&1
        Write-Host "    当前版本: $currentVersion" -ForegroundColor Gray
    } catch {
        Write-Host "    无法获取版本信息" -ForegroundColor Yellow
    }
    Write-Host ""
}

Write-Host "[→] 开始安装 UV..." -ForegroundColor Cyan

try {
    # 1. 创建临时解压目录
    Write-Host ""
    Write-Host "[→] 准备解压..." -ForegroundColor Cyan
    if (Test-Path $UV_EXTRACT_DIR) {
        Remove-Item -Path $UV_EXTRACT_DIR -Recurse -Force
    }
    New-Item -ItemType Directory -Path $UV_EXTRACT_DIR -Force | Out-Null
    Write-Host "    [✓] 临时目录已创建" -ForegroundColor Green
    
    # 2. 解压 ZIP 文件
    Write-Host ""
    Write-Host "[→] 解压安装包..." -ForegroundColor Cyan
    Expand-Archive -Path $UV_ZIP -DestinationPath $UV_EXTRACT_DIR -Force
    Write-Host "    [✓] 解压完成" -ForegroundColor Green
    
    # 3. 创建安装目录
    Write-Host ""
    Write-Host "[→] 准备安装目录..." -ForegroundColor Cyan
    if (-not (Test-Path $UV_INSTALL_DIR)) {
        New-Item -ItemType Directory -Path $UV_INSTALL_DIR -Force | Out-Null
        Write-Host "    [✓] 安装目录已创建: $UV_INSTALL_DIR" -ForegroundColor Green
    } else {
        Write-Host "    [✓] 安装目录已存在: $UV_INSTALL_DIR" -ForegroundColor Green
    }
    
    # 4. 复制可执行文件
    Write-Host ""
    Write-Host "[→] 安装 UV 可执行文件..." -ForegroundColor Cyan
    
    # 查找解压后的 uv.exe 文件
    $uvExeSource = Get-ChildItem -Path $UV_EXTRACT_DIR -Filter "uv.exe" -Recurse | Select-Object -First 1
    
    if ($null -eq $uvExeSource) {
        throw "在解压目录中找不到 uv.exe 文件"
    }
    
    Write-Host "    找到 uv.exe: $($uvExeSource.FullName)" -ForegroundColor Gray
    
    # 复制到安装目录
    Copy-Item -Path $uvExeSource.FullName -Destination $UV_EXE -Force
    Write-Host "    [✓] uv.exe 已安装" -ForegroundColor Green
    
    # 查找并复制其他可执行文件（uvx.exe, uvw.exe 等）
    $otherExes = Get-ChildItem -Path $UV_EXTRACT_DIR -Filter "*.exe" -Recurse | Where-Object { $_.Name -ne "uv.exe" }
    foreach ($exe in $otherExes) {
        $destPath = Join-Path $UV_INSTALL_DIR $exe.Name
        Copy-Item -Path $exe.FullName -Destination $destPath -Force
        Write-Host "    [✓] $($exe.Name) 已安装" -ForegroundColor Green
    }
    
    # 5. 清理临时目录
    Write-Host ""
    Write-Host "[→] 清理临时文件..." -ForegroundColor Cyan
    Remove-Item -Path $UV_EXTRACT_DIR -Recurse -Force
    Write-Host "    [✓] 临时文件已清理" -ForegroundColor Green
    
    # 6. 添加到 PATH（如果尚未添加）
    Write-Host ""
    Write-Host "[→] 检查 PATH 环境变量..." -ForegroundColor Cyan
    $pathEnv = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($pathEnv -notlike "*$UV_INSTALL_DIR*") {
        Write-Host "    [→] 添加到 PATH..." -ForegroundColor Cyan
        $newPath = "$pathEnv;$UV_INSTALL_DIR"
        [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
        Write-Host "    [✓] 已添加到 PATH" -ForegroundColor Green
    } else {
        Write-Host "    [✓] 已在 PATH 中" -ForegroundColor Green
    }
    
    # 7. 验证安装
    Write-Host ""
    Write-Host "[→] 验证安装..." -ForegroundColor Cyan
    if (Test-Path $UV_EXE) {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "  ✓ UV 安装成功!" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "安装信息:" -ForegroundColor Cyan
        Write-Host "  位置: $UV_EXE" -ForegroundColor Gray
        
        try {
            $version = & $UV_EXE --version 2>&1
            Write-Host "  版本: $version" -ForegroundColor Gray
        } catch {
            Write-Host "  无法获取版本信息" -ForegroundColor Yellow
        }
        
        Write-Host ""
        Write-Host "提示: 请重启终端以使 PATH 环境变量生效" -ForegroundColor Yellow
        Write-Host ""
        exit 0
    } else {
        Write-Host ""
        Write-Host "[✗] 安装验证失败 - UV 可执行文件未找到" -ForegroundColor Red
        exit 1
    }
    
} catch {
    Write-Host ""
    Write-Host "[✗] 安装失败: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "故障排除:" -ForegroundColor Yellow
    Write-Host "  1. 检查 ZIP 文件是否完整" -ForegroundColor Gray
    Write-Host "  2. 确保有足够的磁盘空间" -ForegroundColor Gray
    Write-Host "  3. 以管理员权限运行" -ForegroundColor Gray
    Write-Host "  4. 检查防病毒软件是否阻止" -ForegroundColor Gray
    
    # 清理临时目录
    if (Test-Path $UV_EXTRACT_DIR) {
        Remove-Item -Path $UV_EXTRACT_DIR -Recurse -Force -ErrorAction SilentlyContinue
    }
    
    exit 1
}

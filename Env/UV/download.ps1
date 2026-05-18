# UV 包管理器下载脚本
# 下载 UV 的 Windows 压缩包到本地

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  UV 包管理器下载" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 配置
$UV_VERSION = "0.11.2"  # 最新稳定版本
$DOWNLOAD_DIR = "D:\code\model\MonGSV\Env\UV"
$DOWNLOAD_URL = "https://github.com/astral-sh/uv/releases/download/$UV_VERSION/uv-x86_64-pc-windows-msvc.zip"
$ZIP_FILE = Join-Path $DOWNLOAD_DIR "uv-x86_64-pc-windows-msvc.zip"
$EXTRACT_DIR = Join-Path $DOWNLOAD_DIR "uv"

Write-Host "[i] 下载信息:" -ForegroundColor Cyan
Write-Host "    版本: $UV_VERSION" -ForegroundColor Gray
Write-Host "    下载地址: $DOWNLOAD_URL" -ForegroundColor Gray
Write-Host "    保存位置: $ZIP_FILE" -ForegroundColor Gray
Write-Host "    解压位置: $EXTRACT_DIR" -ForegroundColor Gray
Write-Host ""

# 检查目录
if (-not (Test-Path $DOWNLOAD_DIR)) {
    Write-Host "[->] 创建下载目录..." -ForegroundColor Cyan
    New-Item -ItemType Directory -Path $DOWNLOAD_DIR -Force | Out-Null
}

# 检查是否已下载
$needDownload = $true
if (Test-Path $ZIP_FILE) {
    Write-Host "[!] 压缩包已存在" -ForegroundColor Yellow
    $fileSize = (Get-Item $ZIP_FILE).Length / 1MB
    Write-Host "    文件大小: $([math]::Round($fileSize, 2)) MB" -ForegroundColor Gray
    Write-Host ""
    $response = Read-Host "是否重新下载? (y/N)"
    if ($response -ne "y" -and $response -ne "Y") {
        Write-Host "[!] 下载已取消" -ForegroundColor Yellow
        $needDownload = $false
        
        # 检查是否需要解压
        if (Test-Path $EXTRACT_DIR) {
            Write-Host "[i] 文件已解压，无需操作" -ForegroundColor Green
            exit 0
        }
    } else {
        Remove-Item $ZIP_FILE -Force
    }
}

# 下载文件
if ($needDownload) {
    Write-Host "[->] 开始下载 UV..." -ForegroundColor Cyan
    Write-Host ""

    try {
        # 使用 Invoke-WebRequest 下载
        $webClient = New-Object System.Net.WebClient
        $webClient.Headers.Add("User-Agent", "PowerShell")
        
        # 显示进度
        $startTime = Get-Date
        Write-Host "    下载中..." -ForegroundColor Gray
        
        $webClient.DownloadFile($DOWNLOAD_URL, $ZIP_FILE)
        
        $endTime = Get-Date
        $duration = ($endTime - $startTime).TotalSeconds
        $fileSize = (Get-Item $ZIP_FILE).Length / 1MB
        
        Write-Host ""
        Write-Host "[v] 下载完成!" -ForegroundColor Green
        Write-Host "    文件大小: $([math]::Round($fileSize, 2)) MB" -ForegroundColor Gray
        Write-Host "    耗时: $([math]::Round($duration, 2)) 秒" -ForegroundColor Gray
        Write-Host "    平均速度: $([math]::Round($fileSize / $duration, 2)) MB/s" -ForegroundColor Gray
        
    } catch {
        Write-Host ""
        Write-Host "[x] 下载失败: $_" -ForegroundColor Red
        Write-Host ""
        Write-Host "故障排除:" -ForegroundColor Yellow
        Write-Host "  1. 检查网络连接" -ForegroundColor Gray
        Write-Host "  2. 检查防火墙设置" -ForegroundColor Gray
        Write-Host "  3. 尝试使用代理" -ForegroundColor Gray
        Write-Host "  4. 手动下载: $DOWNLOAD_URL" -ForegroundColor Gray
        exit 1
    }
}

# 解压文件
Write-Host ""
Write-Host "[->] 解压文件..." -ForegroundColor Cyan

try {
    # 删除旧的解压目录
    if (Test-Path $EXTRACT_DIR) {
        Remove-Item -Path $EXTRACT_DIR -Recurse -Force
    }
    
    # 解压
    Expand-Archive -Path $ZIP_FILE -DestinationPath $EXTRACT_DIR -Force
    
    Write-Host "[v] 解压完成!" -ForegroundColor Green
    Write-Host "    解压位置: $EXTRACT_DIR" -ForegroundColor Gray
    
    # 列出解压的文件
    Write-Host ""
    Write-Host "[i] 解压内容:" -ForegroundColor Cyan
    Get-ChildItem -Path $EXTRACT_DIR -Recurse | ForEach-Object {
        $relativePath = $_.FullName.Replace($EXTRACT_DIR, "").TrimStart("\")
        if ($_.PSIsContainer) {
            Write-Host "    [DIR]  $relativePath" -ForegroundColor Blue
        } else {
            $size = $_.Length / 1KB
            Write-Host "    [FILE] $relativePath ($([math]::Round($size, 2)) KB)" -ForegroundColor Gray
        }
    }
    
    Write-Host ""
    Write-Host "[v] UV 下载和解压完成!" -ForegroundColor Green
    Write-Host ""
    Write-Host "下一步:" -ForegroundColor Yellow
    Write-Host "  1. 运行 check.ps1 检查状态" -ForegroundColor Gray
    Write-Host "  2. 运行 install.ps1 安装到系统" -ForegroundColor Gray
    
} catch {
    Write-Host ""
    Write-Host "[x] 解压失败: $_" -ForegroundColor Red
    exit 1
}

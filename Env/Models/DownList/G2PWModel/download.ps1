#Requires -Version 5.1
# G2PWModel 下载脚本
# 功能：仅下载模型文件到临时目录，不解压

[CmdletBinding()]
param(
    [Parameter()]
    [string]$OutputPath = "",

    [Parameter()]
    [switch]$SkipExisting
)

# 设置控制台编码
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# 设置错误处理
$ErrorActionPreference = "Stop"

# 设置 TLS 1.2
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# 加载 System.Net.Http 程序集（用于 HttpClient）
Add-Type -AssemblyName System.Net.Http

# 清屏并显示标题
Clear-Host
Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  G2PWModel 模型下载工具" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# 配置
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WorkspaceRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $ScriptDir)))
$Repo = "XXXXRT/GPT-SoVITS-Pretrained"
$FileName = "G2PWModel.zip"
$HfEndpoint = "https://hf-mirror.com"

# 加载环境变量
$EnvFile = Join-Path $WorkspaceRoot "Env\.env"
if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^HF_ENDPOINT=(.+)$') {
            $HfEndpoint = $matches[1]
        }
    }
}

$DownloadUrl = "$HfEndpoint/$Repo/resolve/main/$FileName"

# 确定输出路径
if ([string]::IsNullOrEmpty($OutputPath)) {
    $OutputPath = Join-Path $env:TEMP "G2PWModel_$([Guid]::NewGuid().ToString().Substring(0,8)).zip"
}

# 显示配置信息
Write-Host "下载配置" -ForegroundColor Yellow
Write-Host "----------------------------------------------" -ForegroundColor DarkGray
Write-Host "  模型仓库: $Repo" -ForegroundColor White
Write-Host "  文件名:   $FileName" -ForegroundColor White
Write-Host "  镜像端点: $HfEndpoint" -ForegroundColor White
Write-Host "  保存路径: $OutputPath" -ForegroundColor White
Write-Host "----------------------------------------------" -ForegroundColor DarkGray
Write-Host ""

# 检查是否已存在
if ($SkipExisting -and (Test-Path $OutputPath)) {
    Write-Host "文件已存在，跳过下载" -ForegroundColor Green
    Write-Host ""
    exit 0
}

# 创建输出目录
$OutputDir = Split-Path -Parent $OutputPath
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

# 使用 HttpClient 进行流式下载，支持进度显示
Write-Host "开始下载..." -ForegroundColor Green
Write-Host ""

# 创建 HttpClient
$httpClient = New-Object System.Net.Http.HttpClient
$httpClient.Timeout = [TimeSpan]::FromMinutes(30)

# 开始下载
try {
    $startTime = Get-Date
    $lastUpdateTime = $startTime
    $lastBytes = 0

    # 发送请求
    $response = $httpClient.GetAsync($DownloadUrl, [System.Net.Http.HttpCompletionOption]::ResponseHeadersRead).Result
    $response.EnsureSuccessStatusCode()

    # 获取文件总大小
    $contentLength = $response.Content.Headers.ContentLength
    if ($contentLength) {
        $totalSizeMB = $contentLength / 1MB
        Write-Host "文件大小: $([math]::Round($totalSizeMB, 2)) MB" -ForegroundColor Gray
        Write-Host ""
    }

    # 创建文件流
    $fileStream = [System.IO.File]::Create($OutputPath)
    $contentStream = $response.Content.ReadAsStreamAsync().Result

    # 缓冲区
    $buffer = New-Object byte[] 8192
    $totalBytesRead = 0
    $bytesRead = 0

    # 循环读取并写入
    while (($bytesRead = $contentStream.Read($buffer, 0, $buffer.Length)) -gt 0) {
        $fileStream.Write($buffer, 0, $bytesRead)
        $totalBytesRead += $bytesRead

        # 每0.5秒更新一次进度
        $currentTime = Get-Date
        $timeDiff = ($currentTime - $lastUpdateTime).TotalSeconds

        if ($timeDiff -ge 0.5 -or $bytesRead -lt $buffer.Length) {
            $receivedMB = $totalBytesRead / 1MB

            if ($contentLength) {
                $percent = [math]::Min(100, [math]::Round(($totalBytesRead / $contentLength) * 100, 1))
                $speedMBps = (($totalBytesRead - $lastBytes) / $timeDiff) / 1MB

                # 计算ETA
                if ($speedMBps -gt 0) {
                    $remainingBytes = $contentLength - $totalBytesRead
                    $etaSeconds = $remainingBytes / ($speedMBps * 1MB)
                    $eta = [TimeSpan]::FromSeconds($etaSeconds)
                    $etaStr = "{0:D2}:{1:D2}" -f $eta.Minutes, $eta.Seconds
                } else {
                    $etaStr = "--:--"
                }

                # 绘制进度条
                $barWidth = 40
                $filled = [math]::Floor($barWidth * $percent / 100)
                $empty = $barWidth - $filled
                $bar = "=" * $filled + "-" * $empty

                Write-Host "`r  进度: [$bar] $percent% | $([math]::Round($receivedMB, 1))/$([math]::Round($totalSizeMB, 1)) MB | $([math]::Round($speedMBps, 1)) MB/s | ETA: $etaStr" -NoNewline -ForegroundColor Cyan
            } else {
                Write-Host "`r  已下载: $([math]::Round($receivedMB, 2)) MB" -NoNewline -ForegroundColor Cyan
            }

            $lastUpdateTime = $currentTime
            $lastBytes = $totalBytesRead
        }
    }

    # 关闭流
    $fileStream.Close()
    $contentStream.Close()
    $httpClient.Dispose()

    # 计算总统计
    $endTime = Get-Date
    $totalDuration = $endTime - $startTime
    $fileInfo = Get-Item $OutputPath
    $fileSizeMB = $fileInfo.Length / 1MB
    $avgSpeed = $fileSizeMB / $totalDuration.TotalSeconds

    # 显示完成信息
    Write-Host ""
    Write-Host ""
    Write-Host "==================================================" -ForegroundColor Green
    Write-Host "  下载完成！" -ForegroundColor Green
    Write-Host "==================================================" -ForegroundColor Green
    Write-Host "  文件大小: $([math]::Round($fileSizeMB, 2)) MB" -ForegroundColor White
    Write-Host "  总用时:   $($totalDuration.ToString('mm\:ss'))" -ForegroundColor White
    Write-Host "  平均速度: $([math]::Round($avgSpeed, 2)) MB/s" -ForegroundColor White
    Write-Host "  保存位置: $OutputPath" -ForegroundColor White
    Write-Host "==================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "提示: 使用 install.ps1 安装此文件" -ForegroundColor Yellow
    Write-Host "   示例: .\install.ps1 \"$OutputPath\"" -ForegroundColor DarkGray
    Write-Host ""

    exit 0

} catch {
    # 清理资源
    if ($fileStream) { $fileStream.Close() }
    if ($contentStream) { $contentStream.Close() }
    if ($httpClient) { $httpClient.Dispose() }

    Write-Host ""
    Write-Host ""
    Write-Host "==================================================" -ForegroundColor Red
    Write-Host "  下载失败！" -ForegroundColor Red
    Write-Host "==================================================" -ForegroundColor Red
    Write-Host "  错误信息: $_.Exception.Message" -ForegroundColor White
    Write-Host "==================================================" -ForegroundColor Red
    Write-Host ""

    # 清理失败的文件
    if (Test-Path $OutputPath) {
        Remove-Item $OutputPath -Force -ErrorAction SilentlyContinue
    }

    exit 1
}

#Requires -Version 5.1
# MonGSV 项目打包脚本
# 功能：使用 7-Zip 打包项目，排除 .tarignore 中指定的文件

[CmdletBinding()]
param(
    [Parameter()]
    [string]$OutputFile = "",

    [Parameter()]
    [string]$SourceDir = ".",

    [Parameter()]
    [switch]$UseTar = $false
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
Write-Host "  MonGSV 项目打包工具" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# 查找 7-Zip
function Find-7Zip {
    $possiblePaths = @(
        "${env:ProgramFiles}\7-Zip\7z.exe",
        "${env:ProgramFiles(x86)}\7-Zip\7z.exe",
        "${env:LOCALAPPDATA}\Programs\7-Zip\7z.exe",
        "${env:USERPROFILE}\scoop\apps\7zip\current\7z.exe",
        "${env:USERPROFILE}\AppData\Local\Microsoft\WinGet\Packages\7zip.7zip_Microsoft.Winget.Source_8wekyb3d8bbwe\7z.exe"
    )

    # 检查 PATH 环境变量
    $path7z = Get-Command "7z.exe" -ErrorAction SilentlyContinue
    if ($path7z) {
        return $path7z.Source
    }

    # 检查常见路径
    foreach ($path in $possiblePaths) {
        if (Test-Path $path) {
            return $path
        }
    }

    return $null
}

# 解析 .tarignore 文件
function Get-IgnorePatterns {
    param([string]$IgnoreFile)

    $patterns = @()

    if (-not (Test-Path $IgnoreFile)) {
        Write-Warning "未找到忽略文件: $IgnoreFile"
        return $patterns
    }

    $lines = Get-Content $IgnoreFile -Encoding UTF8

    foreach ($line in $lines) {
        $trimmed = $line.Trim()

        # 跳过空行和注释
        if ([string]::IsNullOrWhiteSpace($trimmed)) { continue }
        if ($trimmed.StartsWith("#")) { continue }

        # 移除目录标记 / 后缀
        if ($trimmed.EndsWith("/")) {
            $trimmed = $trimmed.TrimEnd("/")
        }

        # 添加到模式列表
        $patterns += $trimmed
    }

    return $patterns
}

# 构建 7-Zip 排除参数
function Build-ExcludeArgs {
    param([array]$Patterns)

    $excludeArgs = @()

    foreach ($pattern in $Patterns) {
        # 7-Zip 使用 -x! 来排除文件
        # 处理目录模式
        if ($pattern -match '\*$') {
            # 已经是通配符模式
            $excludeArgs += "-x!$pattern"
        }
        else {
            # 同时排除文件和目录
            $excludeArgs += "-x!$pattern"
            $excludeArgs += "-x!$pattern\*"
        }
    }

    return $excludeArgs
}

# 主程序
$7zipPath = Find-7Zip

if (-not $7zipPath) {
    Write-Host "错误: 未找到 7-Zip" -ForegroundColor Red
    Write-Host ""
    Write-Host "请确保 7-Zip 已安装，或手动指定路径:" -ForegroundColor Yellow
    Write-Host "  1. 添加到 PATH 环境变量" -ForegroundColor Gray
    Write-Host "  2. 安装到默认位置: C:\Program Files\7-Zip\" -ForegroundColor Gray
    Write-Host ""
    exit 1
}

Write-Host "找到 7-Zip: $7zipPath" -ForegroundColor Green
Write-Host ""

# 解析源目录
$SourceDir = Resolve-Path $SourceDir
Write-Host "源目录: $SourceDir" -ForegroundColor White

# 查找 .tarignore 文件
$ignoreFile = Join-Path $SourceDir ".tarignore"
$patterns = Get-IgnorePatterns -IgnoreFile $ignoreFile

Write-Host "加载忽略规则: $($patterns.Count) 条" -ForegroundColor White
if ($patterns.Count -gt 0) {
    Write-Host "  - $($patterns[0..4] -join ', ')$(if ($patterns.Count -gt 5) { ', ...' })" -ForegroundColor Gray
}
Write-Host ""

# 构建输出文件名
if ([string]::IsNullOrEmpty($OutputFile)) {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $folderName = Split-Path $SourceDir -Leaf

    if ($UseTar) {
        $OutputFile = "${folderName}_${timestamp}.tar.gz"
    }
    else {
        $OutputFile = "${folderName}_${timestamp}.7z"
    }
}

# 确保输出文件是绝对路径
if (-not [System.IO.Path]::IsPathRooted($OutputFile)) {
    $OutputFile = Join-Path (Get-Location) $OutputFile
}

$OutputFile = [System.IO.Path]::GetFullPath($OutputFile)

Write-Host "输出文件: $OutputFile" -ForegroundColor White
Write-Host ""

# 显示将被打包的文件夹
Write-Host "将被打包的文件夹:" -ForegroundColor Green
$items = Get-ChildItem -Path $SourceDir -Directory | Where-Object {
    $name = $_.Name
    $excluded = $false
    foreach ($pattern in $patterns) {
        # 使用区分大小写的比较
        if ($name -ceq $pattern -or ($pattern -match '[*?]' -and $name -clike $pattern)) {
            $excluded = $true
            break
        }
    }
    -not $excluded
}
if ($items) {
    $items | ForEach-Object { Write-Host "  ✓ $($_.Name)" -ForegroundColor White }
} else {
    Write-Host "  (无)" -ForegroundColor Gray
}
Write-Host ""

# 显示被排除的文件夹
Write-Host "被排除的文件夹:" -ForegroundColor Red
$excludedItems = Get-ChildItem -Path $SourceDir -Directory | Where-Object {
    $name = $_.Name
    $excluded = $false
    $matchedPattern = ""
    foreach ($pattern in $patterns) {
        # 使用区分大小写的比较
        if ($name -ceq $pattern -or ($pattern -match '[*?]' -and $name -clike $pattern)) {
            $excluded = $true
            $matchedPattern = $pattern
            break
        }
    }
    if ($excluded) {
        Write-Host "  ✗ $name (匹配: $matchedPattern)" -ForegroundColor DarkGray
    }
    $excluded
}
if (-not $excludedItems) {
    Write-Host "  (无)" -ForegroundColor Gray
}
Write-Host ""

# 确认
Write-Host "准备打包..." -ForegroundColor Cyan
Write-Host ""

# 创建临时排除列表文件（避免命令行过长）
$tempExcludeFile = Join-Path $env:TEMP "pack_exclude_$(Get-Random).txt"
$patterns | ForEach-Object { "$_" } | Out-File -FilePath $tempExcludeFile -Encoding UTF8

Write-Host "排除文件内容:" -ForegroundColor Gray
Get-Content $tempExcludeFile | ForEach-Object { Write-Host "  - $_" -ForegroundColor DarkGray }
Write-Host ""

$archiveType = if ($UseTar) { "tar" } else { "7z" }

# 构建参数数组（-bb0 表示不显示文件列表，只显示错误和统计信息）
$7zArgs = @(
    "a",                                    # 添加文件到压缩包
    "-t$archiveType",                       # 压缩类型
    "-m0=lzma2",                            # 压缩方法
    "-mx=5",                                # 压缩级别 (0-9)
    "-mhe=on",                              # 加密文件头
    "-slp",                                 # 使用大内存页
    "-bb0",                                 # 不显示详细文件列表
    "-scsUTF-8",                            # 使用 UTF-8 编码
    "-xr@$tempExcludeFile",                 # 从文件读取排除列表
    "$OutputFile",                          # 输出文件
    "$SourceDir\*"                          # 源目录
)

Write-Host "正在打包..." -ForegroundColor Yellow
Write-Host ""

# 执行打包
try {
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

    # 执行 7-Zip 并捕获输出
    $process = Start-Process -FilePath "$7zipPath" -ArgumentList $7zArgs -Wait -PassThru -NoNewWindow -RedirectStandardOutput (Join-Path $env:TEMP "7z_out.txt") -RedirectStandardError (Join-Path $env:TEMP "7z_err.txt")

    # 只显示最后的统计信息
    $output = Get-Content (Join-Path $env:TEMP "7z_out.txt") -ErrorAction SilentlyContinue
    $output | Select-Object -Last 5 | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }

    $stopwatch.Stop()

    Write-Host ""
    Write-Host "==================================================" -ForegroundColor Green
    Write-Host "  打包成功！" -ForegroundColor Green
    Write-Host "==================================================" -ForegroundColor Green
    Write-Host "  输出文件: $OutputFile" -ForegroundColor White

    if (Test-Path $OutputFile) {
        $fileSize = (Get-Item $OutputFile).Length
        Write-Host "  文件大小: $([math]::Round($fileSize / 1MB, 2)) MB" -ForegroundColor White
    }

    Write-Host "  用时: $($stopwatch.Elapsed.ToString('mm\:ss'))" -ForegroundColor White
    Write-Host "==================================================" -ForegroundColor Green
    Write-Host ""

    exit 0
}
catch {
    Write-Host ""
    Write-Host "==================================================" -ForegroundColor Red
    Write-Host "  打包失败！" -ForegroundColor Red
    Write-Host "==================================================" -ForegroundColor Red
    Write-Host "  错误信息: $($_.Exception.Message)" -ForegroundColor White
    Write-Host "==================================================" -ForegroundColor Red
    Write-Host ""

    exit 1
}
finally {
    # 清理临时文件
    if (Test-Path $tempExcludeFile) {
        Remove-Item $tempExcludeFile -Force -ErrorAction SilentlyContinue
    }
    Remove-Item (Join-Path $env:TEMP "7z_out.txt") -Force -ErrorAction SilentlyContinue
    Remove-Item (Join-Path $env:TEMP "7z_err.txt") -Force -ErrorAction SilentlyContinue
}

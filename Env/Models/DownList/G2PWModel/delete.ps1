# G2PWModel 删除脚本
# 纯 PowerShell 实现

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# 获取工作区根目录（向上4层）
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WorkspaceRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $ScriptDir)))

# 加载 .env 配置
$EnvFile = Join-Path $WorkspaceRoot "Env\.env"
$TargetPath = "GPT_SoVITS\text\G2PWModel"

if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^G2PW_MODEL_PATH=(.+)$') {
            $TargetPath = $matches[1]
        }
    }
}

$FullPath = Join-Path $WorkspaceRoot $TargetPath

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  [删除] 中文字音转换模型" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  路径: $FullPath" -ForegroundColor Gray
Write-Host ""

if (-not (Test-Path $FullPath)) {
    Write-Host "  [!] 模型不存在，无需删除" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "==================================================" -ForegroundColor Green
    Write-Host "  [结果] ✓ 无需删除" -ForegroundColor Green
    Write-Host "==================================================" -ForegroundColor Green
    exit 0
}

Write-Host "  [!] 警告: 此操作将删除 G2PWModel 模型文件" -ForegroundColor Yellow
Write-Host ""

try {
    Write-Host "  [→] 正在删除..." -ForegroundColor Cyan
    Remove-Item -Path $FullPath -Recurse -Force
    Write-Host "  [✓] 删除完成" -ForegroundColor Green
    Write-Host ""
    Write-Host "==================================================" -ForegroundColor Green
    Write-Host "  [结果] ✓ 删除成功" -ForegroundColor Green
    Write-Host "==================================================" -ForegroundColor Green
    exit 0
    
} catch {
    Write-Host ""
    Write-Host "  [✗] 删除失败: $_" -ForegroundColor Red
    Write-Host "==================================================" -ForegroundColor Red
    Write-Host "  [结果] ✗ 删除失败" -ForegroundColor Red
    Write-Host "==================================================" -ForegroundColor Red
    exit 1
}

# G2PWModel 检查脚本
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

# 定义需要检查的文件
$RequiredFiles = @(
    "g2pW.onnx",
    "config.py",
    "char_bopomofo_dict.json",
    "MONOPHONIC_CHARS.txt",
    "POLYPHONIC_CHARS.txt"
)

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  [检查] 中文字音转换模型" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  路径: $FullPath" -ForegroundColor Gray
Write-Host ""

$AllExist = $true

foreach ($file in $RequiredFiles) {
    $FilePath = Join-Path $FullPath $file
    if (Test-Path $FilePath) {
        $Size = 0
        if ((Get-Item $FilePath).PSIsContainer) {
            $Size = (Get-ChildItem $FilePath -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1MB
        } else {
            $Size = (Get-Item $FilePath).Length / 1MB
        }
        Write-Host "  [✓] $file ($([math]::Round($Size, 1)) MB)" -ForegroundColor Green
    } else {
        Write-Host "  [✗] $file - 缺失" -ForegroundColor Red
        $AllExist = $false
    }
}

Write-Host "==================================================" -ForegroundColor Cyan
if ($AllExist) {
    Write-Host "  [结果] ✓ 所有文件检查通过" -ForegroundColor Green
    exit 0
} else {
    Write-Host "  [结果] ✗ 部分文件缺失" -ForegroundColor Red
    exit 1
}

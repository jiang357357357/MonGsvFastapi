[CmdletBinding()]
param(
    [switch]$OnlyBackend,
    [switch]$OnlyFrontend
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = (Resolve-Path (Join-Path $scriptDir "..\..")).Path
$ecosystem = Join-Path $scriptDir "ecosystem.config.cjs"
$logDir = Join-Path $projectRoot "Data\Logs\PM2"

New-Item -ItemType Directory -Path $logDir -Force | Out-Null

$pm2 = Get-Command pm2 -ErrorAction SilentlyContinue
if (-not $pm2) {
    $pm2 = Get-Command npx -ErrorAction SilentlyContinue
    if (-not $pm2) {
        throw "未找到 pm2 或 npx，请先安装 Node.js/PM2"
    }
    $pm2ArgsPrefix = @("pm2")
} else {
    $pm2ArgsPrefix = @()
}

$targets = @()
if ($OnlyBackend) {
    $targets += "MonGsvBackend"
}
if ($OnlyFrontend) {
    $targets += "MonGsvFrontend"
}

Set-Location $projectRoot

if ($targets.Count -eq 0) {
    & $pm2.Source @pm2ArgsPrefix start $ecosystem
} else {
    foreach ($target in $targets) {
        & $pm2.Source @pm2ArgsPrefix start $ecosystem --only $target
    }
}

& $pm2.Source @pm2ArgsPrefix status


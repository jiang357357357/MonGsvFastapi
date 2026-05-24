[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$pm2 = Get-Command pm2 -ErrorAction SilentlyContinue
if (-not $pm2) {
    $pm2 = Get-Command npx -ErrorAction SilentlyContinue
    if (-not $pm2) {
        throw "未找到 pm2 或 npx"
    }
    $pm2ArgsPrefix = @("pm2")
} else {
    $pm2ArgsPrefix = @()
}

& $pm2.Source @pm2ArgsPrefix status


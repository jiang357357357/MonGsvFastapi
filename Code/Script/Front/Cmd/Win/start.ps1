[CmdletBinding()]
param(
    [ValidateSet("dev", "prod", "production", "preview")]
    [string]$Mode = "dev",
    [int]$Port
)

$ErrorActionPreference = "Stop"

function Find-RepoRoot {
    param([string]$StartPath)
    $current = (Resolve-Path $StartPath).Path
    while ($true) {
        if (Test-Path (Join-Path $current ".monconfig")) {
            return $current
        }
        $parent = Split-Path $current -Parent
        if ($parent -eq $current -or [string]::IsNullOrWhiteSpace($parent)) {
            throw "未找到 .monconfig"
        }
        $current = $parent
    }
}

function Get-MonConfigValue {
    param(
        [string]$RepoRoot,
        [string]$Section,
        [string]$Key,
        [string]$Default = ""
    )

    $configPath = Join-Path $RepoRoot ".monconfig"
    $currentSection = ""
    foreach ($rawLine in Get-Content -LiteralPath $configPath -Encoding UTF8) {
        $line = $rawLine.Trim()
        if (-not $line -or $line.StartsWith("#")) {
            continue
        }
        if ($line.StartsWith("[") -and $line.EndsWith("]")) {
            $currentSection = $line.Substring(1, $line.Length - 2).Trim()
            continue
        }
        if ($currentSection -ne $Section) {
            continue
        }
        $commentIndex = $line.IndexOf("#")
        if ($commentIndex -ge 0) {
            $line = $line.Substring(0, $commentIndex).Trim()
        }
        if (-not $line.Contains("=")) {
            continue
        }
        $parts = $line.Split("=", 2)
        if ($parts[0].Trim() -eq $Key) {
            return $parts[1].Trim()
        }
    }
    return $Default
}

$repoRoot = Find-RepoRoot $PSScriptRoot
$frontendDir = Join-Path $repoRoot "Code\GptSov_Front"
if (-not (Test-Path $frontendDir)) {
    throw "前端目录不存在: $frontendDir"
}

if (-not $Port) {
    $Port = [int](Get-MonConfigValue -RepoRoot $repoRoot -Section "frontend" -Key "PORT" -Default "40031")
}

$backendPort = Get-MonConfigValue -RepoRoot $repoRoot -Section "server" -Key "PORT" -Default "40302"
$env:MON_GSV_PORT = $backendPort
$env:FRONTEND_PORT = [string]$Port

$npm = "npm.cmd"
$npx = "npx.cmd"

Set-Location $frontendDir

if (-not (Test-Path (Join-Path $frontendDir "node_modules"))) {
    if (Test-Path (Join-Path $frontendDir "package-lock.json")) {
        & $npm ci
    } else {
        & $npm install
    }
}

Write-Host "MonGSV Frontend"
Write-Host "Repo: $repoRoot"
Write-Host "URL : http://127.0.0.1:$Port"
Write-Host "Mode: $Mode"
Write-Host ""

if ($Mode -in @("prod", "production", "preview")) {
    & $npm run build
    & $npx vite preview --host 0.0.0.0 --port $Port
} else {
    & $npm run dev -- --host 0.0.0.0 --port $Port
}


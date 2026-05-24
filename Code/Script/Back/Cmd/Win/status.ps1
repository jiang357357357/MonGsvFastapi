[CmdletBinding()]
param(
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
if (-not $Port) {
    $Port = [int](Get-MonConfigValue -RepoRoot $repoRoot -Section "server" -Key "PORT" -Default "40302")
}

Write-Host "Backend port: $Port"
$connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if (-not $connections) {
    Write-Host "Status: port is free"
    exit 0
}

Write-Host "Status: port is occupied"
$processIds = $connections | Select-Object -ExpandProperty OwningProcess -Unique
foreach ($processId in $processIds) {
    try {
        $process = Get-Process -Id $processId -ErrorAction Stop
        Write-Host ("Process: PID={0} Name={1}" -f $process.Id, $process.ProcessName)
    } catch {
        Write-Host ("Process: PID={0} exited" -f $processId)
    }
}

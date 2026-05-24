[CmdletBinding()]
param(
    [string]$HostName,
    [int]$Port,
    [switch]$Reload,
    [switch]$NoReload
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
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    $pythonExe = "python"
}

if (-not $HostName) {
    $HostName = Get-MonConfigValue -RepoRoot $repoRoot -Section "server" -Key "HOST" -Default "0.0.0.0"
}
if (-not $Port) {
    $Port = [int](Get-MonConfigValue -RepoRoot $repoRoot -Section "server" -Key "PORT" -Default "40302")
}

$gatewayEntry = Join-Path $repoRoot "Code\FastApi\Main\run_gateway.py"
$argsList = @($gatewayEntry, "start", "--host", $HostName, "--port", [string]$Port)
if ($Reload) {
    $argsList += "--reload"
}
if ($NoReload) {
    $argsList += "--no-reload"
}

Write-Host "MonGSV FastAPI Gateway"
Write-Host "Repo: $repoRoot"
Write-Host "URL : http://$HostName`:$Port"
Write-Host ""

Set-Location $repoRoot
& $pythonExe @argsList


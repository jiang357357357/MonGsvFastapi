[CmdletBinding()]
param(
    [switch]$NoBackend,
    [switch]$NoFrontend,
    [switch]$ReloadBackend,
    [ValidateSet("dev", "prod", "production", "preview")]
    [string]$FrontendMode = "dev"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path

if (-not $NoBackend) {
    $backendScript = Join-Path $repoRoot "Code\Script\Back\Cmd\Win\start.ps1"
    $backendCommand = "Set-Location `"$repoRoot`"; & `"$backendScript`""
    if ($ReloadBackend) {
        $backendCommand += " -Reload"
    }
    Start-Process powershell -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $backendCommand) -WorkingDirectory $repoRoot
}

if (-not $NoFrontend) {
    $frontendScript = Join-Path $repoRoot "Code\Script\Front\Cmd\Win\start.ps1"
    $frontendCommand = "Set-Location `"$repoRoot`"; & `"$frontendScript`" -Mode $FrontendMode"
    Start-Process powershell -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $frontendCommand) -WorkingDirectory $repoRoot
}

Write-Host "Start commands dispatched."


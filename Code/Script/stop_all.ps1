[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path

& (Join-Path $repoRoot "Code\Script\Front\Cmd\Win\stop.ps1")
& (Join-Path $repoRoot "Code\Script\Back\Cmd\Win\stop.ps1")


$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonCmd = Get-Command py -ErrorAction SilentlyContinue
if ($PythonCmd) {
    & py -3 (Join-Path $ScriptDir "check.py") @args
} else {
    & python (Join-Path $ScriptDir "check.py") @args
}
exit $LASTEXITCODE

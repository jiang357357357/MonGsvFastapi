$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonCmd = Get-Command py -ErrorAction SilentlyContinue
if ($PythonCmd) {
    & py -3 (Join-Path $ScriptDir "delete.py") @args
} else {
    & python (Join-Path $ScriptDir "delete.py") @args
}
exit $LASTEXITCODE

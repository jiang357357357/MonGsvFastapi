# Run by the temporary Windows test controller after Explorer opens MonGSV.exe.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = New-Object Text.UTF8Encoding($false)
$OutputEncoding = [Console]::OutputEncoding
$result = @{root=$root;success=$false;errors=@();time=(Get-Date).ToString('o')}
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$result.is_elevated = (New-Object Security.Principal.WindowsPrincipal($identity)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
try {
    $config = Get-Content -Raw (Join-Path $root 'config.json') | ConvertFrom-Json
    $backend = 'http://127.0.0.1:' + $config.backend_port
    $frontend = 'http://127.0.0.1:' + $config.frontend_port
    Status 'waiting-for-native-launch-health' @{backend=$backend;frontend=$frontend}
    $deadline = (Get-Date).AddSeconds(240)
    $health = $null
    while ((Get-Date) -lt $deadline) {
        try { $health = Invoke-RestMethod ($backend+'/health') -TimeoutSec 5; break } catch { Start-Sleep -Seconds 2 }
    }
    if (!$health) { throw 'Backend health never became ready after Explorer launch.' }
    $result.health_ready_at = (Get-Date).ToString('o')
    $result.health = $health
    $bad = @($health.services.PSObject.Properties | Where-Object { $_.Value.status -in @('error','load_error') })
    if ($bad.Count) { throw ('Gateway has service errors: '+(($bad | ForEach-Object {$_.Name+': '+$_.Value.error}) -join '; ')) }
    $page = Invoke-WebRequest -UseBasicParsing ($frontend+'/') -TimeoutSec 10
    $result.frontend_http = [int]$page.StatusCode
    if ($page.StatusCode -ne 200 -or $page.Content -notmatch 'id="root"') { throw 'Frontend index failed' }
    $runtime = Invoke-WebRequest -UseBasicParsing ($frontend+'/mon-config.js') -TimeoutSec 5
    $result.frontend_runtime_config = $runtime.Content
    if ($runtime.Content -notmatch ([string]$config.backend_port)) { throw 'Frontend used the wrong backend port' }
    $result.versions = Invoke-RestMethod ($backend+'/api/models/versions/from-enum/') -TimeoutSec 10
    $result.processes = @(Get-CimInstance Win32_Process | Where-Object {
        $_.ExecutablePath -and $_.ExecutablePath.StartsWith($root,[StringComparison]::OrdinalIgnoreCase)
    } | Select-Object ProcessId,ParentProcessId,Name,ExecutablePath,CommandLine)
    if (!@($result.processes | Where-Object {$_.Name -eq 'MonGSV.exe'}).Count) { throw 'Native launcher is not alive' }
    $result.browser = @(Get-CimInstance Win32_Process -Filter "Name='msedge.exe'" | Select-Object ProcessId,CommandLine)
    $result.browser_windows = @(Get-Process msedge -ErrorAction SilentlyContinue | Where-Object {$_.MainWindowHandle -ne 0} | Select-Object Id,MainWindowTitle)
    $stdout = Join-Path $reports 'diagnose-stdout.json'
    $stderr = Join-Path $reports 'diagnose-stderr.txt'
    $diag = Start-Process -FilePath (Join-Path $root 'runtime\python.exe') -ArgumentList @('-s',('"'+$root+'\diagnose.py"')) -PassThru -Wait -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    Upload $stdout
    Upload $stderr
    $result.diagnostics_exit_code = $diag.ExitCode
    if ($diag.ExitCode -ne 0) { throw ('Windows native dependency diagnostics failed: '+$diag.ExitCode) }
    $result.diagnostics = Get-Content -Raw (Join-Path $root 'data\diagnostics.json') | ConvertFrom-Json
    $result.success = $true
} catch {
    $result.errors += $_.ToString()
} finally {
    $result.completed_at = (Get-Date).ToString('o')
    $path = Join-Path $reports 'startup-result.json'
    $result | ConvertTo-Json -Depth 12 | Set-Content -Encoding UTF8 $path
    Upload $path
    $console = Join-Path $root 'data\launcher\console.log'
    if (Test-Path $console) {
        $snapshot = Join-Path $reports 'launcher-console.log'
        Get-Content -Raw -Encoding UTF8 $console | Set-Content -Encoding UTF8 $snapshot
        Upload $snapshot
    }
    Status 'startup-probe-finished' @{success=$result.success;errors=$result.errors}
}

$ErrorActionPreference = 'Stop'
$before = @(Get-CimInstance Win32_Process | Where-Object {
    $_.ExecutablePath -and $_.ExecutablePath.StartsWith($root,[StringComparison]::OrdinalIgnoreCase)
} | Select-Object -ExpandProperty ProcessId)
$stop = Start-Process -FilePath $env:ComSpec -WorkingDirectory $root -ArgumentList @('/d','/c','Stop.cmd') -PassThru -Wait
if ($stop.ExitCode -ne 0) { throw ('Stop request failed: '+$stop.ExitCode) }
$deadline = (Get-Date).AddSeconds(30)
do {
    Start-Sleep -Milliseconds 500
    $remaining = @(Get-CimInstance Win32_Process | Where-Object {
        $_.ExecutablePath -and $_.ExecutablePath.StartsWith($root,[StringComparison]::OrdinalIgnoreCase)
    })
} while ($remaining.Count -and (Get-Date) -lt $deadline)
if ($remaining.Count) { throw 'Owned application processes survived Stop.' }
if (Test-Path (Join-Path $root 'data\launcher\session.json')) { throw 'Launcher session file survived Stop.' }
$config = Get-Content -Raw (Join-Path $root 'config.json') | ConvertFrom-Json
foreach ($port in @($config.backend_port,$config.frontend_port)) {
    $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,[int]$port)
    try { $listener.Start() } finally { $listener.Stop() }
}
$result = @{success=$true;stop_cmd_exit_code=$stop.ExitCode;stopped_process_ids=$before;remaining_processes=0;ports_released=@($config.backend_port,$config.frontend_port);time=(Get-Date).ToString('o')}
$file = Join-Path $reports 'stop-result.json'
$result | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 $file
Upload $file
if ($StopOnly) { return }
$leaf = 'MonGSV space ' + [char]0x6D4B + [char]0x8BD5
$newRoot = Join-Path ([IO.Path]::GetDirectoryName($root)) $leaf
Move-Item -LiteralPath $root -Destination $newRoot
$config = Get-Content -Raw (Join-Path $newRoot 'config.json') | ConvertFrom-Json
$config.backend_port = 40322
$config.frontend_port = 40032
$config | ConvertTo-Json | Set-Content -Encoding UTF8 (Join-Path $newRoot 'config.json')
Set-Content -Encoding UTF8 (Join-Path $reports 'bundle-root.txt') $newRoot
Start-Process explorer.exe -ArgumentList ('/select,"'+$newRoot+'\MonGSV.exe"')
Status 'ready-for-unicode-custom-port-relaunch' @{root=$newRoot;backend_port=40322;frontend_port=40032}

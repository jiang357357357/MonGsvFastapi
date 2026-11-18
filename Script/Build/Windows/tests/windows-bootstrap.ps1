param([string]$Endpoint = 'http://192.168.122.1:40890')
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$root = Join-Path $env:USERPROFILE 'Desktop\MonGSV'
$reports = Join-Path $env:USERPROFILE 'MonGSV-test-results'
$archive = Join-Path $env:TEMP 'MonGSV-test.zip'
New-Item -ItemType Directory -Force $reports | Out-Null
function Upload([string]$Path, [string]$Name = '') {
    if (!$Name) { $Name = [IO.Path]::GetFileName($Path) }
    Invoke-WebRequest -UseBasicParsing -Method Put -InFile $Path -Uri ($Endpoint + '/reports/' + $Name) | Out-Null
}
function Status([string]$Stage, [object]$Details = $null) {
    $p = Join-Path $reports 'status.json'
    @{stage=$Stage;time=(Get-Date).ToString('o');details=$Details} | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 $p
    Upload $p
}
Start-Transcript -Path (Join-Path $reports 'bootstrap.log') -Force
try {
    $os = Get-CimInstance Win32_OperatingSystem
    $baseline = @{
        caption=$os.Caption;version=$os.Version;build=$os.BuildNumber;architecture=$os.OSArchitecture;
        cpu=(Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty Name);
        gpu=@(Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name);
        system_msvcp140_present=(Test-Path 'C:\Windows\System32\msvcp140.dll');
        python_command=@(Get-Command python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source);
        uv_command=@(Get-Command uv -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source)
    }
    $baseline | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 (Join-Path $reports 'baseline.json')
    Upload (Join-Path $reports 'baseline.json')
    Status 'downloading-package'
    & curl.exe --fail --silent --show-error --retry 2 --output $archive ($Endpoint + '/MonGSV-test.zip')
    if ($LASTEXITCODE) { throw ('Package download failed: '+$LASTEXITCODE) }
    Status 'extracting-package'
    New-Item -ItemType Directory -Force $root | Out-Null
    & tar.exe -xf $archive -C $root
    if ($LASTEXITCODE) { throw ('Package extraction failed: '+$LASTEXITCODE) }
    $hash = (Get-FileHash -Algorithm SHA256 (Join-Path $root 'MonGSV.exe')).Hash.ToLowerInvariant()
    Status 'ready-for-explorer-launch' @{root=$root;launcher_sha256=$hash}
    Set-Content -Encoding UTF8 (Join-Path $reports 'bundle-root.txt') $root
    Start-Process explorer.exe -ArgumentList ('/select,"'+$root+'\MonGSV.exe"')
    # An explicit local test command channel; no service or startup task is installed.
    $last = ''
    $deadline = (Get-Date).AddHours(2)
    while ((Get-Date) -lt $deadline -and !(Test-Path (Join-Path $reports 'stop-control'))) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri ($Endpoint+'/command.ps1') -TimeoutSec 10
            $body = $response.Content
            $sha = [Security.Cryptography.SHA256]::Create()
            $hash = [Convert]::ToBase64String($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($body)))
            $sha.Dispose()
            if ($hash -ne $last) {
                $last = $hash
                try {
                    $root = (Get-Content -Raw (Join-Path $reports 'bundle-root.txt')).Trim()
                    & ([ScriptBlock]::Create($body)) 2>&1 | Tee-Object -FilePath (Join-Path $reports 'command.log')
                    Status 'command-complete'
                } catch {
                    $_ | Out-String | Set-Content -Encoding UTF8 (Join-Path $reports 'command-error.txt')
                    Upload (Join-Path $reports 'command-error.txt')
                    Status 'command-failed' $_.ToString()
                }
                Upload (Join-Path $reports 'command.log')
            }
        } catch { }
        Start-Sleep -Seconds 2
    }
} catch {
    $_ | Out-String | Set-Content -Encoding UTF8 (Join-Path $reports 'bootstrap-error.txt')
    Upload (Join-Path $reports 'bootstrap-error.txt')
    Status 'bootstrap-failed' $_.ToString()
} finally {
    Stop-Transcript
    Upload (Join-Path $reports 'bootstrap.log')
}

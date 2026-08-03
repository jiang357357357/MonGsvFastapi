#Requires -Version 5.1

[CmdletBinding()]
param(
    [Parameter()]
    [string]$OutputFile = "",

    [Parameter()]
    [string]$SourceDir = "",

    [Parameter()]
    [switch]$UseTar,

    [Parameter()]
    [switch]$SkipFrontendBuild,

    [Parameter()]
    [Alias("h")]
    [switch]$Help
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"

function Find-WorkspaceRoot {
    param([string]$StartPath)

    $resolved = (Resolve-Path -LiteralPath $StartPath).Path
    if (Test-Path -LiteralPath $resolved -PathType Leaf) {
        $resolved = Split-Path -Parent $resolved
    }

    $current = $resolved
    while ($true) {
        if (Test-Path -LiteralPath (Join-Path $current ".monconfig")) {
            return $current
        }

        $parent = Split-Path -Parent $current
        if (-not $parent -or $parent -eq $current) {
            return $null
        }
        $current = $parent
    }
}

function Find-7Zip {
    $possiblePaths = @(
        "${env:ProgramFiles}\7-Zip\7z.exe",
        "${env:ProgramFiles(x86)}\7-Zip\7z.exe",
        "${env:LOCALAPPDATA}\Programs\7-Zip\7z.exe",
        "${env:USERPROFILE}\scoop\apps\7zip\current\7z.exe",
        "${env:USERPROFILE}\AppData\Local\Microsoft\WinGet\Packages\7zip.7zip_Microsoft.Winget.Source_8wekyb3d8bbwe\7z.exe"
    )

    $path7z = Get-Command "7z.exe" -ErrorAction SilentlyContinue
    if ($path7z) {
        return $path7z.Source
    }

    foreach ($path in $possiblePaths) {
        if (Test-Path -LiteralPath $path) {
            return $path
        }
    }

    return $null
}

function Invoke-Git {
    param(
        [string]$WorkingDirectory,
        [string[]]$ArgumentList
    )

    & git -C $WorkingDirectory @ArgumentList
    if ($LASTEXITCODE -ne 0) {
        throw "Git command failed with code ${LASTEXITCODE}: git -C `"$WorkingDirectory`" $($ArgumentList -join ' ')"
    }
}

function Get-GitValue {
    param(
        [string]$WorkingDirectory,
        [string[]]$ArgumentList
    )

    $output = @(& git -C $WorkingDirectory @ArgumentList 2>$null)
    $exitCode = $LASTEXITCODE
    $value = $output | Select-Object -First 1
    if ($exitCode -ne 0 -or [string]::IsNullOrWhiteSpace($value)) {
        throw "Could not read Git value: git -C `"$WorkingDirectory`" $($ArgumentList -join ' ')"
    }
    return $value.Trim()
}

function Convert-ToFileUri {
    param([string]$Path)

    $resolved = (Resolve-Path -LiteralPath $Path).Path
    if (-not $resolved.EndsWith([System.IO.Path]::DirectorySeparatorChar)) {
        $resolved += [System.IO.Path]::DirectorySeparatorChar
    }
    return ([uri]$resolved).AbsoluteUri
}

function Copy-WorkingTreeOverlay {
    param(
        [string]$Source,
        [string]$Destination,
        [string[]]$Patterns
    )

    $excludeDirectories = New-Object System.Collections.Generic.List[string]
    $excludeDirectories.Add(".git")
    foreach ($pattern in $Patterns) {
        $excludeDirectories.Add($pattern.Replace("/", "\"))
    }

    $arguments = @(
        $Source,
        $Destination,
        "/E",
        "/COPY:DAT",
        "/DCOPY:DAT",
        "/R:2",
        "/W:1",
        "/NFL",
        "/NDL",
        "/NJH",
        "/NJS",
        "/NP",
        "/XD"
    )
    $arguments += $excludeDirectories.ToArray()
    $arguments += "/XF"
    $arguments += $Patterns

    & robocopy @arguments | Out-Null
    if ($LASTEXITCODE -gt 7) {
        throw "Working-tree overlay failed with robocopy code $LASTEXITCODE."
    }
}

function Apply-WorkingTreeDiff {
    param(
        [string]$Source,
        [string]$Destination,
        [string[]]$ExcludedPaths = @()
    )

    $patchFile = Join-Path $env:TEMP ("mongsv_worktree_{0}.patch" -f ([guid]::NewGuid().ToString("N")))
    try {
        $arguments = @("diff", "--binary", "HEAD", "--output=$patchFile", "--", ".")
        foreach ($path in $ExcludedPaths) {
            $arguments += ":(exclude)$path"
        }
        Invoke-Git -WorkingDirectory $Source -ArgumentList $arguments

        if ((Test-Path -LiteralPath $patchFile -PathType Leaf) -and (Get-Item -LiteralPath $patchFile).Length -gt 0) {
            Invoke-Git -WorkingDirectory $Destination -ArgumentList @("apply", "--binary", "--whitespace=nowarn", $patchFile)
        }
    }
    finally {
        Remove-Item -LiteralPath $patchFile -Force -ErrorAction SilentlyContinue
    }
}

function Assert-CleanTrackedWorkingTree {
    param(
        [string]$WorkingDirectory,
        [string]$DisplayName,
        [switch]$IgnoreDirtySubmodules
    )

    $arguments = @("status", "--porcelain", "--untracked-files=no")
    if ($IgnoreDirtySubmodules) {
        $arguments += "--ignore-submodules=dirty"
    }
    $changes = @(& git -C $WorkingDirectory @arguments)
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        throw "Could not inspect tracked changes in $DisplayName."
    }
    if ($changes.Count -gt 0) {
        $summary = ($changes | Select-Object -First 10) -join [Environment]::NewLine
        throw @"
$DisplayName contains uncommitted tracked changes. Commit them before building an updateable release package.
$summary
"@
    }
}

function New-ShallowReleaseTree {
    param(
        [string]$Source,
        [string]$Destination,
        [string[]]$Patterns
    )

    $git = Get-Command "git.exe" -ErrorAction SilentlyContinue
    if (-not $git) {
        $git = Get-Command "git" -ErrorAction SilentlyContinue
    }
    if (-not $git) {
        throw "Could not find Git. A shallow release repository cannot be created."
    }

    $insideWorkTree = Get-GitValue -WorkingDirectory $Source -ArgumentList @("rev-parse", "--is-inside-work-tree")
    if ($insideWorkTree -ne "true") {
        throw "Source directory is not a Git working tree: $Source"
    }
    $branch = Get-GitValue -WorkingDirectory $Source -ArgumentList @("branch", "--show-current")
    $commit = Get-GitValue -WorkingDirectory $Source -ArgumentList @("rev-parse", "HEAD")
    $origin = Get-GitValue -WorkingDirectory $Source -ArgumentList @("remote", "get-url", "origin")
    $sourceUri = Convert-ToFileUri -Path $Source

    Assert-CleanTrackedWorkingTree `
        -WorkingDirectory $Source `
        -DisplayName "Main repository" `
        -IgnoreDirtySubmodules

    Write-Host "[Git] Creating shallow release repository..." -ForegroundColor Cyan
    & $git.Source clone --quiet --depth 1 --branch $branch --no-recurse-submodules $sourceUri $Destination
    if ($LASTEXITCODE -ne 0) {
        throw "Could not create shallow release repository (git clone exit $LASTEXITCODE)."
    }
    Invoke-Git -WorkingDirectory $Destination -ArgumentList @("remote", "set-url", "origin", $origin)

    $stagedSubmodules = New-Object System.Collections.Generic.List[object]
    $submoduleLines = & git -C $Source config --file .gitmodules --get-regexp "^submodule\..*\.path$" 2>$null
    if ($LASTEXITCODE -eq 0) {
        foreach ($line in $submoduleLines) {
            if ($line -notmatch "^(\S+)\s+(.+)$") {
                continue
            }

            $pathKey = $Matches[1]
            $relativePath = $Matches[2].Trim()
            $submoduleName = $pathKey.Substring("submodule.".Length)
            $submoduleName = $submoduleName.Substring(0, $submoduleName.Length - ".path".Length)
            $submoduleSource = Join-Path $Source $relativePath
            $submoduleDestination = Join-Path $Destination $relativePath
            if (-not (Test-Path -LiteralPath $submoduleSource -PathType Container)) {
                throw "Submodule working tree does not exist: $submoduleSource"
            }

            $submoduleCommit = Get-GitValue -WorkingDirectory $Source -ArgumentList @("rev-parse", "HEAD:$relativePath")
            $submoduleBranch = Get-GitValue -WorkingDirectory $submoduleSource -ArgumentList @("branch", "--show-current")
            $submoduleOrigin = (& git -C $Source config --file .gitmodules --get "submodule.$submoduleName.url").Trim()
            $submoduleUri = Convert-ToFileUri -Path $submoduleSource

            Assert-CleanTrackedWorkingTree `
                -WorkingDirectory $submoduleSource `
                -DisplayName ("Submodule {0}" -f $relativePath)

            if (Test-Path -LiteralPath $submoduleDestination) {
                Remove-Item -LiteralPath $submoduleDestination -Recurse -Force
            }
            $submoduleParent = Split-Path -Parent $submoduleDestination
            New-Item -ItemType Directory -Path $submoduleParent -Force | Out-Null

            & $git.Source clone --quiet --depth 1 --branch $submoduleBranch $submoduleUri $submoduleDestination
            if ($LASTEXITCODE -ne 0) {
                throw "Could not shallow-clone submodule: $relativePath"
            }
            if ((Get-GitValue -WorkingDirectory $submoduleDestination -ArgumentList @("rev-parse", "HEAD")) -ne $submoduleCommit) {
                Invoke-Git -WorkingDirectory $submoduleDestination -ArgumentList @("fetch", "--depth", "1", "origin", $submoduleCommit)
                Invoke-Git -WorkingDirectory $submoduleDestination -ArgumentList @("checkout", "--detach", $submoduleCommit)
            }
            Invoke-Git -WorkingDirectory $submoduleDestination -ArgumentList @("remote", "set-url", "origin", $submoduleOrigin)
            $stagedSubmodules.Add([pscustomobject]@{
                RelativePath = $relativePath
                Source = $submoduleSource
                Destination = $submoduleDestination
                Commit = $submoduleCommit
            })
        }
    }

    Copy-WorkingTreeOverlay -Source $Source -Destination $Destination -Patterns $Patterns

    # Robocopy also overlays tracked files. Restore them first so line-ending or
    # timestamp differences cannot create phantom modifications, then apply only
    # the real tracked changes from each source working tree.
    Invoke-Git -WorkingDirectory $Destination -ArgumentList @("reset", "--hard", "HEAD")
    foreach ($submodule in $stagedSubmodules) {
        Invoke-Git -WorkingDirectory $submodule.Destination -ArgumentList @("reset", "--hard", $submodule.Commit)
    }

    Apply-WorkingTreeDiff `
        -Source $Source `
        -Destination $Destination `
        -ExcludedPaths @($stagedSubmodules | ForEach-Object { $_.RelativePath })
    foreach ($submodule in $stagedSubmodules) {
        Apply-WorkingTreeDiff -Source $submodule.Source -Destination $submodule.Destination
    }

    $stagedCommit = Get-GitValue -WorkingDirectory $Destination -ArgumentList @("rev-parse", "HEAD")
    if ($stagedCommit -ne $commit) {
        throw "Shallow release repository points to an unexpected commit: $stagedCommit"
    }

    Write-Host ("[Git] Branch: {0}" -f $branch) -ForegroundColor Green
    Write-Host ("[Git] Commit: {0}" -f $commit) -ForegroundColor Green
    Write-Host ("[Git] Origin: {0}" -f $origin) -ForegroundColor Green
    Write-Host "[Git] Local working-tree changes and runtime assets were overlaid." -ForegroundColor Green
    Write-Host ""
}

function Get-PackExcludePatterns {
    param([string]$ConfigPath)

    $patterns = New-Object System.Collections.Generic.List[string]
    if (-not (Test-Path -LiteralPath $ConfigPath)) {
        return @()
    }

    $currentSection = ""
    $inExcludeList = $false

    foreach ($rawLine in Get-Content -LiteralPath $ConfigPath -Encoding UTF8) {
        $trimmed = $rawLine.Trim()

        if ($trimmed.StartsWith("[") -and $trimmed.EndsWith("]")) {
            if ($currentSection -eq "pack" -and $inExcludeList) {
                break
            }

            $currentSection = $trimmed.Substring(1, $trimmed.Length - 2).Trim()
            $inExcludeList = $false
            continue
        }

        if ($currentSection -ne "pack") {
            continue
        }

        if (-not $inExcludeList) {
            if ($trimmed.StartsWith("EXCLUDE_PATTERNS=")) {
                $inExcludeList = $true
                $inlineValue = $trimmed.Substring("EXCLUDE_PATTERNS=".Length).Trim()
                if ($inlineValue -and -not $inlineValue.StartsWith("#")) {
                    $patterns.Add($inlineValue.TrimEnd("/"))
                }
            }
            continue
        }

        if ([string]::IsNullOrWhiteSpace($trimmed) -or $trimmed.StartsWith("#")) {
            continue
        }

        if (-not ($rawLine.StartsWith(" ") -or $rawLine.StartsWith([string][char]9))) {
            break
        }

        $patterns.Add($trimmed.TrimEnd("/"))
    }

    return $patterns.ToArray()
}

function Show-Help {
    Write-Host "MonGSV packer for Windows"
    Write-Host ""
    Write-Host "Usage:"
    Write-Host "  .\\pack.ps1 [-OutputFile <file>] [-SourceDir <dir>] [-UseTar] [-SkipFrontendBuild] [-Help]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -OutputFile <file>   Output archive path"
    Write-Host "  -SourceDir <dir>     Git working tree to package, defaults to workspace root"
    Write-Host "  -UseTar              Build tar.gz instead of 7z"
    Write-Host "  -SkipFrontendBuild   Do not run npm build before packing"
    Write-Host "  -Help, -h            Show help"
    Write-Host ""
}

function Invoke-FrontendBuild {
    param([string]$Root)

    $frontendDir = Join-Path $Root "Code\GptSov_Front"
    $packageJson = Join-Path $frontendDir "package.json"
    if (-not (Test-Path -LiteralPath $packageJson -PathType Leaf)) {
        Write-Host "[Build] Frontend package.json not found, skipping." -ForegroundColor Yellow
        return
    }

    $npm = Get-Command "npm.cmd" -ErrorAction SilentlyContinue
    if (-not $npm) {
        $npm = Get-Command "npm" -ErrorAction SilentlyContinue
    }
    if (-not $npm) {
        throw "Could not find npm. Build frontend first or use -SkipFrontendBuild."
    }

    Write-Host "[Build] Building frontend dist..." -ForegroundColor Cyan
    Push-Location $frontendDir
    try {
        if (-not (Test-Path -LiteralPath "node_modules" -PathType Container)) {
            if (Test-Path -LiteralPath "package-lock.json" -PathType Leaf) {
                & $npm.Source ci
            }
            else {
                & $npm.Source install
            }
            if ($LASTEXITCODE -ne 0) {
                throw "Frontend dependency install failed with code $LASTEXITCODE."
            }
        }

        & $npm.Source run build
        if ($LASTEXITCODE -ne 0) {
            throw "Frontend build failed with code $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
    }
    Write-Host "[Build] Frontend dist is ready." -ForegroundColor Green
    Write-Host ""
}

function Show-TopLevelExclusions {
    param(
        [string]$Root,
        [string[]]$Patterns
    )

    if (-not $Patterns -or $Patterns.Count -eq 0) {
        return
    }

    Write-Host "[Exclude] Top-level directory matches:" -ForegroundColor Yellow
    $found = $false

    foreach ($item in Get-ChildItem -LiteralPath $Root -Directory -Force | Sort-Object Name) {
        foreach ($pattern in $Patterns) {
            if ($item.Name -ceq $pattern -or $item.Name -clike $pattern) {
                $bytes = (Get-ChildItem -LiteralPath $item.FullName -Recurse -Force -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
                if ($null -eq $bytes) {
                    $bytes = 0
                }
                $size = [math]::Round(($bytes / 1MB), 1)
                Write-Host ("  - {0} ({1} MB)" -f $item.Name, $size) -ForegroundColor DarkGray
                $found = $true
                break
            }
        }
    }

    if (-not $found) {
        Write-Host "  - (none)" -ForegroundColor DarkGray
    }

    Write-Host ""
}

function Invoke-7Zip {
    param(
        [string]$SevenZipPath,
        [string[]]$ArgumentList
    )

    $stdout = Join-Path $env:TEMP ("mongsv_7z_out_{0}.txt" -f ([guid]::NewGuid().ToString("N")))
    $stderr = Join-Path $env:TEMP ("mongsv_7z_err_{0}.txt" -f ([guid]::NewGuid().ToString("N")))

    try {
        $process = Start-Process -FilePath $SevenZipPath -ArgumentList $ArgumentList -Wait -PassThru -NoNewWindow -RedirectStandardOutput $stdout -RedirectStandardError $stderr
        $output = Get-Content -LiteralPath $stdout -ErrorAction SilentlyContinue
        if ($output) {
            $output | Select-Object -Last 8 | ForEach-Object { Write-Host ("  {0}" -f $_) -ForegroundColor DarkGray }
        }
        if ($process.ExitCode -ne 0) {
            $errorOutput = Get-Content -LiteralPath $stderr -ErrorAction SilentlyContinue
            if ($errorOutput) {
                $errorOutput | ForEach-Object { Write-Host ("  {0}" -f $_) -ForegroundColor Red }
            }
            throw "7-Zip exited with code $($process.ExitCode)."
        }
    }
    finally {
        Remove-Item -LiteralPath $stdout -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $stderr -Force -ErrorAction SilentlyContinue
    }
}

if ($Help) {
    Show-Help
    exit 0
}

$scriptPath = Join-Path $PSScriptRoot "pack.ps1"
$workspaceRoot = Find-WorkspaceRoot -StartPath $scriptPath
if (-not $workspaceRoot) {
    throw "Could not find workspace root via .monconfig."
}

if ([string]::IsNullOrWhiteSpace($SourceDir)) {
    $SourceDir = $workspaceRoot
}
else {
    $SourceDir = (Resolve-Path -LiteralPath $SourceDir).Path
}

if (-not (Test-Path -LiteralPath $SourceDir -PathType Container)) {
    throw "Source directory does not exist: $SourceDir"
}

if (-not $SkipFrontendBuild) {
    Invoke-FrontendBuild -Root $SourceDir
}

$monconfigPath = Join-Path $SourceDir ".monconfig"
$patterns = Get-PackExcludePatterns -ConfigPath $monconfigPath
$sevenZipPath = Find-7Zip
if (-not $sevenZipPath) {
    throw "Could not find 7-Zip. Install it or add 7z.exe to PATH."
}

if ([string]::IsNullOrWhiteSpace($OutputFile)) {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $folderName = Split-Path -Leaf $SourceDir
    $extension = if ($UseTar) { ".tar.gz" } else { ".7z" }
    $defaultOutputDir = Split-Path -Parent $SourceDir
    if ([string]::IsNullOrWhiteSpace($defaultOutputDir)) {
        $defaultOutputDir = $SourceDir
    }
    $OutputFile = Join-Path $defaultOutputDir ("{0}_{1}{2}" -f $folderName, $timestamp, $extension)
}
elseif (-not [System.IO.Path]::IsPathRooted($OutputFile)) {
    $OutputFile = Join-Path (Get-Location).Path $OutputFile
}

$OutputFile = [System.IO.Path]::GetFullPath($OutputFile)
$outputParent = Split-Path -Parent $OutputFile
if ($outputParent) {
    New-Item -ItemType Directory -Force -Path $outputParent | Out-Null
}

$excludeFile = Join-Path $env:TEMP ("mongsv_pack_exclude_{0}.txt" -f ([guid]::NewGuid().ToString("N")))
$patterns | Set-Content -LiteralPath $excludeFile -Encoding UTF8
$stagingParent = Join-Path $env:TEMP ("mongsv_release_{0}" -f ([guid]::NewGuid().ToString("N")))
$packSourceDir = Join-Path $stagingParent (Split-Path -Leaf $SourceDir)

New-Item -ItemType Directory -Path $stagingParent -Force | Out-Null
try {
    New-ShallowReleaseTree -Source $SourceDir -Destination $packSourceDir -Patterns $patterns
}
catch {
    Remove-Item -LiteralPath $stagingParent -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $excludeFile -Force -ErrorAction SilentlyContinue
    throw
}

Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  MonGSV Project Packer (Windows)" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host ("  Source: {0}" -f $SourceDir) -ForegroundColor White
Write-Host ("  Staged: {0}" -f $packSourceDir) -ForegroundColor White
Write-Host ("  Config: {0}" -f $monconfigPath) -ForegroundColor White
Write-Host ("  Output: {0}" -f $OutputFile) -ForegroundColor White
if ($UseTar) {
    Write-Host "  Format: tar.gz" -ForegroundColor White
}
else {
    Write-Host "  Format: 7z" -ForegroundColor White
}
Write-Host ("  Excludes: {0}" -f $patterns.Count) -ForegroundColor White
Write-Host ("  7-Zip: {0}" -f $sevenZipPath) -ForegroundColor White
Write-Host ""

Show-TopLevelExclusions -Root $packSourceDir -Patterns $patterns

$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

try {
    if ($UseTar) {
        $tempDir = Join-Path $env:TEMP ("mongsv_pack_{0}" -f ([guid]::NewGuid().ToString("N")))
        New-Item -ItemType Directory -Force -Path $tempDir | Out-Null

        try {
            $tempTar = Join-Path $tempDir ((Split-Path -Leaf $packSourceDir) + ".tar")

            $tarArgs = @(
                "a",
                "-ttar",
                "-mx=0",
                "-bb0",
                "-scsUTF-8",
                "-xr@$excludeFile",
                $tempTar,
                "$packSourceDir\*"
            )

            Write-Host "Building tar..." -ForegroundColor Yellow
            Invoke-7Zip -SevenZipPath $sevenZipPath -ArgumentList $tarArgs

            $gzipArgs = @(
                "a",
                "-tgzip",
                "-mx=5",
                "-bb0",
                $OutputFile,
                $tempTar
            )

            Write-Host "Compressing to tar.gz..." -ForegroundColor Yellow
            Invoke-7Zip -SevenZipPath $sevenZipPath -ArgumentList $gzipArgs
        }
        finally {
            Remove-Item -LiteralPath $tempDir -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
    else {
        $archiveArgs = @(
            "a",
            "-t7z",
            "-m0=lzma2",
            "-mx=5",
            "-bb0",
            "-scsUTF-8",
            "-xr@$excludeFile",
            $OutputFile,
            "$packSourceDir\*"
        )

        Write-Host "Packing archive..." -ForegroundColor Yellow
        Invoke-7Zip -SevenZipPath $sevenZipPath -ArgumentList $archiveArgs
    }

    $stopwatch.Stop()

    if (-not (Test-Path -LiteralPath $OutputFile)) {
        throw "Archive file was not created."
    }

    $fileSizeMb = [math]::Round((Get-Item -LiteralPath $OutputFile).Length / 1MB, 2)

    Write-Host ""
    Write-Host "==================================================" -ForegroundColor Green
    Write-Host "  Pack complete" -ForegroundColor Green
    Write-Host "==================================================" -ForegroundColor Green
    Write-Host ("  Output: {0}" -f $OutputFile) -ForegroundColor White
    Write-Host ("  Size: {0} MB" -f $fileSizeMb) -ForegroundColor White
    Write-Host ("  Time: {0}" -f $stopwatch.Elapsed.ToString("mm\:ss")) -ForegroundColor White
    Write-Host "==================================================" -ForegroundColor Green
    Write-Host ""
}
finally {
    Remove-Item -LiteralPath $excludeFile -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $stagingParent -Recurse -Force -ErrorAction SilentlyContinue
}

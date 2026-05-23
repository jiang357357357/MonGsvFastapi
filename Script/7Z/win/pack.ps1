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
    Write-Host "  .\\pack.ps1 [-OutputFile <file>] [-SourceDir <dir>] [-UseTar] [-Help]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -OutputFile <file>   Output archive path"
    Write-Host "  -SourceDir <dir>     Source directory, defaults to workspace root"
    Write-Host "  -UseTar              Build tar.gz instead of 7z"
    Write-Host "  -Help, -h            Show help"
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

Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  MonGSV Project Packer (Windows)" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host ("  Source: {0}" -f $SourceDir) -ForegroundColor White
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

Show-TopLevelExclusions -Root $SourceDir -Patterns $patterns

$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

try {
    if ($UseTar) {
        $tempDir = Join-Path $env:TEMP ("mongsv_pack_{0}" -f ([guid]::NewGuid().ToString("N")))
        New-Item -ItemType Directory -Force -Path $tempDir | Out-Null

        try {
            $tempTar = Join-Path $tempDir ((Split-Path -Leaf $SourceDir) + ".tar")

            $tarArgs = @(
                "a",
                "-ttar",
                "-mx=0",
                "-bb0",
                "-scsUTF-8",
                "-xr@$excludeFile",
                $tempTar,
                "$SourceDir\*"
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
            "$SourceDir\*"
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
}

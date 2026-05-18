$uv = Get-Command uv -ErrorAction SilentlyContinue

if (-not $uv) {
    Write-Host "uv not found, installing via official installer..." -ForegroundColor Cyan
    irm https://astral.sh/uv/install.ps1 | iex
} else {
    Write-Host "uv is already installed: $($uv.Source)" -ForegroundColor Green
}

$uv = Get-Command uv -ErrorAction SilentlyContinue

if ($uv) {
    Write-Host "uv version:" -ForegroundColor Green
    uv --version
    exit 0
} else {
    Write-Error "uv installation failed or uv is not in PATH."
    exit 1
}


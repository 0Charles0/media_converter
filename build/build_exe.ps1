# MediaConverter build script (pack exe with PyInstaller)
# Usage: powershell -ExecutionPolicy Bypass -File build\build_exe.ps1
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "Project dir: $root"

# generate icon if missing
py build\make_icon.py
if ($LASTEXITCODE -ne 0) { Write-Host "make_icon failed" -ForegroundColor Red; exit 1 }

# clean previous artifacts
if (Test-Path -LiteralPath "$root\dist\MediaConverter") { Remove-Item -Recurse -Force -LiteralPath "$root\dist\MediaConverter" }
if (Test-Path -LiteralPath "$root\build\MediaConverter") { Remove-Item -Recurse -Force -LiteralPath "$root\build\MediaConverter" }

py -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name MediaConverter `
    --icon assets\app.ico `
    --add-data "assets;assets" `
    --collect-all imageio_ffmpeg `
    --collect-all tkinterdnd2 `
    app.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller failed" -ForegroundColor Red
    exit 1
}

# trim non-Windows tkdnd platform dirs to reduce size
$tkdndRoot = Join-Path $root "dist\MediaConverter\_internal\tkinterdnd2\tkdnd"
if ([string]::IsNullOrWhiteSpace($tkdndRoot) -eq $false -and (Test-Path -LiteralPath $tkdndRoot)) {
    Get-ChildItem -LiteralPath $tkdndRoot -Directory |
        Where-Object { $_.Name -notlike "win-*" } |
        ForEach-Object { Remove-Item -Recurse -Force -LiteralPath $_.FullName }
}

Write-Host "DONE: $root\dist\MediaConverter\MediaConverter.exe" -ForegroundColor Green
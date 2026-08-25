$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot
$pyInstallerConfig = Join-Path $repoRoot "build\pyinstaller-cache"
New-Item -ItemType Directory -Force -Path $pyInstallerConfig | Out-Null
$env:PYINSTALLER_CONFIG_DIR = $pyInstallerConfig

python -m pip install -e ".[build]"
python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --onefile `
    --name Jnotes2Hinote `
    --paths src `
    --distpath dist `
    --workpath build\pyinstaller `
    --specpath build\pyinstaller `
    scripts\gui_entry.py

Write-Output "Built dist\Jnotes2Hinote.exe"

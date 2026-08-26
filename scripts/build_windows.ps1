$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot
$pyInstallerConfig = Join-Path $repoRoot "build\pyinstaller-cache"
New-Item -ItemType Directory -Force -Path $pyInstallerConfig | Out-Null
$env:PYINSTALLER_CONFIG_DIR = $pyInstallerConfig

python -m pip install -e ".[build]"
$excludeModules = @(
    "numpy",
    "scipy",
    "pandas",
    "matplotlib",
    "sklearn",
    "IPython",
    "jupyter",
    "pytest",
    "ruff",
    "setuptools",
    "pkg_resources",
    "cffi",
    "pywin32_system32",
    "win32api",
    "win32com",
    "pythoncom",
    "pywintypes"
)
$pyInstallerArgs = @(
    "--noconfirm",
    "--clean",
    "--windowed",
    "--onedir",
    "--name", "Jnotes2Hinote",
    "--paths", "src",
    "--distpath", "dist",
    "--workpath", "build\pyinstaller",
    "--specpath", "build\pyinstaller"
)
foreach ($module in $excludeModules) {
    $pyInstallerArgs += @("--exclude-module", $module)
}
$staleSingleFile = Join-Path $repoRoot "dist\Jnotes2Hinote.exe"
if (Test-Path -LiteralPath $staleSingleFile -PathType Leaf) {
    Remove-Item -LiteralPath $staleSingleFile -Force
}
$pythonPrefix = (& python -c "import sys; print(sys.prefix)").Trim()
$tkBinaryDir = Join-Path $pythonPrefix "Library\bin"
foreach ($tkBinary in @("tcl86t.dll", "tk86t.dll")) {
    $tkBinaryPath = Join-Path $tkBinaryDir $tkBinary
    if (Test-Path $tkBinaryPath) {
        # Conda stores Tcl/Tk in Library\bin rather than the usual DLLs folder.
        # PyInstaller's Tk hook does not discover these DLLs in older releases.
        $pyInstallerArgs += @("--add-binary", "$tkBinaryPath;.")
    }
}
$pyInstallerArgs += "scripts\gui_entry.py"
python -m PyInstaller @pyInstallerArgs

Write-Output "Built dist\Jnotes2Hinote\Jnotes2Hinote.exe"

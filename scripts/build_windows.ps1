$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot
$buildPython = if ($env:JNOTES2HINOTE_PYTHON) {
    $env:JNOTES2HINOTE_PYTHON
} else {
    (Get-Command python).Source
}
if (-not (Test-Path -LiteralPath $buildPython -PathType Leaf)) {
    throw "Build Python not found: $buildPython"
}
$pyInstallerConfig = Join-Path $repoRoot "build\pyinstaller-cache"
New-Item -ItemType Directory -Force -Path $pyInstallerConfig | Out-Null
$env:PYINSTALLER_CONFIG_DIR = $pyInstallerConfig

$runtimeReady = $true
& $buildPython -c "import PyInstaller, PyPDF2" 2>$null
if ($LASTEXITCODE -ne 0) {
    $runtimeReady = $false
}
if (-not $runtimeReady) {
    & $buildPython -m pip install --no-build-isolation -e ".[build]"
}
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
    "--specpath", "build\pyinstaller",
    "--additional-hooks-dir", "scripts\pyinstaller-hooks",
    "--hidden-import", "PyPDF2"
)
foreach ($module in $excludeModules) {
    $pyInstallerArgs += @("--exclude-module", $module)
}
$staleSingleFile = Join-Path $repoRoot "dist\Jnotes2Hinote.exe"
if (Test-Path -LiteralPath $staleSingleFile -PathType Leaf) {
    Remove-Item -LiteralPath $staleSingleFile -Force
}
$pythonPrefix = (& $buildPython -c "import sys; print(sys.prefix)").Trim()
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
& $buildPython -m PyInstaller @pyInstallerArgs

Write-Output "Built dist\Jnotes2Hinote\Jnotes2Hinote.exe"

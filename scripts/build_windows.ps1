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

$dependencyCheck = @"
import PIL
import PyInstaller
import pypdf
import pypdfium2
import pypdfium2_raw
import tkinterdnd2

version = tuple(int(part) for part in PyInstaller.__version__.split('.')[:2])
if version < (5, 13):
    raise RuntimeError(f'PyInstaller 5.13 or newer is required, found {PyInstaller.__version__}')
"@
$previousErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $buildPython -c $dependencyCheck 2>$null
$dependencyCheckExitCode = $LASTEXITCODE
$ErrorActionPreference = $previousErrorActionPreference
if ($dependencyCheckExitCode -ne 0) {
    & $buildPython -m pip install --no-build-isolation -e ".[build]"
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install build dependencies (exit code $LASTEXITCODE)"
    }
    & $buildPython -c $dependencyCheck
    if ($LASTEXITCODE -ne 0) {
        throw "Build dependencies do not satisfy the supported versions"
    }
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
    "--hidden-import", "pypdf",
    "--hidden-import", "pypdfium2",
    "--hidden-import", "pypdfium2_raw"
)
foreach ($module in $excludeModules) {
    $pyInstallerArgs += @("--exclude-module", $module)
}
$staleSingleFile = Join-Path $repoRoot "dist\Jnotes2Hinote.exe"
if (Test-Path -LiteralPath $staleSingleFile -PathType Leaf) {
    Remove-Item -LiteralPath $staleSingleFile -Force
}
$pythonPrefix = (& $buildPython -c "import sys; print(sys.prefix)").Trim()
$pdfiumPythonPackageDir = (& $buildPython -c "from pathlib import Path; import pypdfium2; print(Path(pypdfium2.__file__).parent)").Trim()
$pdfiumPackageDir = (& $buildPython -c "from pathlib import Path; import pypdfium2_raw; print(Path(pypdfium2_raw.__file__).parent)").Trim()
$pdfiumBinary = Join-Path $pdfiumPackageDir "pdfium.dll"
$pdfiumPythonVersionMetadata = Join-Path $pdfiumPythonPackageDir "version.json"
$pdfiumVersionMetadata = Join-Path $pdfiumPackageDir "version.json"
if (-not (Test-Path -LiteralPath $pdfiumBinary -PathType Leaf)) {
    throw "pypdfium2 runtime binary not found: $pdfiumBinary"
}
if (-not (Test-Path -LiteralPath $pdfiumVersionMetadata -PathType Leaf)) {
    throw "pypdfium2 version metadata not found: $pdfiumVersionMetadata"
}
if (-not (Test-Path -LiteralPath $pdfiumPythonVersionMetadata -PathType Leaf)) {
    throw "pypdfium2 Python version metadata not found: $pdfiumPythonVersionMetadata"
}
$pyInstallerArgs += @("--add-binary", "$pdfiumBinary;pypdfium2_raw")
$pyInstallerArgs += @("--add-data", "$pdfiumPythonVersionMetadata;pypdfium2")
$pyInstallerArgs += @("--add-data", "$pdfiumVersionMetadata;pypdfium2_raw")
$tkBinaryDir = Join-Path $pythonPrefix "Library\bin"
foreach ($tkBinary in @("tcl86t.dll", "tk86t.dll")) {
    $tkBinaryPath = Join-Path $tkBinaryDir $tkBinary
    if (Test-Path $tkBinaryPath) {
        # Conda stores Tcl/Tk in Library\bin rather than the usual DLLs folder.
        # PyInstaller's Tk hook does not discover these DLLs in older releases.
        $pyInstallerArgs += @("--add-binary", "$tkBinaryPath;.")
    }
}
foreach ($condaRuntimeBinary in @(
    "ffi.dll",
    "libbz2.dll",
    "libcrypto-1_1-x64.dll",
    "liblzma.dll",
    "libssl-1_1-x64.dll"
)) {
    $condaRuntimePath = Join-Path $tkBinaryDir $condaRuntimeBinary
    if (Test-Path -LiteralPath $condaRuntimePath -PathType Leaf) {
        # Older PyInstaller releases do not reliably follow dependencies from
        # conda's DLLs directory back into Library\bin.
        $pyInstallerArgs += @("--add-binary", "$condaRuntimePath;.")
    }
}
$pyInstallerArgs += "scripts\gui_entry.py"
& $buildPython -m PyInstaller @pyInstallerArgs
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE"
}

$builtExe = Join-Path $repoRoot "dist\Jnotes2Hinote\Jnotes2Hinote.exe"
$selfTestLog = Join-Path $repoRoot "build\pypdfium2-self-test.log"
Remove-Item -LiteralPath $selfTestLog -Force -ErrorAction SilentlyContinue
$env:JNOTES2HINOTE_SELF_TEST_LOG = $selfTestLog
$pdfiumSelfTest = Start-Process -FilePath $builtExe -ArgumentList "--self-test-pdfium" -WindowStyle Hidden -Wait -PassThru
Remove-Item Env:JNOTES2HINOTE_SELF_TEST_LOG -ErrorAction SilentlyContinue
if ($pdfiumSelfTest.ExitCode -ne 0) {
    $selfTestDetail = if (Test-Path -LiteralPath $selfTestLog) {
        Get-Content -LiteralPath $selfTestLog -Raw
    } else {
        "No diagnostic log was generated."
    }
    throw "Packaged pypdfium2 self-test failed with exit code $($pdfiumSelfTest.ExitCode):`n$selfTestDetail"
}

Write-Output "Built and verified dist\Jnotes2Hinote\Jnotes2Hinote.exe"

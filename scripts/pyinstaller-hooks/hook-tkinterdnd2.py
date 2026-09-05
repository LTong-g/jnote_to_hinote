"""Collect only the Windows x64 Tcl 8 TkDND runtime used by this build."""

from pathlib import Path

from PyInstaller.utils.hooks import get_package_paths

_, package_dir = get_package_paths("tkinterdnd2")
runtime_dir = Path(package_dir) / "tkdnd" / "win-x64"
datas = [
    (str(path), "tkinterdnd2/tkdnd/win-x64")
    for path in runtime_dir.iterdir()
    if path.is_file() and path.suffix.casefold() != ".lib"
]

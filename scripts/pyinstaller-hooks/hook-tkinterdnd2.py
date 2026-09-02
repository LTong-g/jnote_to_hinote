"""Collect the native TkDND binaries used by the desktop GUI."""

from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files("tkinterdnd2")

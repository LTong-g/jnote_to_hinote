"""Jnotes2Hinote v1.6.0 conversion entry point.

This version preserves the v1.5.3 Hinote format and rendering behavior while
making file-output paths safe and predictable.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from . import converter_v1_5_3 as _base

JNote = _base.JNote
JnotesContainerInfo = _base.JnotesContainerInfo
PdfAsset = _base.PdfAsset
PdfPageBinding = _base.PdfPageBinding
TESTED_HUAWEI_NOTES_VERSION = _base.TESTED_HUAWEI_NOTES_VERSION
TESTED_JNOTES_VERSION = _base.TESTED_JNOTES_VERSION
parse_jnotes = _base.parse_jnotes
parse_jnotes_with_info = _base.parse_jnotes_with_info
__version__ = "1.6.0"


def __getattr__(name: str) -> Any:
    return getattr(_base, name)


def ensure_hinote_suffix(path: Path) -> Path:
    """Append ``.hinote`` unless the path already has that final suffix."""
    path = Path(path)
    if path.suffix.casefold() == ".hinote":
        return path
    return path.with_name(path.name + ".hinote")


def _same_file(source: Path, destination: Path) -> bool:
    if source.resolve(strict=False) == destination.resolve(strict=False):
        return True
    try:
        return source.exists() and destination.exists() and os.path.samefile(source, destination)
    except OSError:
        return False


def convert(jnotes_path: Path, output: Path, page_limit: int | None = None) -> dict[str, Any]:
    """Convert through v1.5.3 after normalizing and validating the output path."""
    jnotes_path = Path(jnotes_path)
    output = ensure_hinote_suffix(Path(output))
    if _same_file(jnotes_path, output):
        raise ValueError("输出文件不能与源 Jnotes 文件相同")
    result = _base.convert(jnotes_path, output, page_limit=page_limit)
    result["converterVersion"] = __version__
    result["output"] = str(output)
    result["outputBytes"] = output.stat().st_size
    return result


__all__ = [
    "TESTED_HUAWEI_NOTES_VERSION",
    "TESTED_JNOTES_VERSION",
    "JNote",
    "JnotesContainerInfo",
    "PdfAsset",
    "PdfPageBinding",
    "__version__",
    "convert",
    "ensure_hinote_suffix",
    "parse_jnotes",
    "parse_jnotes_with_info",
]

"""Single runtime entry point for the current versioned conversion core."""
from __future__ import annotations

from .converter_v1_5_1 import (
    TESTED_HUAWEI_NOTES_VERSION,
    TESTED_JNOTES_VERSION,
    convert,
    parse_jnotes,
    parse_jnotes_with_info,
)
from .converter_v1_5_1 import __version__ as CONVERTER_CORE_VERSION

__all__ = [
    "CONVERTER_CORE_VERSION",
    "TESTED_HUAWEI_NOTES_VERSION",
    "TESTED_JNOTES_VERSION",
    "convert",
    "parse_jnotes",
    "parse_jnotes_with_info",
]

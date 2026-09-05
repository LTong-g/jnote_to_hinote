"""Conversion-report helpers shared by command-line and GUI front ends."""
from __future__ import annotations

from pathlib import PurePosixPath, PureWindowsPath
from typing import Any

PATH_KEYS = {"source", "output", "outputDirectory", "path"}


def _basename(value: str) -> str:
    windows_name = PureWindowsPath(value).name
    posix_name = PurePosixPath(value).name
    if "\\" in value:
        return windows_name
    return posix_name


def _path_replacements(payload: Any) -> dict[str, str]:
    replacements: dict[str, str] = {}
    if isinstance(payload, list):
        for item in payload:
            replacements.update(_path_replacements(item))
    elif isinstance(payload, dict):
        for key, value in payload.items():
            if key in PATH_KEYS and isinstance(value, str):
                replacements[value] = _basename(value)
            else:
                replacements.update(_path_replacements(value))
    return replacements


def _redact_error_tail(value: str) -> str:
    """Shorten an absolute path appearing after a common error separator."""
    for separator in ("：", ": "):
        if separator not in value:
            continue
        prefix, detail = value.rsplit(separator, 1)
        leading = detail[: len(detail) - len(detail.lstrip())]
        stripped = detail.strip()
        quote = stripped[:1] if stripped[:1] in {"'", '"'} else ""
        candidate = stripped.strip("'\"")
        if PureWindowsPath(candidate).is_absolute() or PurePosixPath(candidate).is_absolute():
            return f"{prefix}{separator}{leading}{quote}{_basename(candidate)}{quote}"
    return value


def _redact_value(payload: Any, replacements: dict[str, str]) -> Any:
    if isinstance(payload, list):
        return [_redact_value(item, replacements) for item in payload]
    if not isinstance(payload, dict):
        return payload

    redacted: dict[str, Any] = {}
    for key, value in payload.items():
        if key in {"title", "noteTitle"} and isinstance(value, str):
            redacted[key] = "[redacted]"
        elif key in PATH_KEYS and isinstance(value, str):
            redacted[key] = _basename(value)
        elif key == "error" and isinstance(value, str):
            error = value
            for original in sorted(replacements, key=len, reverse=True):
                error = error.replace(original, replacements[original])
            redacted[key] = _redact_error_tail(error)
        else:
            redacted[key] = _redact_value(value, replacements)
    return redacted


def redact_report(payload: Any) -> Any:
    """Return a copy of a report without note titles or absolute paths."""
    return _redact_value(payload, _path_replacements(payload))


__all__ = ["redact_report"]

"""Read the observed Huawei Notes ZIP and PENCILENGINE structures."""

from __future__ import annotations

import gzip
import json
import math
import struct
import zipfile
from collections import Counter, defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any
from zlib import error as ZlibError


def objects(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, list):
        yield from (item for item in value if isinstance(item, dict))


def number(value: Any, default: float = 0) -> float:
    try:
        parsed = float(value)
    except (OverflowError, TypeError, ValueError):
        return default
    return parsed if math.isfinite(parsed) else default


def code(value: Any, default: int = -1) -> int:
    parsed = number(value, default)
    result = int(parsed)
    return result if result == parsed else default


class HinoteReader:
    """Resolve referenced members inside the archive without extracting files."""

    def __init__(self, archive: zipfile.ZipFile, ignored: Counter[str]) -> None:
        self.archive = archive
        self.ignored = ignored
        self.paths: dict[str, list[zipfile.ZipInfo]] = defaultdict(list)
        self.assets: dict[str, list[zipfile.ZipInfo]] = defaultdict(list)
        for info in archive.infolist():
            if info.is_dir():
                continue
            path = info.filename.replace("\\", "/")
            self.paths[path.casefold()].append(info)
            if path.casefold().startswith("files/"):
                self.assets[PurePosixPath(path).name.casefold()].append(info)

    def read_asset(self, reference: Any) -> bytes | None:
        if not isinstance(reference, str) or not reference:
            return None
        path = reference.replace("\\", "/")
        matches = self.paths.get(path.casefold()) if path.casefold().startswith("files/") else None
        if not matches:
            matches = self.assets.get(PurePosixPath(path).name.casefold())
        if not matches or len(matches) != 1:
            return None
        return self.archive.read(matches[0])

    def _metadata(self, path: str, key: str) -> dict[str, Any] | None:
        matches = self.paths[path]
        if len(matches) != 1:
            raise ValueError("压缩包包含重复的华为笔记元数据")
        raw = self.archive.read(matches[0])
        if raw.startswith(b"\x1f\x8b"):
            raw = gzip.decompress(raw)
        wrapper = json.loads(raw)
        value = wrapper.get(key) if isinstance(wrapper, dict) else None
        return value if isinstance(value, dict) else None

    def read_note(self) -> dict[str, Any]:
        notes = []
        for path in self.paths:
            if "/" not in path and path.endswith(".jhinote") and path != "custom_md.jhinote":
                note = self._metadata(path, "customNoteContent")
                if note is not None:
                    notes.append(note)
        if len(notes) != 1:
            raise ValueError("无法识别唯一的华为笔记正文元数据")
        return notes[0]

    def read_pages(self, note: dict[str, Any]) -> list[dict[str, Any]]:
        pages = []
        for path in self.paths:
            if not (path.startswith("pages/") and path.endswith(".jhinote")):
                continue
            try:
                page = self._metadata(path, "customNotePageContent")
            except (ValueError, OSError, EOFError, ZlibError, zipfile.BadZipFile, RuntimeError):
                page = None
            if page is None:
                self.ignored["pageMetadata"] += 1
            elif not code(page.get("isDelete"), 0) and (
                not note.get("id") or not page.get("notesId") or page["notesId"] == note["id"]
            ):
                pages.append(page)
            elif not code(page.get("isDelete"), 0):
                self.ignored["pageMetadata"] += 1
        if not pages:
            raise ValueError("华为笔记中没有可读取的页面")
        return sorted(pages, key=lambda page: code(page.get("pageNumber"), 2**31))


@dataclass(frozen=True)
class InkStroke:
    pen: int
    shape: int
    bgr: tuple[float, float, float]
    opacity: float
    width: float
    points: tuple[tuple[float, float, float], ...]


NO_SHAPE = 0xFFFFFFFF
INK_HEADER_SIZE = 196
INK_STYLE_SIZE = 108
POINT_HEADER_SIZE = 16
POINT_SIZE = 36
INK_TAIL_SIZE = 64


def read_ink(data: bytes) -> Iterator[InkStroke]:
    """Decode the known record layout, allowing a native index after the final record."""
    if not data.startswith(b"PENCILENGINE") or len(data) < INK_HEADER_SIZE:
        raise ValueError("不支持的 PENCILENGINE 文件头")
    declared_count = struct.unpack_from(">I", data, 112)[0]
    if not declared_count and len(data) > INK_HEADER_SIZE + 12:
        raise ValueError("无法识别 PENCILENGINE 笔迹数量")
    pos = INK_HEADER_SIZE
    for _ in range(declared_count):
        header = pos + INK_STYLE_SIZE
        start = header + POINT_HEADER_SIZE
        if start > len(data):
            raise ValueError("PENCILENGINE 笔迹数据已截断")
        prefix, count, stride, reserved = struct.unpack_from(">4I", data, header)
        end = start + count * POINT_SIZE
        next_pos = end + INK_TAIL_SIZE
        if prefix not in (0, 2) or stride != POINT_SIZE or reserved != 0 or not count or next_pos > len(data):
            raise ValueError("不支持的 PENCILENGINE 点表布局")
        shape = struct.unpack_from(">I", data, pos + 8)[0]
        pen = struct.unpack_from(">I", data, pos + 56)[0]
        blue, green, red, opacity, _, width = struct.unpack_from(">6f", data, pos + 64)
        points = []
        for offset in range(start, end, POINT_SIZE):
            x, y, _, pressure = struct.unpack_from(">4f", data, offset + 4)
            points.append((x, y, pressure))
        yield InkStroke(pen, shape, (blue, green, red), opacity, width, tuple(points))
        pos = next_pos

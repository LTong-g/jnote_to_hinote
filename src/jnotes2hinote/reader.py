#!/usr/bin/env python3
"""Read supported Jnotes containers into the converter's in-memory model."""
from __future__ import annotations

import json
import struct
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class JRecord:
    typ: str
    source: str
    object_id: str
    parent_id: str
    aux_path: str
    aux_size: str
    payload: bytes
    binary: bytes = b""


@dataclass
class JNote:
    note_uuid: str
    title: str
    width: float
    height: float
    note_meta: dict[str, Any]
    pages: list[dict[str, Any]]
    records: list[JRecord]
    strokes: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: defaultdict(list))
    images: dict[str, list[tuple[dict[str, Any], bytes]]] = field(default_factory=lambda: defaultdict(list))
    texts: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: defaultdict(list))
    covers: dict[str, bytes] = field(default_factory=dict)
    audio_records: list[JRecord] = field(default_factory=list)



SUPPORTED_ENTRY_NAMES = ("zip.Jzip", "zip.Jnotes")
SUPPORTED_STREAM_VERSION = 2


@dataclass(frozen=True)
class JnotesContainerInfo:
    """Facts about the outer container and inner stream selected for parsing."""

    entry_name: str
    stream_version: int
    stream_size: int
    outer_entry_count: int
    footer_recognized: bool


def _read_utf(data: bytes, pos: int) -> tuple[str, int]:
    if pos + 2 > len(data):
        raise ValueError("Jnotes 内层流缺少 UTF 字符串长度")
    length = struct.unpack_from(">H", data, pos)[0]
    pos += 2
    end = pos + length
    if end > len(data):
        raise ValueError("Jnotes 内层流的 UTF 字符串已截断")
    try:
        value = data[pos:end].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Jnotes 内层流包含无效 UTF-8 字符串") from exc
    return value, end


def _read_footer(data: bytes, pos: int) -> bool:
    """Recognize observed footers while accepting harmless exporter variants."""
    tail = data[pos:]
    # Current samples: int64(2), UTF("Lucky"), int64(19).
    if len(tail) == 23:
        try:
            first = struct.unpack_from(">q", tail, 0)[0]
            label, label_end = _read_utf(tail, 8)
            last = struct.unpack_from(">q", tail, label_end)[0]
        except (ValueError, struct.error):
            pass
        else:
            if first == 2 and label == "Lucky" and last == 19 and label_end + 8 == len(tail):
                return True

    # Older fixtures/exporters observed in this project ended with int32(0)
    # followed by the same marker text.  It is retained for compatibility.
    return tail == struct.pack(">i", 0) + b"Lucky"


def _select_entry(path: Path) -> tuple[bytes, JnotesContainerInfo]:
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            counts = {name: sum(info.filename == name for info in infos) for name in SUPPORTED_ENTRY_NAMES}
            present = [name for name in SUPPORTED_ENTRY_NAMES if counts[name]]
            if not present:
                raise ValueError(
                    "不是受支持的 .Jnotes 压缩包：缺少 zip.Jzip 或 zip.Jnotes"
                )
            if len(present) > 1:
                raise ValueError("Jnotes 压缩包同时包含 zip.Jzip 和 zip.Jnotes，无法确定唯一数据入口")
            entry_name = present[0]
            if counts[entry_name] != 1:
                raise ValueError(f"Jnotes 压缩包包含重复的 {entry_name} 数据入口")
            # read(info) performs the ZIP CRC check, so corrupted compressed
            # members fail before the inner protocol is interpreted.
            data = archive.read(next(info for info in infos if info.filename == entry_name))
            return data, JnotesContainerInfo(
                entry_name=entry_name,
                stream_version=-1,
                stream_size=len(data),
                outer_entry_count=len(infos),
                footer_recognized=False,
            )
    except zipfile.BadZipFile as exc:
        raise ValueError(f"不是有效的 Jnotes ZIP 文件：{exc}") from exc


def parse_jnotes_with_info(path: Path) -> tuple[JNote, JnotesContainerInfo]:
    """Parse a Jnotes file and return both its normal model and container facts."""
    data, container = _select_entry(path)
    pos = 0
    magic, pos = _read_utf(data, pos)
    if magic != "TRY":
        raise ValueError(f"Jnotes 内层流魔数异常：{magic!r}")
    if pos + 4 > len(data):
        raise ValueError("Jnotes 内层流缺少版本号")
    stream_version = struct.unpack_from(">i", data, pos)[0]
    pos += 4
    if stream_version != SUPPORTED_STREAM_VERSION:
        raise ValueError(
            f"不支持的 Jnotes 内层流版本：{stream_version}（当前支持 {SUPPORTED_STREAM_VERSION}）"
        )
    note_uuid, pos = _read_utf(data, pos)

    records: list[JRecord] = []
    footer_start = len(data)
    while pos + 4 <= len(data):
        record_start = pos
        marker = struct.unpack_from(">i", data, pos)[0]
        pos += 4
        if marker != 1:
            footer_start = record_start
            break
        try:
            typ, pos = _read_utf(data, pos)
            source, pos = _read_utf(data, pos)
            object_id, pos = _read_utf(data, pos)
            if pos + 8 > len(data):
                raise ValueError("Jnotes 记录缺少负载长度")
            payload_len = struct.unpack_from(">q", data, pos)[0]
            pos += 8
            parent_id, pos = _read_utf(data, pos)
            aux_path, pos = _read_utf(data, pos)
            aux_size, pos = _read_utf(data, pos)
            if payload_len < 0 or pos + payload_len > len(data):
                raise ValueError(f"Jnotes {typ} 记录负载长度无效")
            payload = data[pos:pos + payload_len]
            pos += payload_len
            binary = b""
            if aux_size.isdigit():
                binary_len = int(aux_size)
                if pos + binary_len > len(data):
                    raise ValueError(f"Jnotes {typ} 记录嵌入二进制长度无效")
                binary = data[pos:pos + binary_len]
                pos += binary_len
            records.append(JRecord(typ, source, object_id, parent_id, aux_path, aux_size, payload, binary))
        except (struct.error, ValueError) as exc:
            raise ValueError(f"Jnotes 记录在偏移 {record_start} 处损坏：{exc}") from exc

    if footer_start == len(data) and pos < len(data):
        footer_start = pos
    footer_recognized = _read_footer(data, footer_start)

    note_meta: dict[str, Any] | None = None
    pages: list[dict[str, Any]] = []
    strokes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    images: dict[str, list[tuple[dict[str, Any], bytes]]] = defaultdict(list)
    texts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    covers: dict[str, bytes] = {}
    audio_records: list[JRecord] = []

    for record in records:
        try:
            if record.typ == "NOTE":
                note_meta = json.loads(record.payload.decode("utf-8"))
            elif record.typ == "PAGE":
                pages.append(json.loads(record.payload.decode("utf-8")))
            elif record.typ == "STROKE":
                strokes[record.parent_id].extend(json.loads(record.payload.decode("utf-8")))
            elif record.typ == "IMAGE":
                images[record.parent_id].append((json.loads(record.payload.decode("utf-8")), record.binary))
            elif record.typ == "TEXT":
                texts[record.parent_id].extend(json.loads(record.payload.decode("utf-8")))
            elif record.typ == "COVER":
                covers[record.object_id] = record.payload
            elif record.typ == "AUDIO_EX":
                audio_records.append(record)
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise ValueError(f"Jnotes {record.typ} 记录内容无效：{exc}") from exc

    if not note_meta:
        raise ValueError("缺少 Jnotes NOTE 记录")
    try:
        title = str(note_meta.get("b") or path.stem)
        width = float(note_meta.get("j", 1240.0))
        height = float(note_meta.get("l", 1754.0))
    except (TypeError, ValueError) as exc:
        raise ValueError("Jnotes NOTE 记录的页面尺寸无效") from exc
    if width <= 0 or height <= 0:
        raise ValueError("Jnotes NOTE 记录的页面尺寸必须为正数")

    note = JNote(note_uuid, title, width, height, note_meta, pages, records)
    note.strokes = strokes
    note.images = images
    note.texts = texts
    note.covers = covers
    note.audio_records = audio_records
    return note, JnotesContainerInfo(
        entry_name=container.entry_name,
        stream_version=stream_version,
        stream_size=container.stream_size,
        outer_entry_count=container.outer_entry_count,
        footer_recognized=footer_recognized,
    )


def parse_jnotes(path: Path) -> JNote:
    """Parse a supported Jnotes file without exposing container metadata."""
    note, _ = parse_jnotes_with_info(path)
    return note


__all__ = [
    "SUPPORTED_ENTRY_NAMES",
    "SUPPORTED_STREAM_VERSION",
    "JNote",
    "JRecord",
    "JnotesContainerInfo",
    "parse_jnotes",
    "parse_jnotes_with_info",
]


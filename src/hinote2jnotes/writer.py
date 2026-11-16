"""Write the observed Jnotes TRY v2 sequential record stream."""

from __future__ import annotations

import json
import struct
import zipfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from jnotes2hinote.reader import SUPPORTED_STREAM_VERSION, JRecord

OUTPUT_SUFFIX = ".Jnotes"
OUTPUT_SUFFIXES = {".jnotes", ".jnote"}
ENTRY_NAME = "zip.Jnotes"


def json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _utf(value: str) -> bytes:
    data = value.encode("utf-8")
    if len(data) > 65535:
        raise ValueError("Jnotes 记录字段超过 UTF 长度限制")
    return struct.pack(">H", len(data)) + data


def write_jnotes(path: Path, note_id: str, records: Iterable[JRecord]) -> None:
    """Stream one ZIP member, including inline image binaries and the observed footer."""
    with (
        zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive,
        archive.open(ENTRY_NAME, "w") as stream,
    ):
        stream.write(_utf("TRY") + struct.pack(">i", SUPPORTED_STREAM_VERSION) + _utf(note_id))
        for record in records:
            stream.write(b"".join((
                struct.pack(">i", 1),
                _utf(record.typ),
                _utf(record.source),
                _utf(record.object_id),
                struct.pack(">q", len(record.payload)),
                _utf(record.parent_id),
                _utf(record.aux_path),
                _utf(str(len(record.binary)) if record.binary else ""),
            )))
            stream.write(record.payload)
            if record.binary:
                stream.write(record.binary)
        stream.write(struct.pack(">q", 2) + _utf("Lucky") + struct.pack(">q", 19))

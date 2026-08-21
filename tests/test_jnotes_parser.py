import json
import struct
import zipfile
from pathlib import Path

from jnotes2hinote.converter_v1_1_0 import parse_jnotes


def java_utf(s: str) -> bytes:
    b = s.encode("utf-8")
    return struct.pack(">H", len(b)) + b


def record(typ: str, oid: str, parent: str, payload: bytes, binary: bytes = b"") -> bytes:
    return b"".join(
        [
            struct.pack(">i", 1),
            java_utf(typ),
            java_utf("test"),
            java_utf(oid),
            struct.pack(">q", len(payload)),
            java_utf(parent),
            java_utf(""),
            java_utf(str(len(binary)) if binary else ""),
            payload,
            binary,
        ]
    )


def test_parse_minimal_jnotes(tmp_path: Path):
    note_id = "note-id"
    page_id = "page-id"
    note = json.dumps({"b": "Fixture", "j": 1240.0, "l": 1754.0}).encode()
    page = json.dumps({"a": page_id, "d": "PageBg/White_Blank_Paper"}).encode()
    stroke = json.dumps([{"b": 1, "e": 1, "c": {"a": 2, "c": -1, "d": 3, "k": [{"x": 1, "y": 2, "p": 0.2}, {"x": 3, "y": 4, "p": 0.3}]}}]).encode()

    jzip = b"".join(
        [
            java_utf("TRY"),
            struct.pack(">i", 2),
            java_utf(note_id),
            record("NOTE", note_id, "", note),
            record("PAGE", page_id, note_id, page),
            record("STROKE", "stroke-record", page_id, stroke),
            struct.pack(">i", 0),
            b"Lucky",
        ]
    )
    path = tmp_path / "fixture.Jnotes"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("zip.Jzip", jzip)

    parsed = parse_jnotes(path)
    assert parsed.title == "Fixture"
    assert len(parsed.pages) == 1
    assert len(parsed.strokes[page_id]) == 1

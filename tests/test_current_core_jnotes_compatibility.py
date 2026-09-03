import json
import struct
import warnings
import zipfile
from pathlib import Path

import pytest

from jnotes2hinote.converter_v1_5_1 import convert, parse_jnotes_with_info


def java_utf(value: str) -> bytes:
    data = value.encode("utf-8")
    return struct.pack(">H", len(data)) + data


def record(typ: str, object_id: str, parent: str, payload: bytes) -> bytes:
    return b"".join([
        struct.pack(">i", 1),
        java_utf(typ),
        java_utf("test"),
        java_utf(object_id),
        struct.pack(">q", len(payload)),
        java_utf(parent),
        java_utf(""),
        java_utf(""),
        payload,
    ])


def make_stream() -> bytes:
    note_id = "note-id"
    page_id = "page-id"
    note = json.dumps({"b": "兼容测试", "j": 1240.0, "l": 1754.0}).encode()
    page = json.dumps({"a": page_id, "d": "PageBg/White_Blank_Paper"}).encode()
    return b"".join([
        java_utf("TRY"),
        struct.pack(">i", 2),
        java_utf(note_id),
        record("NOTE", note_id, "", note),
        record("PAGE", page_id, note_id, page),
        struct.pack(">q", 2),
        java_utf("Lucky"),
        struct.pack(">q", 19),
    ])


def write_container(path: Path, entry_names: list[str], data: bytes | None = None) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for name in entry_names:
            archive.writestr(name, make_stream() if data is None else data)


@pytest.mark.parametrize("entry_name", ["zip.Jzip", "zip.Jnotes"])
def test_reader_supports_both_known_container_names(tmp_path: Path, entry_name: str):
    source = tmp_path / f"source-{entry_name}.Jnotes"
    write_container(source, [entry_name])

    note, info = parse_jnotes_with_info(source)

    assert note.title == "兼容测试"
    assert len(note.pages) == 1
    assert info.entry_name == entry_name
    assert info.stream_version == 2
    assert info.footer_recognized is True


@pytest.mark.parametrize("entry_name", ["zip.Jzip", "zip.Jnotes"])
def test_current_core_converts_both_container_names(tmp_path: Path, entry_name: str):
    source = tmp_path / f"source-{entry_name}.Jnotes"
    output = tmp_path / f"output-{entry_name}.hinote"
    write_container(source, [entry_name])

    result = convert(source, output)

    assert output.is_file()
    assert result["converterVersion"] == "1.5.1"
    assert result["sourceContainer"]["entry"] == entry_name
    assert result["pages"] == 1


def test_reader_rejects_ambiguous_or_missing_entry(tmp_path: Path):
    both = tmp_path / "both.Jnotes"
    write_container(both, ["zip.Jzip", "zip.Jnotes"])
    missing = tmp_path / "missing.Jnotes"
    write_container(missing, ["other.bin"])

    with pytest.raises(ValueError, match="同时包含"):
        parse_jnotes_with_info(both)
    with pytest.raises(ValueError, match="缺少 zip.Jzip 或 zip.Jnotes"):
        parse_jnotes_with_info(missing)


def test_reader_rejects_duplicate_entry(tmp_path: Path):
    source = tmp_path / "duplicate.Jnotes"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        write_container(source, ["zip.Jnotes", "zip.Jnotes"])

    with pytest.raises(ValueError, match="重复"):
        parse_jnotes_with_info(source)


def test_reader_rejects_unsupported_stream_version(tmp_path: Path):
    source = tmp_path / "future.Jnotes"
    data = make_stream().replace(struct.pack(">i", 2), struct.pack(">i", 3), 1)
    write_container(source, ["zip.Jnotes"], data)

    with pytest.raises(ValueError, match="不支持的 Jnotes 内层流版本"):
        parse_jnotes_with_info(source)


def test_reader_does_not_silently_truncate_a_record(tmp_path: Path):
    source = tmp_path / "truncated.Jnotes"
    data = make_stream()[:-23] + struct.pack(">i", 1) + java_utf("PAGE")
    write_container(source, ["zip.Jnotes"], data)

    with pytest.raises(ValueError, match="记录在偏移"):
        parse_jnotes_with_info(source)

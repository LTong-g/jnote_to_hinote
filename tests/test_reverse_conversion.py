import gzip
import io
import json
import struct
import zipfile
from pathlib import Path

import pytest
from PIL import Image
from pypdf import PdfWriter

from hinote2jnotes import convert
from hinote2jnotes.cli import main
from hinote2jnotes.reader import read_ink
from jnotes2hinote.converter import background_for_page, build_pencilengine, make_image_element, make_text_element
from jnotes2hinote.reader import parse_jnotes_with_info


def test_reverse_archive_roundtrip_and_unknown_content(tmp_path: Path):
    source = tmp_path / "源笔记.hjnote"
    points = [{"x": 124, "y": 200, "p": 0.15}, {"x": 400, "y": 500, "p": 0.9}]
    ink, _ = build_pencilengine([
        {"c": {"a": 3, "c": 0x44364C7E, "d": 6, "k": points}},
        {"c": {"a": 7, "b": 4, "d": 3.04, "k": points}},
        {"c": {"a": 5, "d": 4, "k": points}},
    ], 1000 / 1240)
    # An unsupported native pen and an optional trailing native index.
    unsupported_offset = 196 + (108 + 16 + 2 * 36 + 64) + (108 + 16 + 361 * 36 + 64)
    edited = bytearray(ink)
    struct.pack_into(">I", edited, unsupported_offset + 56, 11)
    ink = bytes(edited) + b"shape-index"
    photo = io.BytesIO()
    Image.new("RGBA", (8, 8), (10, 20, 30, 128)).save(photo, "PNG")
    pdf = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(595, 842)
    writer.add_blank_page(842, 595)
    writer.write(pdf)
    text = make_text_element({"e": "云记\n🙂", "g": 80, "j": True, "t8": 1, "x": 350}, "p1", 1240, 1754, 3, 0)
    picture = make_image_element({"x": 0, "c": 124, "e": 315}, "p1", 1240, 1754, 2, 0, "picture.png")
    note = {
        "noteTitle": "华为原生导出", "id": "native-note", "extendFields": "newer-version",
        "attachment": [{"id": "native-pdf", "attachType": 3, "filePath": "/device/native_pdf"}],
    }
    p2 = {
        "id": "p2", "pageNumber": 2, "pageOrientation": 1, "pageRatio": 1240 / 1754,
        "bkgAttachmentId": "native-pdf", "bkgAttachmentIndex": 1,
    }
    p1 = {
        "id": "p1", "pageNumber": 1, "pageRatio": 1240 / 1754, "background": "base2",
        "attachment": [{"attachType": 0, "filePath": "/device/ink.bin"}, {"attachType": 9}],
        "pageElement": [text, picture, {"elementType": 7}],
    }
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("native.jhinote", gzip.compress(json.dumps({"customNoteContent": note}).encode()))
        archive.writestr("pages/p2.jhinote", gzip.compress(json.dumps({"customNotePageContent": p2}).encode()))
        archive.writestr("pages/p1.jhinote", gzip.compress(json.dumps({"customNotePageContent": p1}).encode()))
        archive.writestr("files/ink.bin", ink)
        archive.writestr("files/picture.png", photo.getvalue())
        archive.writestr("files/native_pdf", pdf.getvalue())

    result = convert(source, tmp_path / "output")
    parsed, container = parse_jnotes_with_info(Path(result["output"]))
    assert container.entry_name == "zip.Jnotes" and container.footer_recognized
    assert parsed.title == "华为原生导出"
    assert result["ignored"] == {"pen": 1, "pageAttachment": 1, "element": 1}
    assert result["strokes"] == 2 and result["pdfPages"] == 1
    first, second = parsed.pages
    assert background_for_page(first) == "base2"
    assert second["k"] > second["l"] and second["c"] == 1
    assert second["e"] == next(r.object_id for r in parsed.records if r.typ == "PDF")
    assert next(r.payload for r in parsed.records if r.typ == "PDF") == pdf.getvalue()
    highlighter, ellipse = [item["c"] for item in parsed.strokes[first["a"]]]
    assert (highlighter["a"], highlighter["c"], highlighter["d"]) == (3, 0x44364C7E, 6)
    for converted_point, original_point in zip(highlighter["k"], points):
        assert converted_point == pytest.approx(original_point, rel=1e-6)
    assert (ellipse["a"], ellipse["b"], len(ellipse["k"])) == (7, 4, 361)
    assert ellipse["d"] == pytest.approx(3.04)
    assert parsed.images[first["a"]][0][0]["e"] == 315
    assert parsed.images[first["a"]][0][1] == photo.getvalue()
    restored = parsed.texts[first["a"]][0]
    assert (restored["e"], restored["g"], restored["j"], restored["t8"]) == ("云记\n🙂", 80, True, 1)
    assert parsed.covers

    report = tmp_path / "report.json"
    manifest = tmp_path / "inputs.txt"
    manifest.write_text(source.name + "\n", encoding="utf-8")
    assert main([str(manifest), str(tmp_path / "exports"), "--pages", "1", "--report", str(report)]) == 0
    assert (tmp_path / "exports" / "源笔记.Jnotes").is_file()
    assert json.loads(report.read_text(encoding="utf-8"))["results"][0]["pdfFiles"] == 0


def test_truncated_ink_keeps_completed_strokes():
    path = [{"x": 1, "y": 2}, {"x": 3, "y": 4}]
    ink, _ = build_pencilengine([{"c": {"a": 1, "k": path}}] * 2, 1)
    decoded = read_ink(ink[:-120])
    assert next(decoded).pen == 2
    with pytest.raises(ValueError, match="PENCILENGINE"):
        next(decoded)


def test_invalid_input_does_not_replace_existing_output(tmp_path: Path):
    source = tmp_path / "invalid.hinote"
    source.write_bytes(b"invalid zip")
    output = tmp_path / "existing.Jnotes"
    output.write_bytes(b"existing output")
    with pytest.raises(ValueError, match="华为笔记"):
        convert(source, output)
    assert output.read_bytes() == b"existing output"

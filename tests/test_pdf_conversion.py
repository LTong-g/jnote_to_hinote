import gzip
import hashlib
import io
import json
import struct
import zipfile
from pathlib import Path

from PIL import Image
from PyPDF2 import PdfWriter

from jnotes2hinote.converter_v1_2_0 import convert


def java_utf(value: str) -> bytes:
    data = value.encode("utf-8")
    return struct.pack(">H", len(data)) + data


def record(typ: str, object_id: str, parent: str, payload: bytes) -> bytes:
    return b"".join(
        [
            struct.pack(">i", 1),
            java_utf(typ),
            java_utf("test"),
            java_utf(object_id),
            struct.pack(">q", len(payload)),
            java_utf(parent),
            java_utf(""),
            java_utf(""),
            payload,
        ]
    )


def make_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    writer.add_blank_page(width=842, height=842)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def make_cover() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (12, 18), "white").save(output, "PNG")
    return output.getvalue()


def make_fixture(tmp_path: Path) -> tuple[Path, bytes]:
    note_id = "note-id"
    pdf_name = "import note.pdf"
    first_page = "page-1"
    second_page = "page-2"
    note = json.dumps({"b": "PDF Fixture", "j": 1240.0, "l": 1754.0}).encode()
    page_1 = json.dumps({
        "a": first_page,
        "c": 0,
        "d": "",
        "e": "/data/.data/" + pdf_name,
        "i": True,
        "k": 1240.25,
        "l": 1754.0,
    }).encode()
    page_2 = json.dumps({
        "a": second_page,
        "c": 1,
        "d": "",
        "e": "/data/.data/" + pdf_name,
        "i": False,
        "k": 1720.3125,
        "l": 1753.9584,
    }).encode()
    stroke = json.dumps([{
        "b": 1,
        "e": 1,
        "c": {
            "a": 2,
            "c": -16777216,
            "d": 3,
            "k": [
                {"x": 10, "y": 20, "p": 0.2},
                {"x": 30, "y": 40, "p": 0.3},
            ],
        },
    }]).encode()
    pdf = make_pdf()
    jzip = b"".join([
        java_utf("TRY"),
        struct.pack(">i", 2),
        java_utf(note_id),
        record("NOTE", note_id, "", note),
        record("PDF", pdf_name, "", pdf),
        record("PAGE", first_page, note_id, page_1),
        record("PAGE", second_page, note_id, page_2),
        record("STROKE", "stroke-record", second_page, stroke),
        record("COVER", note_id + "_thumbnail.jpg", "", make_cover()),
        struct.pack(">i", 0),
        b"Lucky",
    ])
    source = tmp_path / "fixture.Jnotes"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("zip.Jzip", jzip)
    return source, pdf


def test_pdf_is_embedded_and_pages_reference_it(tmp_path: Path):
    source, pdf = make_fixture(tmp_path)
    output = tmp_path / "fixture.hinote"

    result = convert(source, output)

    assert result["converterVersion"] == "1.2.0"
    assert result["pdfStats"]["pdfBackedPages"] == 2
    assert result["pdfStats"]["sourcePdfSha256"]["import note.pdf"] == hashlib.sha256(pdf).hexdigest()

    with zipfile.ZipFile(output) as archive:
        top_name = next(name for name in archive.namelist() if name.endswith(".jhinote") and "/" not in name)
        top = json.loads(gzip.decompress(archive.read(top_name)))
        content = top["customNoteContent"]
        assert content["noteType"] == 101
        assert content["noteIcon"] == "import_pdf"
        assert content["hasCover"] == 0
        assert len(content["attachment"]) == 1
        pdf_attachment = content["attachment"][0]
        assert pdf_attachment["attachType"] == 3
        pdf_filename = pdf_attachment["filePath"].rsplit("/", 1)[-1]
        assert archive.read("files/" + pdf_filename) == pdf

        pages = []
        for name in archive.namelist():
            if name.startswith("pages/"):
                page = json.loads(gzip.decompress(archive.read(name)))
                pages.append(page["customNotePageContent"])
        pages.sort(key=lambda page: page["pageNumber"])
        assert [page["bkgAttachmentIndex"] for page in pages] == [0, 1]
        assert all(page["bkgAttachmentId"] == pdf_attachment["id"] for page in pages)
        assert pages[0]["pageElement"] == []
        assert pages[0]["thumbnail"]
        assert pages[1]["attachment"][0]["attachType"] == 0
        assert pages[1]["pageRatio"] == 1720.3125 / 1753.9584

        custom_md = json.loads(gzip.decompress(archive.read("custom_md.jhinote")))
        assert any(
            item["fileMdStr"] == hashlib.sha256(pdf).hexdigest().upper()
            for item in custom_md["customMdContents"]
        )


def test_pdf_page_index_errors_before_output(tmp_path: Path):
    source, _ = make_fixture(tmp_path)
    broken = tmp_path / "broken.Jnotes"
    with zipfile.ZipFile(source) as source_zip:
        jzip = source_zip.read("zip.Jzip").replace(b'"c": 1', b'"c": 2')
    with zipfile.ZipFile(broken, "w") as archive:
        archive.writestr("zip.Jzip", jzip)

    output = tmp_path / "broken.hinote"
    try:
        convert(broken, output)
    except ValueError as exc:
        assert "越界" in str(exc)
    else:
        raise AssertionError("越界 PDF 页码没有失败")
    assert not output.exists()

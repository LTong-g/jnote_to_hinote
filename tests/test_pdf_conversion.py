import gzip
import hashlib
import io
import json
import struct
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, JpegImagePlugin
from PyPDF2 import PdfWriter

from jnotes2hinote.converter_v1_2_0 import convert
from jnotes2hinote.converter_v1_5_3 import convert as convert_current


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


def make_visible_pdf() -> bytes:
    pages = []
    for color, label in (("#205493", "FIRST"), ("#c84242", "SECOND")):
        page = Image.new("RGB", (595, 842), color)
        draw = ImageDraw.Draw(page)
        draw.rectangle((40, 40, 555, 802), outline="white", width=16)
        draw.text((80, 100), label, fill="white", stroke_width=2, stroke_fill="black")
        pages.append(page)
    output = io.BytesIO()
    pages[0].save(output, "PDF", save_all=True, append_images=pages[1:], resolution=72)
    return output.getvalue()


def make_fixture(
    tmp_path: Path,
    pdf: bytes | None = None,
    *,
    landscape: bool = False,
) -> tuple[Path, bytes]:
    note_id = "note-id"
    pdf_name = "import note.pdf"
    first_page = "page-1"
    second_page = "page-2"
    note_width, note_height = (1754.0, 1240.0) if landscape else (1240.0, 1754.0)
    first_width, first_height = (1754.0, 1240.0) if landscape else (1240.25, 1754.0)
    second_width, second_height = (1600.0, 1200.0) if landscape else (1720.3125, 1753.9584)
    note = json.dumps({"b": "PDF Fixture", "j": note_width, "l": note_height}).encode()
    page_1 = json.dumps({
        "a": first_page,
        "c": 0,
        "d": "",
        "e": "/data/.data/" + pdf_name,
        "i": True,
        "k": first_width,
        "l": first_height,
    }).encode()
    page_2 = json.dumps({
        "a": second_page,
        "c": 1,
        "d": "",
        "e": "/data/.data/" + pdf_name,
        "i": False,
        "k": second_width,
        "l": second_height,
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
    pdf = pdf if pdf is not None else make_pdf()
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


def test_current_core_preserves_pdf_for_zip_jnotes_variant(tmp_path: Path):
    source, pdf = make_fixture(tmp_path)
    variant = tmp_path / "variant.Jnotes"
    with zipfile.ZipFile(source) as source_zip, zipfile.ZipFile(variant, "w") as archive:
        archive.writestr("zip.Jnotes", source_zip.read("zip.Jzip"))

    output = tmp_path / "variant.hinote"
    result = convert_current(variant, output)

    assert result["converterVersion"] == "1.5.3"
    assert result["sourceContainer"]["entry"] == "zip.Jnotes"
    assert result["pdfStats"]["sourcePdfSha256"]["import note.pdf"] == hashlib.sha256(pdf).hexdigest()
    with zipfile.ZipFile(output) as archive:
        assert any(archive.read(name) == pdf for name in archive.namelist() if name.startswith("files/"))


def test_current_core_generates_native_quality_thumbnail_for_every_pdf_page(tmp_path: Path):
    source, _ = make_fixture(tmp_path, pdf=make_visible_pdf())
    output = tmp_path / "visible.hinote"
    result = convert_current(source, output)

    assert result["thumbnailStats"] == {
        "generated": 2,
        "pdfRendered": 2,
        "regularRendered": 0,
        "maxEdge": 1080,
        "jpegQuality": 100,
    }
    with zipfile.ZipFile(output) as archive:
        archive_names = archive.namelist()
        pages = []
        for name in archive_names:
            if name.startswith("pages/"):
                pages.append(json.loads(gzip.decompress(archive.read(name))))
        pages.sort(key=lambda page: page["customNotePageContent"]["pageNumber"])
        assert len(pages) == 2
        images = []
        for page in pages:
            content = page["customNotePageContent"]
            filename = content["thumbnail"].rsplit("/", 1)[-1]
            assert filename
            assert "files/" + filename in archive.namelist()
            assert any(item["name"] == filename for item in page["fileList"])
            detail = json.loads(content["data1"])["detailFileMap"]
            assert filename in json.loads(detail)
            image = Image.open(io.BytesIO(archive.read("files/" + filename)))
            image.load()
            assert image.format == "JPEG"
            ratio = content["pageRatio"]
            expected = (
                (1080, round(ratio * 1080))
                if content["pageOrientation"] == 1
                else (round(ratio * 1080), 1080)
            )
            assert image.size == expected
            assert max(image.size) == 1080
            assert JpegImagePlugin.get_sampling(image) == 2
            assert {value for table in image.quantization.values() for value in table} == {1}
            images.append(image.convert("RGB"))
        assert images[0].getpixel((20, 20)) != images[1].getpixel((20, 20))

        top_name = next(
            name
            for name in archive_names
            if "/" not in name and name.endswith(".jhinote") and name != "custom_md.jhinote"
        )
        top = json.loads(gzip.decompress(archive.read(top_name)))
        physical_files = [name.rsplit("/", 1)[-1] for name in archive_names if name.startswith("files/")]
        assert physical_files[:2] == [item["name"] for item in top["fileList"]]

        custom_md = json.loads(gzip.decompress(archive.read("custom_md.jhinote")))
        assert [item["fileNameMdStr"] for item in custom_md["customMdContents"]] == [
            hashlib.sha256(name.encode("utf-8")).hexdigest()
            for name in physical_files
        ]


def test_current_core_uses_native_metadata_for_landscape_pages(tmp_path: Path):
    source, _ = make_fixture(tmp_path, pdf=make_visible_pdf(), landscape=True)
    output = tmp_path / "landscape.hinote"

    result = convert_current(source, output)

    assert result["pageRatio"] == 1240 / 1754
    assert result["pageOrientation"] == 1
    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
        top_name = next(
            name
            for name in names
            if "/" not in name and name.endswith(".jhinote") and name != "custom_md.jhinote"
        )
        top = json.loads(gzip.decompress(archive.read(top_name)))["customNoteContent"]
        assert top["pageRatio"] == 1240 / 1754
        assert top["pageOrientation"] == 1

        pages = [
            json.loads(gzip.decompress(archive.read(name)))
            for name in names
            if name.startswith("pages/")
        ]
        pages.sort(key=lambda page: page["customNotePageContent"]["pageNumber"])
        assert [page["customNotePageContent"]["pageRatio"] for page in pages] == [
            1240 / 1754,
            1200 / 1600,
        ]
        assert all(page["customNotePageContent"]["pageOrientation"] == 1 for page in pages)
        for page in pages:
            content = page["customNotePageContent"]
            filename = content["thumbnail"].rsplit("/", 1)[-1]
            image = Image.open(io.BytesIO(archive.read("files/" + filename)))
            assert image.size == (1080, round(content["pageRatio"] * 1080))


def test_current_core_generates_thumbnails_for_mixed_pdf_and_regular_pages(tmp_path: Path):
    note_id = "mixed-note"
    pdf_name = "mixed.pdf"
    page_1, blank_page, page_3 = "pdf-1", "blank", "pdf-2"
    note = json.dumps({"b": "Mixed", "j": 1240.0, "l": 1754.0}).encode()
    pages = [
        {"a": page_1, "c": 0, "d": "", "e": "/data/.data/" + pdf_name, "k": 1240.0, "l": 1754.0},
        {"a": blank_page, "d": "PageBg/White_Blank_Paper", "k": 1240.0, "l": 1754.0},
        {"a": page_3, "c": 1, "d": "", "e": "/data/.data/" + pdf_name, "k": 1240.0, "l": 1754.0},
    ]
    stroke = json.dumps([{
        "b": 1,
        "e": 1,
        "c": {"a": 2, "c": -16777216, "d": 3, "k": [{"x": 10, "y": 20}, {"x": 80, "y": 120}]},
    }]).encode()
    stream = b"".join([
        java_utf("TRY"),
        struct.pack(">i", 2),
        java_utf(note_id),
        record("NOTE", note_id, "", note),
        record("PDF", pdf_name, "", make_visible_pdf()),
        *(record("PAGE", page["a"], note_id, json.dumps(page).encode()) for page in pages),
        record("STROKE", "blank-stroke", blank_page, stroke),
        struct.pack(">i", 0),
        b"Lucky",
    ])
    source = tmp_path / "mixed.Jnotes"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("zip.Jzip", stream)
    output = tmp_path / "mixed.hinote"

    result = convert_current(source, output)

    assert result["thumbnailStats"]["generated"] == 3
    assert result["thumbnailStats"]["pdfRendered"] == 2
    assert result["thumbnailStats"]["regularRendered"] == 1
    with zipfile.ZipFile(output) as archive:
        pages_out = []
        for name in archive.namelist():
            if name.startswith("pages/"):
                pages_out.append(json.loads(gzip.decompress(archive.read(name)))["customNotePageContent"])
        pages_out.sort(key=lambda page: page["pageNumber"])
        assert [page["bkgAttachmentIndex"] for page in pages_out] == [0, 0, 1]
        assert pages_out[0]["bkgAttachmentId"]
        assert pages_out[1]["bkgAttachmentId"] == ""
        assert pages_out[2]["bkgAttachmentId"] == pages_out[0]["bkgAttachmentId"]
        assert [page["cloudSyncState"] for page in pages_out] == [0, 0, 0]
        assert all(page["thumbnail"] for page in pages_out)

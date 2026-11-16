"""Map Huawei Notes pages and editable objects into Jnotes records."""

from __future__ import annotations

import math
import os
import time
import uuid
import zipfile
from collections import Counter
from collections.abc import Iterator
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from zlib import error as ZlibError

from PIL import Image
from pypdf import PdfReader
from pypdf.errors import PyPdfError

from jnotes2hinote._version import __version__
from jnotes2hinote.converter import J_TO_HW_PEN
from jnotes2hinote.reader import JRecord
from jnotes2hinote.thumbnail import PdfThumbnailRenderer, render_regular_thumbnail

from .reader import NO_SHAPE, HinoteReader, InkStroke, code, number, objects, read_ink
from .writer import OUTPUT_SUFFIX, OUTPUT_SUFFIXES, json_bytes, write_jnotes

PENS = {huawei: jnotes for jnotes, huawei in J_TO_HW_PEN.items()}
SHAPES = {0: (6, 0), 16: (6, 12), 7: (7, 3), 10: (7, 4)}
PAPERS = {
    "base1": ("PageBg/White_Blank_Paper", 0),
    "base2": ("PageBg/White_Graph_Paper", 2),
    "base3": ("PageBg/White_Graph_Paper", 0),
    "base4": ("PageBg/White_Line_paper_1_Paper", 0),
    "base5": ("PageBg/White_Line_paper_1_Paper", -1),
    "base6": ("PageBg/White_Dotted_Paper", 0),
}
ASSET_ERRORS = (zipfile.BadZipFile, OSError, RuntimeError, EOFError, ZlibError)


def _record(kind: str, object_id: str, parent: str, payload: bytes, *, binary: bytes = b"",
            aux_path: str = "") -> JRecord:
    return JRecord(kind, "", object_id, parent, aux_path, "", payload, binary)


def _asset(reader: HinoteReader, reference: Any) -> bytes | None:
    try:
        return reader.read_asset(reference)
    except ASSET_ERRORS:
        return None


def _page_size(page: dict[str, Any], note: dict[str, Any]) -> tuple[float, float]:
    orientation = code(page.get("pageOrientation"), code(note.get("pageOrientation"), 0))
    ratio = number(page.get("pageRatio"), number(note.get("pageRatio"), 1240 / 1754))
    if not 0.01 <= ratio <= 100:
        ratio = 1240 / 1754
    # Older exports used width / height and did not set the landscape flag.
    short_over_long = min(ratio, 1 / ratio)
    if orientation == 1 or ratio > 1:
        return 1754.0, 1754 * short_over_long
    return 1240.0, 1240 / short_over_long


def _signed_argb(value: int) -> int:
    return value - (1 << 32) if value >= (1 << 31) else value


def _channel(value: float, default: float = 0) -> int:
    return round(max(0, min(1, number(value, default))) * 255)


def _stroke(stroke: InkStroke, width: float, order: int, ignored: Counter[str]) -> dict[str, Any] | None:
    geom = None if stroke.shape == NO_SHAPE else SHAPES.get(stroke.shape)
    if stroke.shape != NO_SHAPE and (geom is None or stroke.pen != 2):
        ignored["geometry"] += 1
        return None
    pen = geom[0] if geom else PENS.get(stroke.pen)
    if pen is None:
        ignored["pen"] += 1
        return None
    if not math.isfinite(stroke.width) or stroke.width <= 0:
        ignored["invalidStroke"] += 1
        return None
    points = []
    for x, y, pressure in stroke.points:
        if not math.isfinite(x) or not math.isfinite(y):
            ignored["invalidStroke"] += 1
            return None
        points.append({
            "x": x * width / 1000,
            "y": y * width / 1000,
            "p": max(0.001, min(1, number(pressure, 0.2))),
        })
    blue, green, red = map(_channel, stroke.bgr)
    opacity = _channel(stroke.opacity, 1) if pen == 3 else 255
    color = _signed_argb((opacity << 24) | (red << 16) | (green << 8) | blue)
    style = {"a": pen, "c": color, "d": stroke.width * (3 / 16 if pen == 3 else 1), "k": points}
    if geom:
        style["b"] = geom[1]
        if stroke.shape == 0:
            style["l"] = [points[0], points[-1]]
    return {"b": order, "e": order, "c": style}


class TextStyle(HTMLParser):
    """Read the basic formatting emitted by the forward converter."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden = 0
        self.style: dict[str, Any] = {
            "f": -16777216, "g": 40.0, "j": False, "k": False, "m": False, "t8": 0,
        }

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self.hidden += 1
            return
        if self.hidden:
            return
        values = dict(attrs)
        if tag == "br":
            self.parts.append("\n")
        elif tag in {"b", "strong"}:
            self.style["j"] = True
        elif tag in {"i", "em"}:
            self.style["k"] = True
        elif tag == "u":
            self.style["m"] = True
        elif tag in {"div", "p"}:
            self.style["t8"] = {"center": 1, "right": 2}.get(values.get("align"), 0)
        elif tag == "hw_font":
            size = number(values.get("size"), 1)
            if 0 < size <= 1000:
                self.style["g"] = size * 40
        elif tag == "font":
            color = values.get("color", "") or ""
            if color.startswith("#") and len(color) in (7, 9):
                try:
                    packed = int(color[1:], 16)
                except ValueError:
                    return
                self.style["f"] = _signed_argb(packed | (0xFF000000 if len(color) == 7 else 0))

    def handle_endtag(self, tag: str) -> None:
        if self.hidden and tag in {"script", "style"}:
            self.hidden -= 1
        if tag in {"div", "p"} and self.parts and not self.parts[-1].endswith("\n"):
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            if self.parts and self.parts[-1] == "\n":
                data = data.removeprefix("\n")
            self.parts.append(data)


def _box(element: dict[str, Any], width: float, height: float) -> dict[str, float]:
    return {
        "x": number(element.get("positionX")) * width,
        "y": number(element.get("positionY")) * height,
        "c": max(0.001, number(element.get("width"), 0.3)) * width,
        "d": max(0.001, number(element.get("height"), 0.05)) * height,
    }


def _text(element: dict[str, Any]) -> dict[str, Any]:
    parser = TextStyle()
    html = element.get("html")
    if isinstance(html, str):
        try:
            parser.feed(html)
            parser.close()
        except AssertionError:
            # HTMLParser raises on malformed declarations in some Python versions.
            pass
    text = element.get("contentText")
    if not isinstance(text, str) or not text:
        text = "".join(parser.parts).rstrip("\n")
    return {"e": text, **parser.style}


def _image(data: bytes | None) -> tuple[bytes, str] | None:
    if not data:
        return None
    try:
        with Image.open(BytesIO(data)) as image:
            ext = {"JPEG": ".jpg", "PNG": ".png", "GIF": ".gif"}.get(image.format or "")
            if ext is None:
                return None
            image.verify()
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError):
        return None
    return data, ext


def _pdf_assets(
    reader: HinoteReader, note: dict[str, Any], pages: list[dict[str, Any]], ignored: Counter[str],
) -> dict[str, tuple[str, bytes, int]]:
    references = {str(page.get("bkgAttachmentId") or "") for page in pages} - {""}
    assets = {}
    for attach in objects(note.get("attachment")):
        if code(attach.get("isDelete"), 0):
            continue
        key = str(attach.get("id") or "")
        if code(attach.get("attachType")) != 3:
            ignored["noteAttachment"] += 1
            continue
        if key not in references or key in assets:
            continue
        data = _asset(reader, attach.get("filePath"))
        if not data:
            continue
        try:
            pdf = PdfReader(BytesIO(data))
            if pdf.is_encrypted:
                continue
            page_count = len(pdf.pages)
        except (PyPdfError, ValueError, TypeError, KeyError, OSError, RecursionError):
            continue
        assets[key] = (uuid.uuid4().hex + ".pdf", data, page_count)
    return assets


def _preview(
    reader: HinoteReader, page: dict[str, Any], strokes: list[dict[str, Any]],
    images: list[tuple[dict[str, Any], bytes]], texts: list[dict[str, Any]],
    width: float, height: float, pdf: tuple[str, bytes, int] | None,
    ignored: Counter[str],
) -> bytes | None:
    thumbnail = _asset(reader, page.get("thumbnail"))
    if _image(thumbnail):
        try:
            with Image.open(BytesIO(thumbnail)) as image:
                image.thumbnail((1200, 1200))
                out = BytesIO()
                image.convert("RGB").save(out, "JPEG", quality=90)
                return out.getvalue()
        except (OSError, ValueError):
            pass
    # Bound preview allocations even if page elements contain extreme dimensions.
    preview_images = [
        (box, data) for box, data in images
        if max(abs(box["x"]) / width, abs(box["y"]) / height, box["c"] / width, box["d"] / height) <= 4
    ]
    overlays = {
        "page_width": width, "page_height": height, "strokes": strokes, "images": preview_images, "texts": texts,
    }
    try:
        if pdf:
            with PdfThumbnailRenderer() as renderer:
                return renderer.render(asset_key=pdf[0], payload=pdf[1], page_index=pdf[2], **overlays)
        return render_regular_thumbnail(cover=None, **overlays)
    except (OSError, RuntimeError, ValueError, OverflowError, Image.DecompressionBombError):
        ignored["coverPreview"] += 1
        return None


def _records(
    reader: HinoteReader, note: dict[str, Any], pages: list[dict[str, Any]], note_id: str, title: str,
    ignored: Counter[str], stats: Counter[str],
) -> Iterator[JRecord]:
    width, height = _page_size(pages[0], note)
    yield _record("NOTE", note_id, "", json_bytes({"a": note_id, "b": title, "j": width, "l": height}))
    pdfs = _pdf_assets(reader, note, pages, ignored)
    written_pdfs = set()
    cover = None
    for order, page in enumerate(pages):
        width, height = _page_size(page, note)
        page_id = str(uuid.uuid4())
        template = str(page.get("background") or "base1")
        if template not in PAPERS or code(page.get("pageColor"), -1) not in (-1, 0xFFFFFFFF):
            ignored["background"] += 1
        paper, parts = PAPERS.get(template, PAPERS["base1"])
        page_meta = {
            "a": page_id, "c": order, "d": paper, "e": "", "i": False, "k": width, "l": height,
            "p": json_bytes({"paperBg": paper, "horParts": parts, "verParts": parts}).decode("utf-8"),
        }
        pdf_id = str(page.get("bkgAttachmentId") or "")
        pdf_index = code(page.get("bkgAttachmentIndex"))
        pdf = None
        if pdf_id:
            asset = pdfs.get(pdf_id)
            if asset and 0 <= pdf_index < asset[2]:
                name, data, _ = asset
                pdf = (name, data, pdf_index)
                if pdf_id not in written_pdfs:
                    yield _record("PDF", name, "", data)
                    written_pdfs.add(pdf_id)
                    stats["pdfFiles"] += 1
                page_meta.update(c=pdf_index, e=name)
                stats["pdfPages"] += 1
            else:
                ignored["pdfBackground"] += 1
        yield _record("PAGE", page_id, note_id, json_bytes(page_meta))

        strokes = []
        for attach in objects(page.get("attachment")):
            if code(attach.get("isDelete"), 0):
                continue
            if code(attach.get("attachType")) != 0:
                ignored["pageAttachment"] += 1
                continue
            data = _asset(reader, attach.get("filePath"))
            try:
                for source_stroke in read_ink(data or b""):
                    stroke = _stroke(source_stroke, width, len(strokes) + 1, ignored)
                    if stroke is not None:
                        strokes.append(stroke)
            except ValueError:
                ignored["inkAttachment"] += 1
        if strokes:
            yield _record("STROKE", str(uuid.uuid4()), page_id, json_bytes(strokes))
            stats["strokes"] += len(strokes)

        images = []
        texts = []
        elements = sorted(objects(page.get("pageElement")), key=lambda item: number(item.get("positionZ")))
        for layer, element in enumerate(elements):
            if code(element.get("isDelete"), 0):
                continue
            element_type = code(element.get("elementType"))
            if element_type not in (0, 1):
                ignored["element"] += 1
                continue
            element_id = str(uuid.uuid4())
            box = _box(element, width, height)
            if not all(math.isfinite(value) for value in box.values()):
                ignored["invalidElement"] += 1
                continue
            meta = {"a": element_id, "b": layer, **box}
            if element_type == 0:
                if number(element.get("angle")) % 360:
                    ignored["textRotation"] += 1
                texts.append({**meta, **_text(element)})
                continue
            image = _image(_asset(reader, element.get("filePath")))
            if image is None:
                ignored["image"] += 1
                continue
            blob, extension = image
            meta["e"] = number(element.get("angle")) % 360
            yield _record("IMAGE", element_id, page_id, json_bytes(meta), binary=blob, aux_path=element_id + extension)
            if order == 0:
                images.append((meta, blob))
            stats["images"] += 1
        if texts:
            yield _record("TEXT", str(uuid.uuid4()), page_id, json_bytes(texts))
            stats["texts"] += len(texts)
        stats["pages"] += 1
        if order == 0:
            cover = _preview(reader, page, strokes, images, texts, width, height, pdf, ignored)
    if cover:
        yield _record("COVER", f"{note_id}_thumbnail.jpg", "", cover)


def convert(hinote_path: Path, output: Path, page_limit: int | None = None) -> dict[str, Any]:
    """Convert a Huawei export without gating on an app version or generator."""
    source, destination = Path(hinote_path), Path(output)
    if destination.suffix.casefold() not in OUTPUT_SUFFIXES:
        destination = destination.with_name(destination.name + OUTPUT_SUFFIX)
    if source.resolve() == destination.resolve() or (destination.exists() and source.samefile(destination)):
        raise ValueError("输出不能覆盖原始华为笔记")
    if page_limit is not None and page_limit < 0:
        raise ValueError("页数必须大于等于 0")
    ignored: Counter[str] = Counter()
    stats: Counter[str] = Counter(dict.fromkeys(("pages", "strokes", "images", "texts", "pdfFiles", "pdfPages"), 0))
    started = time.perf_counter()
    try:
        with zipfile.ZipFile(source) as archive:
            reader = HinoteReader(archive, ignored)
            note = reader.read_note()
            pages = reader.read_pages(note)
            title = str(note.get("noteTitle") or source.stem)
            note_id = str(uuid.uuid4())
            destination.parent.mkdir(parents=True, exist_ok=True)
            with TemporaryDirectory(prefix=".hinote2jnotes-", dir=destination.parent) as workspace:
                candidate = Path(workspace) / "note.Jnotes"
                write_jnotes(candidate, note_id, _records(
                    reader, note, pages[:page_limit or None], note_id, title, ignored, stats,
                ))
                os.replace(candidate, destination)
    except (zipfile.BadZipFile, EOFError, ZlibError) as exc:
        raise ValueError("华为笔记压缩包或正文数据已损坏") from exc
    return {
        "schemaVersion": 2, "version": __version__, "direction": "hinote2jnotes",
        "title": title, "source": str(source), "output": str(destination),
        "sourcePages": len(pages), **stats, "ignored": dict(ignored), "ignoredTotal": sum(ignored.values()),
        "elapsedSeconds": round(time.perf_counter() - started, 3),
    }

"""Native-quality Hinote thumbnail rendering for converter v1.5.2.

Huawei Notes samples use a fixed 1080-pixel thumbnail height, JPEG quality
100, and 4:2:0 chroma subsampling.  Rendering at twice the final resolution
before a Lanczos downsample keeps thin handwritten strokes legible.
"""
from __future__ import annotations

import io
from collections.abc import Mapping
from typing import Any

from PIL import Image, ImageDraw, UnidentifiedImageError

from .converter_v1_1_2 import _load_thumbnail_font

THUMBNAIL_HEIGHT = 1080
THUMBNAIL_SUPERSAMPLE = 2
THUMBNAIL_JPEG_QUALITY = 100
THUMBNAIL_JPEG_SUBSAMPLING = 2


def thumbnail_dimensions(page_width: float, page_height: float) -> tuple[int, int]:
    """Return the native observed thumbnail dimensions for a page ratio."""
    if page_width <= 0 or page_height <= 0:
        raise ValueError("缩略图页面尺寸必须为正数")
    return max(1, round(page_width / page_height * THUMBNAIL_HEIGHT)), THUMBNAIL_HEIGHT


def _argb(value: Any, default: int = -16777216) -> tuple[int, int, int, int]:
    argb = int(value if value is not None else default) & 0xFFFFFFFF
    alpha = (argb >> 24) & 255
    if alpha == 0:
        alpha = 255
    return alpha, (argb >> 16) & 255, (argb >> 8) & 255, argb & 255


def _work_dimensions(page_width: float, page_height: float) -> tuple[int, int, int, int]:
    target_width, target_height = thumbnail_dimensions(page_width, page_height)
    return (
        target_width,
        target_height,
        target_width * THUMBNAIL_SUPERSAMPLE,
        target_height * THUMBNAIL_SUPERSAMPLE,
    )


def _cover_background(cover: bytes | None, work_size: tuple[int, int]) -> Image.Image:
    canvas = Image.new("RGBA", work_size, "white")
    if not cover:
        return canvas
    try:
        image = Image.open(io.BytesIO(cover)).convert("RGBA")
        image = image.resize(work_size, Image.Resampling.LANCZOS)
        canvas.alpha_composite(image)
    except (OSError, UnidentifiedImageError, ValueError):
        # A source COVER record is optional preview data.  A bad one must not
        # prevent the editable note from getting a usable thumbnail.
        pass
    return canvas


def _add_image(
    canvas: Image.Image,
    meta: Mapping[str, Any],
    data: bytes,
    *,
    page_width: float,
    page_height: float,
) -> None:
    if not data:
        return
    try:
        source = Image.open(io.BytesIO(data)).convert("RGBA")
        scale_x = canvas.width / page_width
        scale_y = canvas.height / page_height
        x = round(float(meta.get("x", 0)) * scale_x)
        y = round(float(meta.get("y", 0)) * scale_y)
        width = max(1, round(float(meta.get("c", page_width)) * scale_x))
        height = max(1, round(float(meta.get("d", page_height)) * scale_y))
        source = source.resize((width, height), Image.Resampling.LANCZOS)
        angle = float(meta.get("e", 0) or 0)
        if angle > 180:
            angle -= 360
        if angle:
            rotated = source.rotate(-angle, resample=Image.Resampling.BICUBIC, expand=True)
            x -= (rotated.width - width) // 2
            y -= (rotated.height - height) // 2
            source = rotated
        layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        layer.alpha_composite(source, (x, y))
        canvas.alpha_composite(layer)
    except (OSError, UnidentifiedImageError, ValueError, TypeError):
        # Keep a malformed optional image from invalidating the full note.
        pass


def _add_strokes(
    canvas: Image.Image,
    strokes: list[dict[str, Any]],
    *,
    page_width: float,
    page_height: float,
) -> None:
    draw = ImageDraw.Draw(canvas, "RGBA")
    scale_x = canvas.width / page_width
    scale_y = canvas.height / page_height
    for record in strokes:
        style = record.get("c", {})
        if int(style.get("a", -1)) == 10:
            continue
        points = style.get("k") or []
        if not points:
            continue
        alpha, red, green, blue = _argb(style.get("c"))
        width = max(1, round(float(style.get("d", 3)) * scale_x))
        xy = [
            (float(point.get("x", 0)) * scale_x, float(point.get("y", 0)) * scale_y)
            for point in points
        ]
        if len(xy) == 1:
            x, y = xy[0]
            radius = max(1, width / 2)
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(red, green, blue, alpha))
        else:
            draw.line(xy, fill=(red, green, blue, alpha), width=width, joint="curve")


def _add_texts(
    canvas: Image.Image,
    texts: list[dict[str, Any]],
    *,
    page_width: float,
    page_height: float,
) -> None:
    draw = ImageDraw.Draw(canvas, "RGBA")
    scale_x = canvas.width / page_width
    scale_y = canvas.height / page_height
    for text in texts:
        value = str(text.get("e", ""))[:100]
        if not value:
            continue
        x = round(float(text.get("x", 0)) * scale_x)
        y = round(float(text.get("y", 0)) * scale_y)
        size = max(12, round(float(text.get("g", 40)) * scale_x))
        font = _load_thumbnail_font(size)
        alpha, red, green, blue = _argb(text.get("f"))
        try:
            draw.text((x, y), value, fill=(red, green, blue, alpha), font=font)
        except UnicodeEncodeError:
            draw.text((x, y), value.encode("ascii", errors="replace").decode("ascii"), fill=(red, green, blue, alpha), font=font)


def _encode_thumbnail(canvas: Image.Image, target_size: tuple[int, int]) -> bytes:
    image = canvas.resize(target_size, Image.Resampling.LANCZOS).convert("RGB")
    output = io.BytesIO()
    image.save(
        output,
        "JPEG",
        quality=THUMBNAIL_JPEG_QUALITY,
        subsampling=THUMBNAIL_JPEG_SUBSAMPLING,
        optimize=True,
    )
    return output.getvalue()


def render_regular_thumbnail(
    *,
    page_width: float,
    page_height: float,
    strokes: list[dict[str, Any]],
    images: list[tuple[dict[str, Any], bytes]],
    texts: list[dict[str, Any]],
    cover: bytes | None,
) -> bytes:
    """Render an ordinary Jnotes page as a native-quality Hinote thumbnail."""
    target_width, target_height, work_width, work_height = _work_dimensions(page_width, page_height)
    canvas = _cover_background(cover, (work_width, work_height))
    for meta, data in images:
        _add_image(canvas, meta, data, page_width=page_width, page_height=page_height)
    _add_strokes(canvas, strokes, page_width=page_width, page_height=page_height)
    _add_texts(canvas, texts, page_width=page_width, page_height=page_height)
    return _encode_thumbnail(canvas, (target_width, target_height))


class PdfThumbnailRenderer:
    """Cache PDFium documents and composite their pages with Jnotes overlays."""

    def __init__(self) -> None:
        self._documents: dict[str, Any] = {}

    def _document(self, key: str, payload: bytes) -> Any:
        document = self._documents.get(key)
        if document is not None:
            return document
        try:
            import pypdfium2 as pdfium
        except ImportError as exc:  # pragma: no cover - dependency/packaging error
            raise RuntimeError("PDF 缩略图渲染需要 pypdfium2，请重新安装 Jnotes2Hinote") from exc
        try:
            document = pdfium.PdfDocument(payload)
        except Exception as exc:
            raise ValueError(f"无法打开用于缩略图的 PDF：{exc}") from exc
        self._documents[key] = document
        return document

    def render(
        self,
        *,
        asset_key: str,
        payload: bytes,
        page_index: int,
        page_width: float,
        page_height: float,
        strokes: list[dict[str, Any]],
        images: list[tuple[dict[str, Any], bytes]],
        texts: list[dict[str, Any]],
    ) -> bytes:
        target_width, target_height, work_width, work_height = _work_dimensions(page_width, page_height)
        document = self._document(asset_key, payload)
        try:
            page = document[page_index]
            _, pdf_height = page.get_size()
            bitmap = page.render(scale=work_height / pdf_height)
            background = bitmap.to_pil().convert("RGBA")
        except Exception as exc:
            raise ValueError(f"无法渲染 PDF 缩略图第 {page_index + 1} 页：{exc}") from exc

        canvas = Image.new("RGBA", (work_width, work_height), "white")
        background.thumbnail((work_width, work_height), Image.Resampling.LANCZOS)
        canvas.alpha_composite(background, ((work_width - background.width) // 2, (work_height - background.height) // 2))
        _add_strokes(canvas, strokes, page_width=page_width, page_height=page_height)
        for meta, data in images:
            _add_image(canvas, meta, data, page_width=page_width, page_height=page_height)
        _add_texts(canvas, texts, page_width=page_width, page_height=page_height)
        return _encode_thumbnail(canvas, (target_width, target_height))

    def close(self) -> None:
        for document in self._documents.values():
            close = getattr(document, "close", None)
            if close:
                close()
        self._documents.clear()

    def __enter__(self) -> PdfThumbnailRenderer:  # noqa: PYI034 - Python 3.10 has no typing.Self
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

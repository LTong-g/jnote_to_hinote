"""Orientation-safe Hinote thumbnail rendering for converter v1.5.3."""
from __future__ import annotations

from typing import Any

from PIL import Image

from . import thumbnail_renderer_v1_5_2 as _base

THUMBNAIL_MAX_EDGE = 1080
THUMBNAIL_SUPERSAMPLE = _base.THUMBNAIL_SUPERSAMPLE
THUMBNAIL_JPEG_QUALITY = _base.THUMBNAIL_JPEG_QUALITY
THUMBNAIL_JPEG_SUBSAMPLING = _base.THUMBNAIL_JPEG_SUBSAMPLING


def thumbnail_dimensions(page_width: float, page_height: float) -> tuple[int, int]:
    """Keep the longest thumbnail edge at the native 1080-pixel limit."""
    if page_width <= 0 or page_height <= 0:
        raise ValueError("缩略图页面尺寸必须为正数")
    if page_width <= page_height:
        return max(1, round(page_width / page_height * THUMBNAIL_MAX_EDGE)), THUMBNAIL_MAX_EDGE
    return THUMBNAIL_MAX_EDGE, max(1, round(page_height / page_width * THUMBNAIL_MAX_EDGE))


def _work_dimensions(page_width: float, page_height: float) -> tuple[int, int, int, int]:
    target_width, target_height = thumbnail_dimensions(page_width, page_height)
    return (
        target_width,
        target_height,
        target_width * THUMBNAIL_SUPERSAMPLE,
        target_height * THUMBNAIL_SUPERSAMPLE,
    )


def render_regular_thumbnail(
    *,
    page_width: float,
    page_height: float,
    strokes: list[dict[str, Any]],
    images: list[tuple[dict[str, Any], bytes]],
    texts: list[dict[str, Any]],
    cover: bytes | None,
) -> bytes:
    """Render an ordinary page without allowing landscape thumbnails over 1080 px."""
    target_width, target_height, work_width, work_height = _work_dimensions(page_width, page_height)
    canvas = _base._cover_background(cover, (work_width, work_height))
    for meta, data in images:
        _base._add_image(canvas, meta, data, page_width=page_width, page_height=page_height)
    _base._add_strokes(canvas, strokes, page_width=page_width, page_height=page_height)
    _base._add_texts(canvas, texts, page_width=page_width, page_height=page_height)
    return _base._encode_thumbnail(canvas, (target_width, target_height))


class PdfThumbnailRenderer(_base.PdfThumbnailRenderer):
    """Render PDF pages with the v1.5.3 longest-edge dimensions."""

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
            pdf_width, pdf_height = page.get_size()
            scale = min(work_width / pdf_width, work_height / pdf_height)
            bitmap = page.render(scale=scale)
            background = bitmap.to_pil().convert("RGBA")
        except Exception as exc:
            raise ValueError(f"无法渲染 PDF 缩略图第 {page_index + 1} 页：{exc}") from exc

        canvas = Image.new("RGBA", (work_width, work_height), "white")
        background.thumbnail((work_width, work_height), Image.Resampling.LANCZOS)
        canvas.alpha_composite(
            background,
            ((work_width - background.width) // 2, (work_height - background.height) // 2),
        )
        _base._add_strokes(canvas, strokes, page_width=page_width, page_height=page_height)
        for meta, data in images:
            _base._add_image(canvas, meta, data, page_width=page_width, page_height=page_height)
        _base._add_texts(canvas, texts, page_width=page_width, page_height=page_height)
        return _base._encode_thumbnail(canvas, (target_width, target_height))

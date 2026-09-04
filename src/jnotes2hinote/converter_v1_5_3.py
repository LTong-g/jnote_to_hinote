"""Jnotes2Hinote v1.5.3 conversion core.

This version keeps the v1.5.2 editable content and corrects landscape
thumbnail dimensions plus archive resource ordering.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from PIL import Image, JpegImagePlugin

from . import converter_v1_5_2 as _base
from .converter_v1_1_2 import gzip_json, sha256_hex, uuid32
from .jnotes_reader_v1_5_1 import JnotesContainerInfo, parse_jnotes_with_info
from .thumbnail_renderer_v1_5_3 import (
    THUMBNAIL_JPEG_SUBSAMPLING,
    THUMBNAIL_MAX_EDGE,
    PdfThumbnailRenderer,
    render_regular_thumbnail,
    thumbnail_dimensions,
)

JNote = _base.JNote
PdfAsset = _base.PdfAsset
PdfPageBinding = _base.PdfPageBinding
TESTED_HUAWEI_NOTES_VERSION = _base.TESTED_HUAWEI_NOTES_VERSION
TESTED_JNOTES_VERSION = _base.TESTED_JNOTES_VERSION
__version__ = "1.5.3"


def __getattr__(name: str) -> Any:
    return getattr(_base, name)


def parse_jnotes(path: Path) -> JNote:
    return parse_jnotes_with_info(path)[0]


def _hinote_page_geometry(page_width: float, page_height: float) -> tuple[float, int]:
    """Return native Hinote ratio/orientation metadata for physical dimensions."""
    if page_width <= 0 or page_height <= 0:
        raise ValueError("Hinote 页面尺寸必须为正数")
    if page_width > page_height:
        return page_height / page_width, 1
    return page_width / page_height, 0


def _archive_entry_order(
    entries: dict[str, bytes],
) -> tuple[list[str], list[str], list[str]]:
    """Order resources by Hinote references instead of random UUID names."""
    top_names = [
        name
        for name in entries
        if "/" not in name and name.endswith(".jhinote") and name != "custom_md.jhinote"
    ]
    page_objects: list[tuple[int, str, dict[str, Any]]] = []
    for name, payload in entries.items():
        if name.startswith("pages/") and name.endswith(".jhinote"):
            page_object = json.loads(gzip.decompress(payload))
            page_number = int(page_object["customNotePageContent"].get("pageNumber", 0))
            page_objects.append((page_number, name, page_object))
    page_objects.sort(key=lambda item: item[0])

    ordered_files: list[str] = []
    seen: set[str] = set()

    def add_file(filename: str) -> None:
        entry_name = f"files/{filename}"
        if entry_name in entries and entry_name not in seen:
            ordered_files.append(entry_name)
            seen.add(entry_name)

    for top_name in top_names:
        top_object = json.loads(gzip.decompress(entries[top_name]))
        for item in top_object.get("fileList", []):
            add_file(str(item.get("name", "")))
    for _, _, page_object in page_objects:
        for item in page_object.get("fileList", []):
            add_file(str(item.get("name", "")))
    for name in entries:
        if name.startswith("files/") and name not in seen:
            ordered_files.append(name)
            seen.add(name)

    return [item[1] for item in page_objects], ordered_files, top_names


def _rewrite_thumbnails(
    archive_path: Path,
    *,
    jn: JNote,
    pages_src: list[dict[str, Any]],
    assets: dict[str, PdfAsset],
    bindings: dict[str, PdfPageBinding],
) -> dict[str, int]:
    with zipfile.ZipFile(archive_path) as archive:
        entries = {name: archive.read(name) for name in archive.namelist()}

    page_entries: list[tuple[str, dict[str, Any]]] = []
    for name, payload in entries.items():
        if name.startswith("pages/") and name.endswith(".jhinote"):
            page_entries.append((name, json.loads(gzip.decompress(payload))))
    page_entries.sort(key=lambda item: int(item[1]["customNotePageContent"].get("pageNumber", 0)))
    if len(page_entries) != len(pages_src):
        raise ValueError("生成的 Hinote 页面数量与源笔记不一致")

    pdf_note = bool(bindings)
    regular_count = 0
    pdf_count = 0
    with PdfThumbnailRenderer() as pdf_renderer:
        for source_page, (entry_name, page_object) in zip(pages_src, page_entries):
            content = page_object["customNotePageContent"]
            source_page_id = str(source_page.get("a", ""))
            page_width, page_height, _ = _base._pdf_base._page_geometry(jn, source_page)
            page_ratio, page_orientation = _hinote_page_geometry(page_width, page_height)
            content["pageRatio"] = page_ratio
            content["pageOrientation"] = page_orientation
            strokes = list(jn.strokes.get(source_page_id, []))
            strokes.sort(key=lambda record: (int(record.get("b", 0)), int(record.get("e", 0))))
            binding = bindings.get(source_page_id)
            if binding:
                asset = assets[binding.asset_key]
                thumbnail = pdf_renderer.render(
                    asset_key=binding.asset_key,
                    payload=asset.payload,
                    page_index=binding.page_index,
                    page_width=page_width,
                    page_height=page_height,
                    strokes=strokes,
                    images=jn.images.get(source_page_id, []),
                    texts=jn.texts.get(source_page_id, []),
                )
                pdf_count += 1
            else:
                thumbnail = render_regular_thumbnail(
                    page_width=page_width,
                    page_height=page_height,
                    strokes=strokes,
                    images=jn.images.get(source_page_id, []),
                    texts=jn.texts.get(source_page_id, []),
                    cover=_base._base.find_cover_bytes(jn, source_page),
                )
                regular_count += 1
            old_name = _base._thumbnail_name(str(content.get("thumbnail", "")))
            if old_name:
                entries.pop(f"files/{old_name}", None)
            new_name = uuid32() + ".jpg"
            _base._update_page_thumbnail(
                page_object,
                thumbnail_name=new_name,
                thumbnail_bytes=thumbnail,
                old_thumbnail_name=old_name,
            )
            if pdf_note:
                content["cloudSyncState"] = 0
            entries[f"files/{new_name}"] = thumbnail
            entries[entry_name] = gzip_json(page_object)

    first_content = page_entries[0][1]["customNotePageContent"]
    for top_name in (
        name
        for name in entries
        if "/" not in name and name.endswith(".jhinote") and name != "custom_md.jhinote"
    ):
        top_object = json.loads(gzip.decompress(entries[top_name]))
        top_content = top_object["customNoteContent"]
        top_content["pageRatio"] = first_content["pageRatio"]
        top_content["pageOrientation"] = first_content["pageOrientation"]
        entries[top_name] = gzip_json(top_object)

    page_names, file_names, top_names = _archive_entry_order(entries)
    all_file_bytes = [(PurePosixPath(name).name, entries[name]) for name in file_names]
    entries["custom_md.jhinote"] = gzip_json({
        "customMdContents": [
            {
                "fileMdStr": sha256_hex(payload, True),
                "fileNameMdStr": sha256_hex(name.encode("utf-8"), False),
            }
            for name, payload in all_file_bytes
        ]
    })
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name in page_names:
            archive.writestr(name, entries[name])
        for name in file_names:
            archive.writestr(name, entries[name])
        for name in top_names:
            archive.writestr(name, entries[name])
        emitted = {*page_names, *file_names, *top_names, "custom_md.jhinote"}
        for name, payload in entries.items():
            if name not in emitted:
                archive.writestr(name, payload)
        archive.writestr("custom_md.jhinote", entries["custom_md.jhinote"])
    return {"generated": len(page_entries), "pdfRendered": pdf_count, "regularRendered": regular_count}


def _validate_thumbnails(archive_path: Path) -> None:
    with zipfile.ZipFile(archive_path) as archive:
        names = set(archive.namelist())
        custom_md = json.loads(gzip.decompress(archive.read("custom_md.jhinote")))
        md_hashes = {item.get("fileMdStr") for item in custom_md.get("customMdContents", [])}
        for entry_name in names:
            if not entry_name.startswith("pages/"):
                continue
            page_object = json.loads(gzip.decompress(archive.read(entry_name)))
            content = page_object["customNotePageContent"]
            name = _base._thumbnail_name(str(content.get("thumbnail", "")))
            if not name or f"files/{name}" not in names:
                raise ValueError(f"Hinote 页面缺少缩略图：{entry_name}")
            data = archive.read(f"files/{name}")
            image = Image.open(io.BytesIO(data))
            image.load()
            page_ratio = float(content["pageRatio"])
            page_orientation = int(content["pageOrientation"])
            if not 0 < page_ratio <= 1 or page_orientation not in (0, 1):
                raise ValueError(f"Hinote 页面方向元数据不正确：{entry_name}")
            expected_size = (
                thumbnail_dimensions(1.0, page_ratio)
                if page_orientation == 1
                else thumbnail_dimensions(page_ratio, 1.0)
            )
            if image.format != "JPEG" or image.size != expected_size or max(image.size) != THUMBNAIL_MAX_EDGE:
                raise ValueError(f"Hinote 缩略图规格不正确：{name}")
            if JpegImagePlugin.get_sampling(image) != THUMBNAIL_JPEG_SUBSAMPLING:
                raise ValueError(f"Hinote 缩略图采样方式不正确：{name}")
            if any(value != 1 for table in image.quantization.values() for value in table):
                raise ValueError(f"Hinote 缩略图 JPEG 质量不正确：{name}")
            digest = hashlib.sha256(data).hexdigest().upper()
            if digest not in md_hashes:
                raise ValueError(f"Hinote 缩略图未写入 custom_md：{name}")
            if not any(
                item.get("name") == name and item.get("hash") == digest
                for item in page_object.get("fileList", [])
            ):
                raise ValueError(f"Hinote 缩略图 fileList 哈希不正确：{name}")
            data1 = json.loads(content.get("data1", "{}"))
            detail_map = json.loads(data1.get("detailFileMap", "{}"))
            if detail_map.get(name) != [_base.file_info(name, data)]:
                raise ValueError(f"Hinote 缩略图 detailFileMap 哈希不正确：{name}")


def convert(jnotes_path: Path, output: Path, page_limit: int | None = None) -> dict[str, Any]:
    """Convert a Jnotes file using orientation-safe native-quality thumbnails."""
    jn, _ = parse_jnotes_with_info(jnotes_path)
    pages_src = jn.pages[:page_limit] if page_limit else jn.pages
    if not pages_src:
        raise ValueError("源笔记没有页面")
    assets, bindings, _ = _base._pdf_base._resolve_pdf_pages(jn, pages_src)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.{uuid32()}.tmp")
    try:
        result = _base._base.convert(jnotes_path, temporary, page_limit=page_limit)
        thumbnail_stats = _rewrite_thumbnails(
            temporary,
            jn=jn,
            pages_src=pages_src,
            assets=assets,
            bindings=bindings,
        )
        _validate_thumbnails(temporary)
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    result["converterVersion"] = __version__
    result["output"] = str(output)
    result["outputBytes"] = output.stat().st_size
    first_width, first_height, _ = _base._pdf_base._page_geometry(jn, pages_src[0])
    result["pageRatio"], result["pageOrientation"] = _hinote_page_geometry(first_width, first_height)
    for source_page, page_stats in zip(pages_src, result.get("pageStats", [])):
        page_width, page_height, _ = _base._pdf_base._page_geometry(jn, source_page)
        page_stats["pageRatio"], page_stats["pageOrientation"] = _hinote_page_geometry(
            page_width,
            page_height,
        )
    result["thumbnailStats"] = {
        **thumbnail_stats,
        "maxEdge": THUMBNAIL_MAX_EDGE,
        "jpegQuality": 100,
    }
    return result


__all__ = [
    "TESTED_HUAWEI_NOTES_VERSION",
    "TESTED_JNOTES_VERSION",
    "JNote",
    "JnotesContainerInfo",
    "PdfAsset",
    "PdfPageBinding",
    "__version__",
    "convert",
    "parse_jnotes",
    "parse_jnotes_with_info",
]

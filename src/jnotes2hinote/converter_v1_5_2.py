"""Jnotes2Hinote v1.5.2 conversion core.

This version keeps the v1.5.1 editable Hinote conversion intact and replaces
its generated page previews with native-quality, per-page thumbnails.
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

from . import converter_v1_2_0 as _pdf_base
from . import converter_v1_5_1 as _base
from .converter_v1_1_2 import file_info, gzip_json, sha256_hex, uuid32
from .jnotes_reader_v1_5_1 import JnotesContainerInfo, parse_jnotes_with_info
from .thumbnail_renderer_v1_5_2 import (
    THUMBNAIL_HEIGHT,
    THUMBNAIL_JPEG_SUBSAMPLING,
    PdfThumbnailRenderer,
    render_regular_thumbnail,
    thumbnail_dimensions,
)

JNote = _base.JNote
PdfAsset = _pdf_base.PdfAsset
PdfPageBinding = _pdf_base.PdfPageBinding
TESTED_HUAWEI_NOTES_VERSION = _base.TESTED_HUAWEI_NOTES_VERSION
TESTED_JNOTES_VERSION = _base.TESTED_JNOTES_VERSION
__version__ = "1.5.2"


def __getattr__(name: str) -> Any:
    return getattr(_base, name)


def parse_jnotes(path: Path) -> JNote:
    return parse_jnotes_with_info(path)[0]


def _thumbnail_name(value: str) -> str:
    return PurePosixPath(value).name if value else ""


def _update_page_thumbnail(
    page_object: dict[str, Any],
    *,
    thumbnail_name: str,
    thumbnail_bytes: bytes,
    old_thumbnail_name: str,
) -> None:
    content = page_object["customNotePageContent"]
    content["thumbnail"] = f"/data/user/0/com.huawei.hinote/files/thumbnail/{thumbnail_name}"
    old_names = {old_thumbnail_name} if old_thumbnail_name else set()
    page_object["fileList"] = [
        item for item in page_object.get("fileList", []) if item.get("name") not in old_names
    ]
    page_object["fileList"].append(file_info(thumbnail_name, thumbnail_bytes))
    data1 = json.loads(content.get("data1", "{}"))
    detail_map = json.loads(data1.get("detailFileMap", "{}"))
    for old_name in old_names:
        detail_map.pop(old_name, None)
    detail_map[thumbnail_name] = [file_info(thumbnail_name, thumbnail_bytes)]
    data1["detailFileMap"] = json.dumps(detail_map, ensure_ascii=False, separators=(",", ":"))
    data1.setdefault("thumbnail_area", "")
    data1.setdefault("book_mark", "")
    content["data1"] = json.dumps(data1, ensure_ascii=False, separators=(",", ":"))


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
            page_width, page_height, _ = _pdf_base._page_geometry(jn, source_page)
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
                    cover=_base.find_cover_bytes(jn, source_page),
                )
                regular_count += 1
            old_name = _thumbnail_name(str(content.get("thumbnail", "")))
            if old_name:
                entries.pop(f"files/{old_name}", None)
            new_name = uuid32() + ".jpg"
            _update_page_thumbnail(
                page_object,
                thumbnail_name=new_name,
                thumbnail_bytes=thumbnail,
                old_thumbnail_name=old_name,
            )
            if pdf_note:
                content["cloudSyncState"] = 0
            entries[f"files/{new_name}"] = thumbnail
            entries[entry_name] = gzip_json(page_object)

    all_file_bytes = {
        PurePosixPath(name).name: payload
        for name, payload in entries.items()
        if name.startswith("files/")
    }
    entries["custom_md.jhinote"] = gzip_json({
        "customMdContents": [
            {
                "fileMdStr": sha256_hex(payload, True),
                "fileNameMdStr": sha256_hex(name.encode("utf-8"), False),
            }
            for name, payload in all_file_bytes.items()
        ]
    })
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name in sorted(item for item in entries if item.startswith("pages/")):
            archive.writestr(name, entries[name])
        for name in sorted(item for item in entries if item.startswith("files/")):
            archive.writestr(name, entries[name])
        for name in sorted(item for item in entries if not item.startswith(("pages/", "files/")) and item != "custom_md.jhinote"):
            archive.writestr(name, entries[name])
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
            name = _thumbnail_name(str(content.get("thumbnail", "")))
            if not name or f"files/{name}" not in names:
                raise ValueError(f"Hinote 页面缺少缩略图：{entry_name}")
            data = archive.read(f"files/{name}")
            image = Image.open(io.BytesIO(data))
            image.load()
            expected_size = thumbnail_dimensions(
                float(content["pageRatio"]),
                1.0,
            )
            if image.format != "JPEG" or image.size != expected_size:
                raise ValueError(f"Hinote 缩略图规格不正确：{name}")
            if JpegImagePlugin.get_sampling(image) != THUMBNAIL_JPEG_SUBSAMPLING:
                raise ValueError(f"Hinote 缩略图采样方式不正确：{name}")
            if any(value != 1 for table in image.quantization.values() for value in table):
                raise ValueError(f"Hinote 缩略图 JPEG 质量不正确：{name}")
            digest = hashlib.sha256(data).hexdigest().upper()
            if digest not in md_hashes:
                raise ValueError(f"Hinote 缩略图未写入 custom_md：{name}")
            if not any(item.get("name") == name and item.get("hash") == digest for item in page_object.get("fileList", [])):
                raise ValueError(f"Hinote 缩略图 fileList 哈希不正确：{name}")
            data1 = json.loads(content.get("data1", "{}"))
            detail_map = json.loads(data1.get("detailFileMap", "{}"))
            if detail_map.get(name) != [file_info(name, data)]:
                raise ValueError(f"Hinote 缩略图 detailFileMap 哈希不正确：{name}")


def convert(jnotes_path: Path, output: Path, page_limit: int | None = None) -> dict[str, Any]:
    """Convert a Jnotes file and regenerate native-quality page previews."""
    jn, _ = parse_jnotes_with_info(jnotes_path)
    pages_src = jn.pages[:page_limit] if page_limit else jn.pages
    if not pages_src:
        raise ValueError("源笔记没有页面")
    assets, bindings, _ = _pdf_base._resolve_pdf_pages(jn, pages_src)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.{uuid32()}.tmp")
    try:
        result = _base.convert(jnotes_path, temporary, page_limit=page_limit)
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
    result["thumbnailStats"] = {**thumbnail_stats, "height": THUMBNAIL_HEIGHT, "jpegQuality": 100}
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

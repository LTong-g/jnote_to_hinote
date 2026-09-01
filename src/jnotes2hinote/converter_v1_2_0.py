#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Jnotes2Hinote v1.2.0 转换核心。

v1.2.0 增加 Jnotes PDF 笔记的原生转换：完整保留源 PDF，并在 Hinote
页面中通过 bkgAttachmentId/bkgAttachmentIndex 引用 PDF 页面。PDF 不会被
栅格化为正文图片；Jnotes 的 COVER 缩略图也只用于页面预览。

v1.1.2 及更早核心保持不变。本模块复用 v1.1.2 已验证的笔迹、图片、文本
和 PENCILENGINE 构建逻辑，只新增 PDF 附件和页面背景引用。
"""
from __future__ import annotations

import hashlib
import io
import json
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image

from . import converter_v1_1_2 as _base
from .converter_v1_1_2 import *  # noqa: F401,F403

__version__ = "1.2.0"


@dataclass(frozen=True)
class PdfAsset:
    """A source PDF record and its validated page count."""

    key: str
    object_id: str
    payload: bytes
    page_count: int


@dataclass(frozen=True)
class PdfPageBinding:
    """The PDF attachment and zero-based page index used by one Jnotes page."""

    asset_key: str
    page_index: int


def __getattr__(name: str) -> Any:
    """Keep private helper compatibility while leaving historical cores untouched."""
    return getattr(_base, name)


def _basename(value: str) -> str:
    return str(value).replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]


def _pdf_page_count(payload: bytes) -> int:
    """Validate a PDF and return its page count without rendering it."""
    if not payload.startswith(b"%PDF-"):
        raise ValueError("Jnotes PDF 记录不是合法 PDF：缺少 %PDF- 文件头")

    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader
        except ImportError as exc:  # pragma: no cover - packaging/install error
            raise RuntimeError("PDF 转换需要 pypdf 或 PyPDF2，请先安装项目依赖") from exc

    try:
        reader = PdfReader(BytesIO(payload), strict=False)
        if reader.is_encrypted:
            raise ValueError("暂不支持加密 PDF")
        count = len(reader.pages)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"无法读取 Jnotes 中的 PDF：{exc}") from exc
    if count <= 0:
        raise ValueError("Jnotes 中的 PDF 没有页面")
    return count


def _resolve_pdf_pages(
    jn: JNote,
    pages: list[dict[str, Any]],
) -> tuple[dict[str, PdfAsset], dict[str, PdfPageBinding], dict[str, Any]]:
    """Resolve PAGE.e/PAGE.c references to PDF records before writing anything."""
    pdf_records = [record for record in jn.records if record.typ == "PDF"]
    records_by_key: dict[str, Any] = {}
    for record in pdf_records:
        key = _basename(record.object_id).casefold()
        if not key:
            raise ValueError("Jnotes PDF 记录缺少文件名")
        if key in records_by_key:
            raise ValueError(f"Jnotes 中存在重复的 PDF 文件名：{_basename(record.object_id)}")
        records_by_key[key] = record

    referenced_keys = {
        _basename(str(page.get("e", ""))) .casefold()
        for page in pages
        if str(page.get("e", "")).strip()
    }
    if not referenced_keys:
        return {}, {}, {
            "sourcePdfRecords": len(pdf_records),
            "referencedPdfRecords": 0,
            "embeddedPdfFiles": 0,
            "pdfBackedPages": 0,
            "unresolvedPdfPages": 0,
            "pdfBytes": 0,
            "sourcePdfSha256": {},
        }

    assets: dict[str, PdfAsset] = {}
    for key in sorted(referenced_keys):
        record = records_by_key.get(key)
        if record is None:
            raise ValueError(f"PAGE 引用了不存在的 PDF 记录：{key}")
        assets[key] = PdfAsset(
            key=key,
            object_id=str(record.object_id),
            payload=bytes(record.payload),
            page_count=_pdf_page_count(record.payload),
        )

    bindings: dict[str, PdfPageBinding] = {}
    unresolved = 0
    for page in pages:
        source_page_id = str(page.get("a", ""))
        source_pdf = str(page.get("e", "")).strip()
        if not source_pdf:
            continue
        key = _basename(source_pdf).casefold()
        asset = assets[key]
        raw_index = page.get("c")
        try:
            page_index = int(raw_index)
        except (TypeError, ValueError) as exc:
            unresolved += 1
            raise ValueError(f"PDF 页面索引无效：{raw_index!r}") from exc
        if page_index < 0 or page_index >= asset.page_count:
            unresolved += 1
            raise ValueError(
                f"PDF 页面索引越界：{_basename(source_pdf)}[{page_index}]，"
                f"实际页数为 {asset.page_count}"
            )
        if not source_page_id:
            unresolved += 1
            raise ValueError("PDF 页面缺少 Jnotes 页面 ID")
        bindings[source_page_id] = PdfPageBinding(key, page_index)

    pdf_stats = {
        "sourcePdfRecords": len(pdf_records),
        "referencedPdfRecords": len(assets),
        "embeddedPdfFiles": len(assets),
        "pdfBackedPages": len(bindings),
        "unresolvedPdfPages": unresolved,
        "pdfBytes": sum(len(asset.payload) for asset in assets.values()),
        "sourcePdfSha256": {
            asset.key: hashlib.sha256(asset.payload).hexdigest() for asset in assets.values()
        },
    }
    return assets, bindings, pdf_stats


def _page_geometry(jn: JNote, page: dict[str, Any]) -> tuple[float, float, float]:
    """Use PAGE.k/l when present so PDF pages with different ratios stay correct."""
    try:
        width = float(page.get("k", jn.width) or jn.width)
        height = float(page.get("l", jn.height) or jn.height)
    except (TypeError, ValueError) as exc:
        raise ValueError("Jnotes 页面尺寸无效") from exc
    if width <= 0 or height <= 0:
        raise ValueError("Jnotes 页面尺寸必须为正数")
    return width, height, width / height


def _first_cover(jn: JNote) -> bytes | None:
    """Return the source cover preview for PDF page 1, if it is an image."""
    for name, data in jn.covers.items():
        if name.casefold().startswith(jn.note_uuid.casefold()) and (
            data.startswith(b"\xff\xd8\xff") or data.startswith(b"\x89PNG")
        ):
            return data
    for data in jn.covers.values():
        if data.startswith(b"\xff\xd8\xff") or data.startswith(b"\x89PNG"):
            return data
    return None


def _thumbnail_jpeg(data: bytes) -> bytes:
    """Normalize a source cover to a preview JPEG; this is never page content."""
    try:
        image = Image.open(BytesIO(data)).convert("RGB")
    except Exception as exc:
        raise ValueError(f"无法读取 Jnotes 封面缩略图：{exc}") from exc
    output = BytesIO()
    image.save(output, "JPEG", quality=90, optimize=True)
    return output.getvalue()


def _write_archive(path: Path, entries: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name in sorted(key for key in entries if key.startswith("pages/")):
            archive.writestr(name, entries[name])
        for name in sorted(key for key in entries if key.startswith("files/")):
            archive.writestr(name, entries[name])
        top_names = [
            key for key in entries
            if key.endswith(".jhinote") and "/" not in key and key != "custom_md.jhinote"
        ]
        for name in sorted(top_names):
            archive.writestr(name, entries[name])
        archive.writestr("custom_md.jhinote", entries["custom_md.jhinote"])


def _validate_pdf_archive(
    path: Path,
    *,
    source_pages: list[dict[str, Any]],
    assets: dict[str, PdfAsset],
    bindings: dict[str, PdfPageBinding],
    attachment_ids: dict[str, str],
    output_names: dict[str, str],
) -> None:
    """Check the emitted PDF references and byte identity before publishing output."""
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        top_names = [
            name for name in names
            if name.endswith(".jhinote") and "/" not in name and name != "custom_md.jhinote"
        ]
        if len(top_names) != 1:
            raise ValueError("生成的 Hinote 缺少唯一顶层笔记文件")
        top = json.loads(gzip.decompress(archive.read(top_names[0])))
        content = top["customNoteContent"]
        top_attachments = {str(item["id"]): item for item in content.get("attachment", [])}

        for key, asset in assets.items():
            filename = output_names[key]
            if f"files/{filename}" not in names:
                raise ValueError(f"生成的 Hinote 缺少 PDF 文件：{filename}")
            if archive.read(f"files/{filename}") != asset.payload:
                raise ValueError(f"生成的 Hinote 中 PDF 字节不一致：{filename}")
            attachment = top_attachments.get(attachment_ids[key])
            if attachment is None or attachment.get("attachType") != 3:
                raise ValueError(f"生成的 Hinote 缺少 PDF 附件：{filename}")
            if _basename(str(attachment.get("filePath", ""))) != filename:
                raise ValueError(f"PDF 附件路径不正确：{filename}")

        pages: list[dict[str, Any]] = []
        for name in names:
            if not name.startswith("pages/"):
                continue
            page_obj = json.loads(gzip.decompress(archive.read(name)))
            pages.append(page_obj["customNotePageContent"])
        pages.sort(key=lambda page: int(page.get("pageNumber", 0)))
        if len(pages) != len(source_pages):
            raise ValueError("生成的 Hinote 页面数量与源笔记不一致")

        for source_page, output_page in zip(source_pages, pages):
            source_id = str(source_page.get("a", ""))
            binding = bindings.get(source_id)
            if binding is None:
                continue
            expected_attachment = attachment_ids[binding.asset_key]
            if output_page.get("bkgAttachmentId") != expected_attachment:
                raise ValueError("Hinote 页面 PDF 附件引用不一致")
            if int(output_page.get("bkgAttachmentIndex", -1)) != binding.page_index:
                raise ValueError("Hinote 页面 PDF 索引不一致")

        custom_md = json.loads(gzip.decompress(archive.read("custom_md.jhinote")))
        md_hashes = {str(item.get("fileMdStr", "")) for item in custom_md.get("customMdContents", [])}
        for key, asset in assets.items():
            if hashlib.sha256(asset.payload).hexdigest().upper() not in md_hashes:
                raise ValueError("PDF 文件未写入 custom_md.jhinote")


def convert(
    jnotes_path: Path,
    output: Path,
    page_limit: int | None = None,
) -> dict[str, Any]:
    """Convert Jnotes, preserving PDF-backed pages as native Hinote PDF pages."""
    jn = parse_jnotes(jnotes_path)
    pages_src = jn.pages[:page_limit] if page_limit else jn.pages
    if not pages_src:
        raise ValueError("源笔记没有页面")

    assets, bindings, pdf_stats = _resolve_pdf_pages(jn, pages_src)
    if not bindings:
        result = _base.convert(jnotes_path, output, page_limit=page_limit)
        result["converterVersion"] = __version__
        result["pdfStats"] = pdf_stats
        return result

    note_id = uuid32()
    ts = now_ms()
    note_ratio = _page_geometry(jn, pages_src[0])[2]
    all_zip: dict[str, bytes] = {}
    all_file_bytes: dict[str, bytes] = {}
    page_results: list[dict[str, Any]] = []
    total_stats = defaultdict(int)

    pdf_filenames: dict[str, str] = {}
    pdf_attachment_ids: dict[str, str] = {}
    top_attachments: list[dict[str, Any]] = []
    for key, asset in assets.items():
        filename = f"{uuid32()}_pdf"
        attachment_id = uuid32()
        pdf_filenames[key] = filename
        pdf_attachment_ids[key] = attachment_id
        all_zip[f"files/{filename}"] = asset.payload
        all_file_bytes[filename] = asset.payload
        top_attachments.append({
            "attachType": 3,
            "cloudSyncState": 1,
            "createTime": ts,
            "filePath": f"/data/user/0/com.huawei.hinote/files/importfiles/{filename}",
            "isDelete": 0,
            "modifiedTime": ts,
            "notesId": note_id,
            "playbackProgress": 0,
            "id": attachment_id,
            "notePageId": None,
            "data1": '{"synDataTpye":"memonote","pageElementId":""}',
            "data2": "",
            "data3": "",
            "data4": "",
            "data5": "",
            "unStructUuid": "",
            "transText": None,
            "contentText": "",
        })

    cover = _first_cover(jn)
    for page_idx, page in enumerate(pages_src, start=1):
        old_pid = str(page.get("a"))
        page_id = uuid32()
        page_files: dict[str, bytes] = {}
        page_attachments: list[dict[str, Any]] = []
        elements: list[dict[str, Any]] = []
        page_width, page_height, page_ratio = _page_geometry(jn, page)
        binding = bindings.get(old_pid)
        is_pdf_page = binding is not None
        zpos = 1

        if not is_pdf_page:
            page_cover = find_cover_bytes(jn, page)
            if page_cover:
                filename = uuid32() + image_ext(page_cover)
                page_files[filename] = page_cover
                elements.append(make_image_element(
                    {"x": 0, "y": 0, "c": page_width, "d": page_height, "e": 0},
                    page_id,
                    page_width,
                    page_height,
                    0,
                    ts,
                    filename,
                ))

        for meta, data in jn.images.get(old_pid, []):
            if not data:
                continue
            filename = uuid32() + image_ext(data)
            page_files[filename] = data
            elements.append(make_image_element(meta, page_id, page_width, page_height, zpos, ts, filename))
            zpos += 1

        for text in jn.texts.get(old_pid, []):
            elements.append(make_text_element(text, page_id, page_width, page_height, zpos, ts))
            zpos += 1

        page_strokes = list(jn.strokes.get(old_pid, []))
        page_strokes.sort(key=lambda record: (int(record.get("b", 0)), int(record.get("e", 0))))
        convertible = [record for record in page_strokes if int(record.get("c", {}).get("a", -1)) != 10]
        bin_size = 0
        pstats = {
            "normal": 0,
            "geometry": 0,
            "geometryFallback": 0,
            "paperTapeSkipped": len(page_strokes) - len(convertible),
        }
        if convertible:
            bin_name = uuid32() + ".bin"
            bin_data, pstats = build_pencilengine(page_strokes, 1000.0 / page_width)
            page_files[bin_name] = bin_data
            bin_size = len(bin_data)
            page_attachments.append({
                "attachType": 0,
                "cloudSyncState": 1,
                "createTime": ts,
                "filePath": f"/data/user/0/com.huawei.hinote/files/hwFile/{bin_name}",
                "isDelete": 0,
                "modifiedTime": ts,
                "notesId": note_id,
                "playbackProgress": 0,
                "id": uuid32(),
                "notePageId": page_id,
                "data1": '{"pageElementId":""}',
                "data2": "",
                "data3": "",
                "data4": "",
                "data5": "",
                "unStructUuid": "",
                "transText": None,
                "contentText": "",
            })
        for key, value in pstats.items():
            total_stats[key] += value

        thumbnail_name = ""
        if is_pdf_page:
            if page_idx == 1 and cover:
                thumbnail_name = uuid32() + ".jpg"
                page_files[thumbnail_name] = _thumbnail_jpeg(cover)
        else:
            thumbnail_name = uuid32() + ".jpg"
            page_files[thumbnail_name] = render_thumbnail(
                jn,
                page,
                page_strokes,
                jn.images.get(old_pid, []),
                jn.texts.get(old_pid, []),
                find_cover_bytes(jn, page),
            )

        file_list = [file_info(name, data) for name, data in page_files.items()]
        page_map = detail_map(page_files)
        page_obj = {
            "customNotePageContent": {
                "pageBookMarks": [],
                "attachment": page_attachments,
                "background": "base1" if is_pdf_page else background_for_page(page),
                "bkgAttachmentId": pdf_attachment_ids[binding.asset_key] if binding else "",
                "bkgAttachmentIndex": binding.page_index if binding else 0,
                "chapterNumber": "",
                "cloudSyncState": 0 if is_pdf_page else 1,
                "createTime": ts,
                "guid": "",
                "id": page_id,
                "isDelete": 0,
                "lastPageTag": 1 if page_idx == len(pages_src) else 0,
                "modifiedTime": ts,
                "notesId": note_id,
                "pageColor": -1,
                "pageElement": elements,
                "pageNumber": page_idx,
                "pageOrientation": 0,
                "pageRatio": page_ratio,
                "pageType": 1,
                "thumbnail": (
                    f"/data/user/0/com.huawei.hinote/files/thumbnail/{thumbnail_name}"
                    if thumbnail_name
                    else ""
                ),
                "unStructUuid": "",
                "data1": json.dumps(
                    {"detailFileMap": page_map, "thumbnail_area": "", "book_mark": ""},
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                "data2": "",
                "data3": "",
                "data4": "",
                "data5": "",
            },
            "fileList": file_list,
        }
        all_zip[f"pages/{page_id}.jhinote"] = gzip_json(page_obj)
        for filename, data in page_files.items():
            all_zip[f"files/{filename}"] = data
            all_file_bytes[filename] = data

        page_results.append({
            "page": page_idx,
            "sourcePageId": old_pid,
            "background": "base1" if is_pdf_page else background_for_page(page),
            "pdfBacked": is_pdf_page,
            "pdfAttachmentId": pdf_attachment_ids[binding.asset_key] if binding else "",
            "pdfPageIndex": binding.page_index if binding else None,
            "sourceStrokeRecords": len(page_strokes),
            "convertedInk": len(convertible),
            "paperTapeSkipped": pstats["paperTapeSkipped"],
            "images": len(jn.images.get(old_pid, [])),
            "texts": len(jn.texts.get(old_pid, [])),
            "elements": len(elements),
            "binBytes": bin_size,
            "pageRatio": page_ratio,
        })

    outline_name = f"{note_id}_{ts}_outline.json"
    outline_data = note_id.encode("ascii")
    all_zip[f"files/{outline_name}"] = outline_data
    all_file_bytes[outline_name] = outline_data

    top_names = list(pdf_filenames.values()) + [outline_name]
    top_detail = {
        name: [file_info(name, all_file_bytes[name])] for name in top_names
    }
    top = {
        "customNoteContent": {
            "attachment": top_attachments,
            "background": "base1",
            "categoryId": "system_category_uuid_unclassified",
            "cloudSyncState": 0,
            "createTime": ts,
            "data1": json.dumps({
                "relationTags": "[]",
                "relationPages": "",
                "originDeviceType": "tablet",
                "isContentCover": "1",
                "isInfNote": "0",
                "infStylusPath": "",
                "detailFileMap": json.dumps(top_detail, separators=(",", ":")),
                "record_item_mapper_key": "",
                "localData1": "",
            }, ensure_ascii=False, separators=(",", ":")),
            "deleteTag": 0,
            "deleteTime": 0,
            "extendFields": "hinote_1.0.5",
            "guid": "",
            "hasCover": 0,
            "id": note_id,
            "isFavorite": 0,
            "isTop": 0,
            "modifiedTime": ts,
            "noteIcon": "import_pdf",
            "noteTitle": jn.title,
            "noteType": 101,
            "pageColor": -1,
            "pageOrientation": 0,
            "pageRatio": note_ratio,
            "unStructUuid": "",
            "bookIntroduction": "",
            "userId": "",
            "noteTemplate": "",
            "data2": "",
            "data3": "",
            "data4": "",
            "data5": "",
            "coverId": "",
            "parentId": "system_category_uuid_unclassified",
            "outLineAttachment": [],
            "recordItemEntities": [],
        },
        "fileList": [file_info(name, all_file_bytes[name]) for name in top_names],
    }
    all_zip[f"{note_id}.jhinote"] = gzip_json(top)

    all_zip["custom_md.jhinote"] = gzip_json({
        "customMdContents": [
            {
                "fileMdStr": sha256_hex(data, True),
                "fileNameMdStr": sha256_hex(name.encode("utf-8"), False),
            }
            for name, data in all_file_bytes.items()
        ]
    })

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.{uuid32()}.tmp")
    try:
        _write_archive(temporary, all_zip)
        _validate_pdf_archive(
            temporary,
            source_pages=pages_src,
            assets=assets,
            bindings=bindings,
            attachment_ids=pdf_attachment_ids,
            output_names=pdf_filenames,
        )
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)

    pdf_stats["outputPdfSha256"] = {
        key: hashlib.sha256(all_zip[f"files/{pdf_filenames[key]}"]).hexdigest()
        for key in assets
    }
    return {
        "converterVersion": __version__,
        "referenceHinoteRequired": False,
        "testedVersions": {
            "jnotes": TESTED_JNOTES_VERSION,
            "huaweiNotes": TESTED_HUAWEI_NOTES_VERSION,
        },
        "source": str(jnotes_path),
        "output": str(output),
        "title": jn.title,
        "pages": len(pages_src),
        "pageRatio": note_ratio,
        "sourceRecords": len(jn.records),
        "audioRecordsDetectedButNotConverted": len(jn.audio_records),
        "strokeStats": dict(total_stats),
        "pdfStats": pdf_stats,
        "pageStats": page_results,
        "outputBytes": output.stat().st_size,
    }

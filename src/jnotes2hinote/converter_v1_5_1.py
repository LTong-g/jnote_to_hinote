#!/usr/bin/env python3
"""Jnotes2Hinote v1.5.1 conversion core.

v1.5.1 keeps the v1.2.0 Hinote output and native-PDF behavior, and adds
compatibility with Jnotes exports whose outer ZIP data member is named
``zip.Jnotes``.  The previously supported ``zip.Jzip`` member remains
supported.  Historical converter modules are intentionally not modified.
"""
from __future__ import annotations

import hashlib
import json
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any

from . import converter_v1_2_0 as _pdf_base
from .converter_v1_1_2 import (
    TESTED_HUAWEI_NOTES_VERSION,
    TESTED_JNOTES_VERSION,
    JNote,
    background_for_page,
    build_pencilengine,
    detail_map,
    file_info,
    find_cover_bytes,
    gzip_json,
    image_ext,
    make_image_element,
    make_text_element,
    now_ms,
    render_thumbnail,
    sha256_hex,
    uuid32,
)
from .jnotes_reader_v1_5_1 import JnotesContainerInfo, parse_jnotes_with_info

PdfAsset = _pdf_base.PdfAsset
PdfPageBinding = _pdf_base.PdfPageBinding

__version__ = "1.5.1"


def __getattr__(name: str) -> Any:
    """Keep access to the v1.2.0 private PDF helpers for compatibility."""
    return getattr(_pdf_base, name)


def parse_jnotes(path: Path) -> JNote:
    """Parse a Jnotes file supporting both known outer data-member names."""
    return parse_jnotes_with_info(path)[0]


def _container_report(info: JnotesContainerInfo) -> dict[str, Any]:
    return {
        "entry": info.entry_name,
        "streamVersion": info.stream_version,
        "streamBytes": info.stream_size,
        "outerEntryCount": info.outer_entry_count,
        "footerRecognized": info.footer_recognized,
    }


def _result_metadata(
    jnotes_path: Path,
    output: Path,
    jn: JNote,
    pages_src: list[dict[str, Any]],
    ratio: float,
    total_stats: dict[str, int],
    page_results: list[dict[str, Any]],
    source_info: JnotesContainerInfo,
    *,
    pdf_stats: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "converterVersion": __version__,
        "referenceHinoteRequired": False,
        "testedVersions": {
            "jnotes": TESTED_JNOTES_VERSION,
            "huaweiNotes": TESTED_HUAWEI_NOTES_VERSION,
        },
        "source": str(jnotes_path),
        "sourceContainer": _container_report(source_info),
        "output": str(output),
        "title": jn.title,
        "pages": len(pages_src),
        "pageRatio": ratio,
        "sourceRecords": len(jn.records),
        "audioRecordsDetectedButNotConverted": len(jn.audio_records),
        "strokeStats": dict(total_stats),
        "pageStats": page_results,
        "outputBytes": output.stat().st_size,
    }
    if pdf_stats is not None:
        result["pdfStats"] = pdf_stats
    return result


def _convert_regular(
    jnotes_path: Path,
    output: Path,
    jn: JNote,
    pages_src: list[dict[str, Any]],
    source_info: JnotesContainerInfo,
    pdf_stats: dict[str, Any],
) -> dict[str, Any]:
    """Convert a parsed non-PDF-backed note without reopening its source ZIP."""
    note_id = uuid32()
    ts = now_ms()
    ratio = jn.width / jn.height
    sx = 1000.0 / jn.width
    all_zip: dict[str, bytes] = {}
    all_file_bytes: dict[str, bytes] = {}
    page_results: list[dict[str, Any]] = []
    total_stats = defaultdict(int)

    for page_idx, page in enumerate(pages_src, start=1):
        old_pid = str(page.get("a"))
        page_id = uuid32()
        page_files: dict[str, bytes] = {}
        attachments: list[dict[str, Any]] = []
        elements: list[dict[str, Any]] = []
        zpos = 1

        cover = find_cover_bytes(jn, page)
        if cover:
            ext = image_ext(cover)
            filename = uuid32() + ext
            page_files[filename] = cover
            elements.append(make_image_element(
                {"x": 0, "y": 0, "c": jn.width, "d": jn.height, "e": 0},
                page_id, jn.width, jn.height, 0, ts, filename,
            ))

        for meta, data in jn.images.get(old_pid, []):
            if not data:
                continue
            filename = uuid32() + image_ext(data)
            page_files[filename] = data
            elements.append(make_image_element(meta, page_id, jn.width, jn.height, zpos, ts, filename))
            zpos += 1

        for text in jn.texts.get(old_pid, []):
            elements.append(make_text_element(text, page_id, jn.width, jn.height, zpos, ts))
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
            bin_data, pstats = build_pencilengine(page_strokes, sx)
            page_files[bin_name] = bin_data
            bin_size = len(bin_data)
            attachments.append({
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

        thumbnail_name = uuid32() + ".jpg"
        page_files[thumbnail_name] = render_thumbnail(
            jn, page, page_strokes, jn.images.get(old_pid, []), jn.texts.get(old_pid, []), cover,
        )
        page_obj = {
            "customNotePageContent": {
                "pageBookMarks": [],
                "attachment": attachments,
                "background": background_for_page(page),
                "bkgAttachmentId": "",
                "bkgAttachmentIndex": 0,
                "chapterNumber": "",
                "cloudSyncState": 1,
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
                "pageRatio": ratio,
                "pageType": 1,
                "thumbnail": f"/data/user/0/com.huawei.hinote/files/thumbnail/{thumbnail_name}",
                "unStructUuid": "",
                "data1": json.dumps(
                    {"detailFileMap": detail_map(page_files), "thumbnail_area": "", "book_mark": ""},
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                "data2": "",
                "data3": "",
                "data4": "",
                "data5": "",
            },
            "fileList": [file_info(name, data) for name, data in page_files.items()],
        }
        all_zip[f"pages/{page_id}.jhinote"] = gzip_json(page_obj)
        for filename, data in page_files.items():
            all_zip[f"files/{filename}"] = data
            all_file_bytes[filename] = data

        page_results.append({
            "page": page_idx,
            "sourcePageId": old_pid,
            "background": background_for_page(page),
            "sourceStrokeRecords": len(page_strokes),
            "convertedInk": len(convertible),
            "paperTapeSkipped": pstats["paperTapeSkipped"],
            "images": len(jn.images.get(old_pid, [])),
            "texts": len(jn.texts.get(old_pid, [])),
            "elements": len(elements),
            "binBytes": bin_size,
        })

    outline_name = f"{note_id}_{ts}_outline.json"
    outline_data = note_id.encode("ascii")
    all_zip[f"files/{outline_name}"] = outline_data
    all_file_bytes[outline_name] = outline_data
    outline_hash = sha256_hex(outline_data, True)
    top_detail = {outline_name: [{"name": outline_name, "hash": outline_hash}]}
    top = {
        "customNoteContent": {
            "attachment": [],
            "background": background_for_page(pages_src[0]),
            "categoryId": "system_category_uuid_unclassified",
            "cloudSyncState": 1,
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
            "hasCover": 1,
            "id": note_id,
            "isFavorite": 0,
            "isTop": 0,
            "modifiedTime": ts,
            "noteIcon": "base_7",
            "noteTitle": jn.title,
            "noteType": 100,
            "pageColor": -1,
            "pageOrientation": 0,
            "pageRatio": ratio,
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
        "fileList": [{"name": outline_name, "hash": outline_hash}],
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
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name in sorted(key for key in all_zip if key.startswith("pages/")):
            archive.writestr(name, all_zip[name])
        for name in sorted(key for key in all_zip if key.startswith("files/")):
            archive.writestr(name, all_zip[name])
        archive.writestr(f"{note_id}.jhinote", all_zip[f"{note_id}.jhinote"])
        archive.writestr("custom_md.jhinote", all_zip["custom_md.jhinote"])

    return _result_metadata(
        jnotes_path, output, jn, pages_src, ratio, total_stats, page_results, source_info,
        pdf_stats=pdf_stats,
    )


def _convert_pdf(
    jnotes_path: Path,
    output: Path,
    jn: JNote,
    pages_src: list[dict[str, Any]],
    source_info: JnotesContainerInfo,
    assets: dict[str, PdfAsset],
    bindings: dict[str, PdfPageBinding],
    pdf_stats: dict[str, Any],
) -> dict[str, Any]:
    """Convert parsed PDF-backed pages using v1.2.0's native-PDF layout."""
    note_id = uuid32()
    ts = now_ms()
    note_ratio = _pdf_base._page_geometry(jn, pages_src[0])[2]
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

    cover = _pdf_base._first_cover(jn)
    for page_idx, page in enumerate(pages_src, start=1):
        old_pid = str(page.get("a"))
        page_id = uuid32()
        page_files: dict[str, bytes] = {}
        page_attachments: list[dict[str, Any]] = []
        elements: list[dict[str, Any]] = []
        page_width, page_height, page_ratio = _pdf_base._page_geometry(jn, page)
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
                    page_id, page_width, page_height, 0, ts, filename,
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
                page_files[thumbnail_name] = _pdf_base._thumbnail_jpeg(cover)
        else:
            thumbnail_name = uuid32() + ".jpg"
            page_files[thumbnail_name] = render_thumbnail(
                jn, page, page_strokes, jn.images.get(old_pid, []), jn.texts.get(old_pid, []),
                find_cover_bytes(jn, page),
            )

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
                    if thumbnail_name else ""
                ),
                "unStructUuid": "",
                "data1": json.dumps(
                    {"detailFileMap": detail_map(page_files), "thumbnail_area": "", "book_mark": ""},
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                "data2": "",
                "data3": "",
                "data4": "",
                "data5": "",
            },
            "fileList": [file_info(name, data) for name, data in page_files.items()],
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
    top_detail = {name: [file_info(name, all_file_bytes[name])] for name in top_names}
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
        _pdf_base._write_archive(temporary, all_zip)
        _pdf_base._validate_pdf_archive(
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
    return _result_metadata(
        jnotes_path, output, jn, pages_src, note_ratio, total_stats, page_results, source_info,
        pdf_stats=pdf_stats,
    )


def convert(
    jnotes_path: Path,
    output: Path,
    page_limit: int | None = None,
) -> dict[str, Any]:
    """Convert a Jnotes file while accepting both known outer ZIP variants."""
    jn, source_info = parse_jnotes_with_info(jnotes_path)
    pages_src = jn.pages[:page_limit] if page_limit else jn.pages
    if not pages_src:
        raise ValueError("源笔记没有页面")

    assets, bindings, pdf_stats = _pdf_base._resolve_pdf_pages(jn, pages_src)
    if not bindings:
        return _convert_regular(jnotes_path, output, jn, pages_src, source_info, pdf_stats)
    return _convert_pdf(
        jnotes_path, output, jn, pages_src, source_info, assets, bindings, pdf_stats,
    )


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

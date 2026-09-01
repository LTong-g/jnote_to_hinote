#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Jnotes2Hinote v1.1.2 转换核心。

v1.1.2 保留 v1.1.1 的 Jnotes/Hinote 序列化和笔迹映射行为，仅修复缩略图
绘制中文文本时 Pillow 默认字体不支持中文而导致转换失败的问题。

v1.1.1 作为历史版本核心保留不变；本模块复用其已验证的底层构建函数，
并提供 v1.1.2 的独立转换入口和报告版本号。
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from . import converter_v1_1_1 as _base
from .converter_v1_1_1 import *  # noqa: F401,F403

__version__ = "1.1.2"


def __getattr__(name: str) -> Any:
    """Keep private helper compatibility while leaving the old module untouched."""
    return getattr(_base, name)


def _thumbnail_font_candidates() -> list[Path]:
    """Return common system fonts with Chinese and Latin glyph coverage."""
    font_names = (
        "msyh.ttc",                 # Microsoft YaHei
        "simhei.ttf",               # SimHei
        "simsun.ttc",               # SimSun
        "Deng.ttf",                 # DengXian
        "NotoSansCJK-Regular.ttc",
        "NotoSansSC-Regular.otf",
        "SourceHanSansSC-Regular.otf",
    )
    font_dirs: list[Path] = []
    if os.name == "nt":
        windir = os.environ.get("WINDIR", r"C:\Windows")
        font_dirs.append(Path(windir) / "Fonts")
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            font_dirs.append(Path(local_app_data) / "Microsoft" / "Windows" / "Fonts")
    font_dirs.extend(
        (
            Path("/System/Library/Fonts"),
            Path("/Library/Fonts"),
            Path("/usr/share/fonts/opentype/noto"),
            Path("/usr/share/fonts/truetype/noto"),
            Path("/usr/share/fonts/truetype/wqy"),
        )
    )
    return [font_dir / name for font_dir in font_dirs for name in font_names]


@lru_cache(maxsize=8)
def _load_thumbnail_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a local font for thumbnail text, with a safe Pillow fallback."""
    for font_path in _thumbnail_font_candidates():
        if not font_path.is_file():
            continue
        try:
            return ImageFont.truetype(str(font_path), size=size)
        except (OSError, ValueError):
            continue
    return ImageFont.load_default()


def _draw_thumbnail_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
) -> None:
    """Draw thumbnail text without letting an unavailable fallback font abort conversion."""
    try:
        draw.text(xy, text, fill=(0, 0, 0, 255), font=font)
    except UnicodeEncodeError:
        # The default Pillow bitmap font only supports Latin-1. This branch is
        # a last-resort safeguard for machines without a CJK system font.
        fallback_text = text.encode("ascii", errors="replace").decode("ascii")
        draw.text(xy, fallback_text, fill=(0, 0, 0, 255), font=font)


def render_thumbnail(
    jn: JNote,
    page: dict[str, Any],
    strokes: list[dict[str, Any]],
    images: list[tuple[dict[str, Any], bytes]],
    texts: list[dict[str, Any]],
    cover: bytes | None,
    out_w: int = 300,
) -> bytes:
    """Render a page thumbnail using an installed Chinese/Latin system font."""
    ratio = jn.width / jn.height
    out_h = max(1, round(out_w / ratio))
    im = Image.new("RGB", (out_w, out_h), "white")
    draw = ImageDraw.Draw(im, "RGBA")
    thumbnail_font = _load_thumbnail_font(max(10, round(out_w / 30)))

    if cover:
        try:
            ci = Image.open(io.BytesIO(cover)).convert("RGB").resize((out_w, out_h))
            im.paste(ci, (0, 0))
        except Exception:
            pass

    for meta, data in images:
        if not data:
            continue
        try:
            ii = Image.open(io.BytesIO(data)).convert("RGBA")
            x = round(float(meta.get("x", 0)) / jn.width * out_w)
            y = round(float(meta.get("y", 0)) / jn.height * out_h)
            w = max(1, round(float(meta.get("c", jn.width)) / jn.width * out_w))
            h = max(1, round(float(meta.get("d", jn.height)) / jn.height * out_h))
            ii.thumbnail((w, h))
            layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
            layer.alpha_composite(ii, (x, y))
            im = Image.alpha_composite(im.convert("RGBA"), layer).convert("RGB")
            draw = ImageDraw.Draw(im, "RGBA")
        except Exception:
            pass

    for rec in strokes:
        c = rec.get("c", {})
        if int(c.get("a", -1)) == 10:
            continue
        pts = c.get("k") or []
        if len(pts) < 2:
            continue
        argb = int(c.get("c", -12698050)) & 0xFFFFFFFF
        a, r, g, b = (argb >> 24) & 255, (argb >> 16) & 255, (argb >> 8) & 255, argb & 255
        if a == 0:
            a = 255
        xy_points = [(float(p.get("x", 0)) / jn.width * out_w, float(p.get("y", 0)) / jn.height * out_h) for p in pts]
        wd = max(1, round(float(c.get("d", 3)) * out_w / jn.width))
        draw.line(xy_points, fill=(r, g, b, a), width=wd, joint="curve")

    for t in texts:
        x = round(float(t.get("x", 0)) / jn.width * out_w)
        y = round(float(t.get("y", 0)) / jn.height * out_h)
        _draw_thumbnail_text(draw, (x, y), str(t.get("e", ""))[:100], thumbnail_font)

    bio = io.BytesIO()
    im.save(bio, "JPEG", quality=75, optimize=True)
    return bio.getvalue()


def convert(
    jnotes_path: Path,
    output: Path,
    page_limit: int | None = None,
) -> dict[str, Any]:
    """Convert a `.Jnotes` notebook to a self-contained Huawei `.hinote` archive."""
    jn = parse_jnotes(jnotes_path)
    pages_src = jn.pages[:page_limit] if page_limit else jn.pages
    if not pages_src:
        raise ValueError("源笔记没有页面")

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
            fn = uuid32() + ext
            page_files[fn] = cover
            elements.append(make_image_element({"x": 0, "y": 0, "c": jn.width, "d": jn.height, "e": 0}, page_id, jn.width, jn.height, 0, ts, fn))

        for meta, data in jn.images.get(old_pid, []):
            if not data:
                continue
            fn = uuid32() + image_ext(data)
            page_files[fn] = data
            elements.append(make_image_element(meta, page_id, jn.width, jn.height, zpos, ts, fn))
            zpos += 1

        for t in jn.texts.get(old_pid, []):
            elements.append(make_text_element(t, page_id, jn.width, jn.height, zpos, ts))
            zpos += 1

        page_strokes = list(jn.strokes.get(old_pid, []))
        page_strokes.sort(key=lambda r: (int(r.get("b", 0)), int(r.get("e", 0))))
        convertible = [r for r in page_strokes if int(r.get("c", {}).get("a", -1)) != 10]
        bin_size = 0
        pstats = {"normal": 0, "geometry": 0, "geometryFallback": 0, "paperTapeSkipped": len(page_strokes) - len(convertible)}
        if convertible:
            bin_name = uuid32() + ".bin"
            bin_data, pstats = build_pencilengine(page_strokes, sx)
            page_files[bin_name] = bin_data
            bin_size = len(bin_data)
            attachments.append({
                "attachType": 0, "cloudSyncState": 1, "createTime": ts,
                "filePath": f"/data/user/0/com.huawei.hinote/files/hwFile/{bin_name}",
                "isDelete": 0, "modifiedTime": ts, "notesId": note_id, "playbackProgress": 0,
                "id": uuid32(), "notePageId": page_id, "data1": '{"pageElementId":""}',
                "data2": "", "data3": "", "data4": "", "data5": "", "unStructUuid": "",
                "transText": None, "contentText": "",
            })
        for k, v in pstats.items():
            total_stats[k] += v

        thumb_name = uuid32() + ".jpg"
        thumb = render_thumbnail(jn, page, page_strokes, jn.images.get(old_pid, []), jn.texts.get(old_pid, []), cover)
        page_files[thumb_name] = thumb

        p_filelist = [file_info(n, d) for n, d in page_files.items()]
        pdm = detail_map(page_files)
        page_obj = {
            "customNotePageContent": {
                "pageBookMarks": [], "attachment": attachments, "background": background_for_page(page),
                "bkgAttachmentId": "", "bkgAttachmentIndex": 0, "chapterNumber": "", "cloudSyncState": 1,
                "createTime": ts, "guid": "", "id": page_id, "isDelete": 0,
                "lastPageTag": 1 if page_idx == len(pages_src) else 0, "modifiedTime": ts, "notesId": note_id,
                "pageColor": -1, "pageElement": elements, "pageNumber": page_idx, "pageOrientation": 0,
                "pageRatio": ratio, "pageType": 1,
                "thumbnail": f"/data/user/0/com.huawei.hinote/files/thumbnail/{thumb_name}",
                "unStructUuid": "",
                "data1": json.dumps({"detailFileMap": pdm, "thumbnail_area": "", "book_mark": ""}, ensure_ascii=False, separators=(",", ":")),
                "data2": "", "data3": "", "data4": "", "data5": "",
            },
            "fileList": p_filelist,
        }
        page_path = f"pages/{page_id}.jhinote"
        all_zip[page_path] = gzip_json(page_obj)
        for fn, d in page_files.items():
            all_zip[f"files/{fn}"] = d
            all_file_bytes[fn] = d

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
            "attachment": [], "background": background_for_page(pages_src[0]),
            "categoryId": "system_category_uuid_unclassified", "cloudSyncState": 1,
            "createTime": ts,
            "data1": json.dumps({
                "relationTags": "[]", "relationPages": "", "originDeviceType": "tablet",
                "isContentCover": "1", "isInfNote": "0", "infStylusPath": "",
                "detailFileMap": json.dumps(top_detail, separators=(",", ":")),
                "record_item_mapper_key": "", "localData1": "",
            }, ensure_ascii=False, separators=(",", ":")),
            "deleteTag": 0, "deleteTime": 0, "extendFields": "hinote_1.0.5", "guid": "",
            "hasCover": 1, "id": note_id, "isFavorite": 0, "isTop": 0, "modifiedTime": ts,
            "noteIcon": "base_7", "noteTitle": jn.title, "noteType": 100, "pageColor": -1,
            "pageOrientation": 0, "pageRatio": ratio, "unStructUuid": "", "bookIntroduction": "",
            "userId": "", "noteTemplate": "", "data2": "", "data3": "", "data4": "", "data5": "",
            "coverId": "", "parentId": "system_category_uuid_unclassified", "outLineAttachment": [],
            "recordItemEntities": [],
        },
        "fileList": [{"name": outline_name, "hash": outline_hash}],
    }
    all_zip[f"{note_id}.jhinote"] = gzip_json(top)

    md = [
        {"fileMdStr": sha256_hex(data, True), "fileNameMdStr": sha256_hex(name.encode("utf-8"), False)}
        for name, data in all_file_bytes.items()
    ]
    all_zip["custom_md.jhinote"] = gzip_json({"customMdContents": md})

    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for n in sorted(k for k in all_zip if k.startswith("pages/")):
            z.writestr(n, all_zip[n])
        for n in sorted(k for k in all_zip if k.startswith("files/")):
            z.writestr(n, all_zip[n])
        z.writestr(f"{note_id}.jhinote", all_zip[f"{note_id}.jhinote"])
        z.writestr("custom_md.jhinote", all_zip["custom_md.jhinote"])

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
        "pageRatio": ratio,
        "sourceRecords": len(jn.records),
        "audioRecordsDetectedButNotConverted": len(jn.audio_records),
        "strokeStats": dict(total_stats),
        "pageStats": page_results,
        "outputBytes": output.stat().st_size,
    }

"""Current Jnotes-to-Hinote conversion implementation.

The module contains the current editable-ink serialization, native PDF
embedding, page metadata, archive ordering, thumbnail regeneration, and safe
output handling. Historical releases are available from Git tags.
"""
from __future__ import annotations

import gzip
import hashlib
import html
import io
import json
import math
import os
import struct
import time
import uuid
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path, PurePosixPath
from typing import Any

from PIL import Image, JpegImagePlugin
from pypdf import PdfReader

from ._version import __version__
from .reader import JNote, JnotesContainerInfo, parse_jnotes, parse_jnotes_with_info
from .thumbnail import (
    THUMBNAIL_JPEG_SUBSAMPLING,
    THUMBNAIL_MAX_EDGE,
    PdfThumbnailRenderer,
    render_regular_thumbnail,
    thumbnail_dimensions,
)

TESTED_JNOTES_VERSION = "3.2.3.2"
TESTED_HUAWEI_NOTES_VERSION = "15.0.14.295"


def u32be(v: int) -> bytes:
    return struct.pack(">I", v & 0xFFFFFFFF)


def f32be(v: float) -> bytes:
    return struct.pack(">f", float(v))


def sha256_hex(data: bytes, upper: bool = True) -> str:
    h = hashlib.sha256(data).hexdigest()
    return h.upper() if upper else h.lower()


def uuid32() -> str:
    return uuid.uuid4().hex


def now_ms() -> int:
    return int(time.time() * 1000)


def gzip_json(obj: Any) -> bytes:
    raw = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return gzip.compress(raw, compresslevel=6, mtime=0)


# PENCILENGINE binary structure


def _parse_normal_pencilengine(data: bytes) -> list[tuple[int, int, int, int, int, int]]:
    """解析带 64 字节尾部和 12 字节尾标记的标准 v15 PENCILENGINE 链。"""
    if not data.startswith(b"PENCILENGINE"):
        raise ValueError("不是 PENCILENGINE 二进制文件")
    blocks: list[tuple[int, int, int, int, int, int]] = []
    pos = 196
    while pos < len(data) - 12:
        ph = pos + 108
        if ph + 16 > len(data) - 12:
            raise ValueError("PENCILENGINE 样式/文件头被截断")
        prefix, count, stride, reserved = struct.unpack_from(">IIII", data, ph)
        if prefix not in (0, 2) or not (2 <= count <= 20000) or stride != 36 or reserved != 0:
            raise ValueError(f"PENCILENGINE 在 {pos} 处出现异常数据块")
        ps = ph + 16
        pe = ps + count * 36
        end = pe + 64
        if end > len(data) - 12:
            raise ValueError("PENCILENGINE 数据块被截断")
        blocks.append((pos, ph, count, ps, pe, end))
        pos = end
    if pos != len(data) - 12:
        raise ValueError("PENCILENGINE 尾标记位置异常")
    return blocks


# Ink and geometry serialization


J_TO_HW_PEN = {
    1: 2,  # Jnotes 圆珠笔 -> 华为圆珠笔
    2: 1,  # Jnotes 钢笔 -> 华为钢笔
    3: 5,  # Jnotes 荧光笔 -> 华为荧光笔
    5: 3,  # Jnotes 铅笔 -> 华为 HB 铅笔
}

# Jnotes 规则化/显式几何图形 -> 华为原生几何图形代码。
J_GEOMETRY_TO_HW_SHAPE = {
    (6, 0): 0,   # 手写规则化直线
    (6, 12): 16, # 手写规则化曲线
    (6, 4): 10,  # 识别出的椭圆
    (7, 3): 7,   # 显式矩形工具
    (7, 4): 10,  # 显式圆/椭圆工具
}


def _source_rgb(c: dict[str, Any]) -> tuple[int, int, int]:
    argb = int(c.get("c", -16777216)) & 0xFFFFFFFF
    return (argb >> 16) & 0xFF, (argb >> 8) & 0xFF, argb & 0xFF


def _source_alpha(c: dict[str, Any]) -> int:
    argb = int(c.get("c", -16777216)) & 0xFFFFFFFF
    return (argb >> 24) & 0xFF


def _write_huawei_bgr(style: bytearray, c: dict[str, Any]) -> None:
    r, g, b = _source_rgb(c)
    style[64:68] = f32be(b / 255.0)
    style[68:72] = f32be(g / 255.0)
    style[72:76] = f32be(r / 255.0)


def _normal_tail(cur_count: int, next_count: int, stroke_uuid: bytes, seq: int) -> bytes:
    t = bytearray(64)
    t[0:4] = f32be(float(cur_count - 1))
    t[4:8] = u32be(48)
    t[8:12] = u32be(0)
    t[12:16] = u32be(65538)
    t[16:20] = u32be(next_count * 36 + 140)
    t[20:36] = stroke_uuid
    t[36:40] = u32be(68)
    t[40:44] = u32be(52)
    t[44:48] = u32be(120)
    t[48:52] = u32be(next_count * 36 + 20)
    t[52:56] = u32be(0)
    t[56:60] = u32be(seq)
    t[60:64] = u32be(0)
    return bytes(t)


def _end_tail(cur_count: int, stroke_uuid: bytes) -> bytes:
    t = bytearray(64)
    t[0:4] = f32be(float(cur_count - 1))
    t[4:8] = u32be(40)
    t[8:12] = u32be(3)
    t[12:16] = u32be(65536)
    t[16:20] = u32be(0)
    t[20:36] = stroke_uuid
    t[36:40] = u32be(0)
    t[40:44] = u32be(0)
    t[44:48] = u32be(32)
    t[48:52] = u32be(4)
    t[52:56] = u32be(65536)
    t[56:60] = u32be(0)
    t[60:64] = u32be(0)
    return bytes(t)


def _resample_xy(points: list[dict[str, Any]], n: int) -> list[tuple[float, float]]:
    if not points:
        return [(0.0, 0.0)] * n
    if len(points) == 1:
        p = points[0]
        return [(float(p.get("x", 0.0)), float(p.get("y", 0.0)))] * n
    out: list[tuple[float, float]] = []
    for i in range(n):
        p = points[round(i * (len(points) - 1) / (n - 1))]
        out.append((float(p.get("x", 0.0)), float(p.get("y", 0.0))))
    return out


def _make_header_skeleton() -> bytes:
    """创建 v1.1.1 使用的最小华为笔记 15.0.14.295 PENCILENGINE 文件头。"""
    h = bytearray(196)
    h[0:12] = b"PENCILENGINE"
    h[12:16] = u32be(76)
    h[16:20] = u32be(65537)
    h[20:24] = u32be(0)
    h[24:28] = u32be(1)
    h[76:80] = u32be(48)
    h[80:84] = u32be(2)
    h[84:88] = u32be(65536)
    h[92:108] = uuid.uuid4().bytes
    h[108:112] = u32be(12)
    h[120:124] = u32be(1)
    h[124:128] = u32be(0)
    h[128:132] = u32be(1000)
    h[132:136] = u32be(625)
    return bytes(h)


def _make_style(
    count: int,
    pen_type: int,
    c: dict[str, Any],
    width: float,
    *,
    shape_code: int | None = None,
    highlighter: bool = False,
) -> bytes:
    s = bytearray(108)
    s[0:4] = f32be(float(count - 1))
    s[4:8] = b"\x01\x01\x00\x00" if highlighter else b"\x01\x00\x00\x00"
    s[8:12] = u32be(0xFFFFFFFF if shape_code is None else shape_code)
    s[56:60] = u32be(pen_type)
    _write_huawei_bgr(s, c)

    opacity = 1.0
    if highlighter:
        opacity = min(80.0 / 255.0, _source_alpha(c) / 255.0)
    s[76:80] = f32be(opacity)
    s[80:84] = f32be(opacity)
    s[84:88] = f32be(width)

    # 目标版本中经过设备验证的工具标志。
    if pen_type in (3, 5) or shape_code is not None:
        s[92:96] = u32be(0x0040A000)
    s[104:108] = f32be(1.0)
    return bytes(s)


def _make_point_header(count: int, prefix: int = 0) -> bytes:
    return u32be(prefix) + u32be(count) + u32be(36) + u32be(0)


def _make_normal_point(i: int, count: int, x: float, y: float, pressure: float) -> bytes:
    b = bytearray(36)
    b[0:4] = f32be(float(max(0, i - 1)))
    b[4:8] = f32be(x)
    b[8:12] = f32be(y)
    b[12:16] = u32be(round(i * 3.75))
    b[16:20] = f32be(pressure)
    b[20:24] = f32be(2.3)
    b[24:28] = f32be(10.0)
    b[28:32] = f32be(0.2)
    if count == 1:
        flag = 1
    elif i == 0:
        flag = 4
    elif i == count - 1:
        flag = 5
    else:
        flag = 6
    b[32:36] = u32be(flag)
    return bytes(b)


def _make_shape_point(i: int, x: float, y: float) -> bytes:
    b = bytearray(36)
    b[0:4] = f32be(float(max(0, i - 1)))
    b[4:8] = f32be(x)
    b[8:12] = f32be(y)
    b[12:16] = u32be(0)
    b[16:20] = f32be(1.0)
    b[20:24] = f32be(0.0)
    b[24:28] = f32be(0.0)
    b[28:32] = f32be(0.2)
    b[32:36] = u32be(1)
    return bytes(b)


def _build_normal_body(rec: dict[str, Any], sx: float) -> tuple[bytes, int]:
    c = rec.get("c", {})
    pts = c.get("k") or []
    if len(pts) < 2:
        pts = (pts or [{"x": 0.0, "y": 0.0, "p": 0.2}]) * 2

    jtype = int(c.get("a", 2))
    htype = J_TO_HW_PEN.get(jtype, 1)
    count = len(pts)
    width = float(c.get("d", 4.0))
    highlighter = jtype == 3
    if highlighter:
        # 已在华为笔记 15.0.14.295 上完成设备标定。
        width *= 16.0 / 3.0

    style = _make_style(count, htype, c, width, highlighter=highlighter)
    body = bytearray(style)
    body.extend(_make_point_header(count, 0))
    for i, p in enumerate(pts):
        x = float(p.get("x", 0.0)) * sx
        y = float(p.get("y", 0.0)) * sx
        pressure = float(p.get("p", 0.2))
        if not math.isfinite(pressure):
            pressure = 0.2
        pressure = max(0.001, min(1.0, pressure))
        body.extend(_make_normal_point(i, count, x, y, pressure))
    return bytes(body), count


def _bbox_coords(points: list[dict[str, Any]], sx: float) -> tuple[float, float, float, float]:
    xs = [float(p.get("x", 0.0)) * sx for p in points] or [0.0]
    ys = [float(p.get("y", 0.0)) * sx for p in points] or [0.0]
    return min(xs), max(xs), min(ys), max(ys)


def _geometry_width_direct(d: float) -> float:
    """使用与普通笔迹相同的 Jnotes 宽度直接值。"""
    width = float(d)
    if not math.isfinite(width):
        raise ValueError("几何宽度必须是有限数值")
    return width


def _build_geometry_body(rec: dict[str, Any], sx: float) -> tuple[bytes, int, bool]:
    c = rec.get("c", {})
    jt = int(c.get("a", -1))
    subtype = int(c.get("b", -1))
    alpha = _source_alpha(c)

    # 验证笔记中经过设备确认的特殊情况：
    # 半透明 type=6,b=12 对象是由荧光笔生成的平滑曲线。
    # 在观察到的 Jnotes 3.2.3.2 数据中，几何 d=30 对应源荧光笔 d=6，
    # 后者映射为华为荧光笔宽度 32。
    if jt == 6 and subtype == 12 and alpha < 255:
        pseudo = {"c": dict(c)}
        pseudo["c"]["a"] = 3
        pseudo["c"]["d"] = float(c.get("d", 30.0)) / 5.0
        body, count = _build_normal_body(pseudo, sx)
        style = bytearray(body[:108])
        opacity = alpha / 255.0
        style[76:80] = f32be(opacity)
        style[80:84] = f32be(opacity)
        return bytes(style) + body[108:], count, False

    shape_code = J_GEOMETRY_TO_HW_SHAPE.get((jt, subtype))
    width = _geometry_width_direct(float(c.get("d", 3.0)))

    if shape_code is None:
        # 未知几何子类型：将可见路径保留为圆珠笔笔迹。
        pseudo = {"c": dict(c)}
        pseudo["c"]["a"] = 1
        body, count = _build_normal_body(pseudo, sx)
        style = bytearray(body[:108])
        style[84:88] = f32be(width)
        return bytes(style) + body[108:], count, False

    k = c.get("k") or []
    if shape_code == 0:
        count = 2
        l = c.get("l") or []
        source = l if len(l) >= 2 else k
        if len(source) >= 2:
            coords = [
                (float(source[0].get("x", 0.0)) * sx, float(source[0].get("y", 0.0)) * sx),
                (float(source[-1].get("x", 0.0)) * sx, float(source[-1].get("y", 0.0)) * sx),
            ]
        else:
            coords = [(0.0, 0.0), (0.0, 0.0)]
        prefix = 2
    elif shape_code == 7:
        count = 5
        x0, x1, y0, y1 = _bbox_coords(k, sx)
        coords = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
        prefix = 2
    elif shape_code == 10:
        count = 361
        x0, x1, y0, y1 = _bbox_coords(k, sx)
        cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        rx, ry = (x1 - x0) / 2.0, (y1 - y0) / 2.0
        coords = []
        for i in range(count):
            angle = 2.0 * math.pi * i / (count - 1)
            coords.append((cx + rx * math.cos(angle), cy + ry * math.sin(angle)))
        prefix = 0
    else:  # 华为图形代码 16：平滑曲线
        count = 101
        coords = [(x * sx, y * sx) for x, y in _resample_xy(k, count)]
        prefix = 0

    style = _make_style(count, 2, c, width, shape_code=shape_code)
    body = bytearray(style)
    body.extend(_make_point_header(count, prefix))
    for i, (x, y) in enumerate(coords):
        body.extend(_make_shape_point(i, x, y))
    return bytes(body), count, True


def build_pencilengine(strokes: list[dict[str, Any]], sx: float) -> tuple[bytes, dict[str, int]]:
    """在不依赖华为参考笔记的情况下生成完整的 PENCILENGINE 链接文件。"""
    convertible = [r for r in strokes if int(r.get("c", {}).get("a", -1)) != 10]
    if not convertible:
        raise ValueError("没有可转换的手写笔迹")

    bodies: list[bytes] = []
    counts: list[int] = []
    ids: list[bytes] = []
    stats = {
        "normal": 0,
        "geometry": 0,
        "geometryFallback": 0,
        "paperTapeSkipped": len(strokes) - len(convertible),
    }

    for rec in convertible:
        jt = int(rec.get("c", {}).get("a", -1))
        if jt in (6, 7):
            body, count, native = _build_geometry_body(rec, sx)
            stats["geometry" if native else "geometryFallback"] += 1
        else:
            body, count = _build_normal_body(rec, sx)
            stats["normal"] += 1
        bodies.append(body)
        counts.append(count)
        ids.append(uuid.uuid4().bytes)

    header = bytearray(_make_header_skeleton())
    header[92:108] = uuid.uuid4().bytes
    header[112:116] = u32be(len(bodies))
    header[136:140] = u32be(48)
    header[140:144] = u32be(0)
    header[144:148] = u32be(65538)
    header[148:152] = u32be(counts[0] * 36 + 140)
    header[152:168] = uuid.uuid4().bytes
    header[168:172] = u32be(68)
    header[172:176] = u32be(52)
    header[176:180] = u32be(120)
    header[180:184] = u32be(counts[0] * 36 + 20)
    header[184:188] = u32be(0)
    root_seq = (int(time.time() * 1000) // 10) & 0x7FFFFFFF
    header[188:192] = u32be(root_seq)
    header[192:196] = u32be(0)

    body = bytearray()
    seq = root_seq + 1
    for i in range(len(bodies) - 1):
        body.extend(bodies[i])
        body.extend(_normal_tail(counts[i], counts[i + 1], ids[i], seq))
        seq = (seq + 1) & 0xFFFFFFFF
    body.extend(bodies[-1])
    body.extend(_end_tail(counts[-1], ids[-1]))

    trailer = b"\x00" * 12
    total_len = len(header) + len(body) + len(trailer)
    header[88:92] = u32be(total_len - 124)
    header[116:120] = u32be(total_len - 196)
    result = bytes(header) + bytes(body) + trailer

    # 结构自检，用于捕获根链接/后续计数回归。
    blocks = _parse_normal_pencilengine(result)
    if len(blocks) != len(bodies):
        raise AssertionError("PENCILENGINE 笔迹数量验证失败")
    if struct.unpack_from(">I", result, 148)[0] != counts[0] * 36 + 140:
        raise AssertionError("PENCILENGINE 根指针 A 验证失败")
    if struct.unpack_from(">I", result, 180)[0] != counts[0] * 36 + 20:
        raise AssertionError("PENCILENGINE 根指针 B 验证失败")
    for i in range(len(blocks) - 1):
        pe = blocks[i][4]
        next_count = blocks[i + 1][2]
        if struct.unpack_from(">I", result, pe + 16)[0] != next_count * 36 + 140:
            raise AssertionError("PENCILENGINE 后续指针 A 验证失败")
        if struct.unpack_from(">I", result, pe + 48)[0] != next_count * 36 + 20:
            raise AssertionError("PENCILENGINE 后续指针 B 验证失败")
    return result, stats

# Page elements and backgrounds


def image_ext(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"GIF8"):
        return ".gif"
    return ".bin"


def numeric_entities(s: str) -> str:
    out: list[str] = []
    for ch in s:
        if ch == "\n":
            out.append("<br>\n")
        elif ord(ch) < 128:
            out.append(html.escape(ch, quote=False))
        else:
            out.append(f"&#{ord(ch)};")
    return "".join(out)


def argb_hex(v: int) -> str:
    return f"#{v & 0xFFFFFFFF:08X}"


def make_text_element(t: dict[str, Any], page_id: str, note_w: float, note_h: float, z: int, ts: int) -> dict[str, Any]:
    text = str(t.get("e", ""))
    size = max(0.5, float(t.get("g", 40.0)) / 40.0)
    color = argb_hex(int(t.get("f", -16777216)))
    inner = f'<hw_font size ="{size:.2f}"><font color ="{color}">{numeric_entities(text)}</font></hw_font>'
    if t.get("m"):
        inner = f"<u>{inner}</u>"
    if t.get("k"):
        inner = f"<i>{inner}</i>"
    if t.get("j"):
        inner = f"<b>{inner}</b>"
    align = int(t.get("t8", 0))
    if align == 1:
        inner = f'<div align="center">{inner}</div>'
    elif align == 2:
        inner = f'<div align="right">{inner}</div>'
    h = f'<note><element type="Text">{inner}</element></note>'
    return {
        "id": uuid32(), "notePageId": page_id, "elementType": 0,
        "positionX": float(t.get("x", 0.0)) / note_w,
        "positionY": float(t.get("y", 0.0)) / note_h,
        "positionZ": z,
        "width": max(0.01, float(t.get("c", note_w * 0.3)) / note_w),
        "height": max(0.01, float(t.get("d", note_h * 0.05)) / note_h),
        "angle": 0.0,
        "contentText": text, "html": h, "filePath": None,
        "playbackProgress": 0, "cloudSyncState": 1,
        "createTime": ts, "modifiedTime": ts, "isDelete": 0,
        "unStructUuid": "", "transtext": None, "scale": 1.0,
        "data1": '{"sourceDpi":"370","type":"0"}',
        "data2": "", "data3": "", "data4": "", "data5": "",
    }


def make_image_element(meta: dict[str, Any], page_id: str, note_w: float, note_h: float, z: int, ts: int, file_name: str) -> dict[str, Any]:
    angle = float(meta.get("e", 0.0) or 0.0)
    if angle > 180:
        angle -= 360
    return {
        "id": uuid32(), "notePageId": page_id, "elementType": 1,
        "positionX": float(meta.get("x", 0.0)) / note_w,
        "positionY": float(meta.get("y", 0.0)) / note_h,
        "positionZ": z,
        "width": max(0.001, float(meta.get("c", note_w)) / note_w),
        "height": max(0.001, float(meta.get("d", note_h)) / note_h),
        "angle": angle,
        "contentText": "", "html": "",
        "filePath": f"/data/user/0/com.huawei.hinote/files/image/{file_name}",
        "playbackProgress": 0, "cloudSyncState": 1,
        "createTime": ts, "modifiedTime": ts, "isDelete": 0,
        "unStructUuid": "", "transtext": None, "scale": 1,
        "data1": '{"sourceDpi":"370","type":"0"}',
        "data2": "", "data3": "", "data4": "", "data5": "",
    }


def _paper_params(page: dict[str, Any]) -> tuple[str, float | None]:
    raw = page.get("p")
    bg = str(page.get("d", ""))
    ui_size: float | None = None
    if raw:
        try:
            obj = json.loads(str(raw))
            bg = str(obj.get("paperBg") or bg)
            hp = obj.get("horParts")
            if isinstance(hp, (int, float)):
                ui_size = float(hp) + 3.0
        except (json.JSONDecodeError, TypeError):
            pass
    return bg, ui_size


def background_for_page(page: dict[str, Any]) -> str:
    """将 Jnotes 纸张映射为华为原生 base 模板。

    已经设备确认的华为模板 ID：
      base1 空白、base4 宽横线、base5 窄横线、
      base6 点阵、base3 小/窄方格、base2 中/宽方格。
    """
    bg, ui_size = _paper_params(page)
    low = bg.lower()
    if "blank" in low or not low or "/cover/" in low:
        return "base1"
    if "white_line_paper_1_paper" in low:
        if ui_size is not None and ui_size <= 2.0:
            return "base5"
        return "base4"
    if "narrow-line" in low or "line" in low:
        return "base4"
    if "dotted" in low:
        return "base6"
    if "white_graph_paper" in low:
        if ui_size is not None and ui_size <= 4.0:
            return "base3"
        return "base2"
    if "wide_grid" in low:
        return "base2"
    return "base1"


def find_cover_bytes(jn: JNote, page: dict[str, Any]) -> bytes | None:
    d = str(page.get("d", ""))
    if "/Cover/" not in d and not page.get("i"):
        return None
    stem = d.rstrip("/").split("/")[-1]
    preferred = [f"{stem}.jpg", f"{stem}.png", f"{stem}_coverThumbnail.jpg"]
    for name in preferred:
        if name in jn.covers:
            return jn.covers[name]
    for name, data in jn.covers.items():
        if name.startswith(stem) and data.startswith((b"\xff\xd8\xff", b"\x89PNG")):
            return data
    return None


def file_info(name: str, data: bytes) -> dict[str, str]:
    return {"name": name, "hash": sha256_hex(data, True)}


def detail_map(files: dict[str, bytes]) -> str:
    m = {name: [file_info(name, data)] for name, data in files.items()}
    return json.dumps(m, ensure_ascii=False, separators=(",", ":"))


# Native PDF handling


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


def _basename(value: str) -> str:
    return str(value).replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]


def _pdf_page_count(payload: bytes) -> int:
    """Validate a PDF and return its page count without rendering it."""
    if not payload.startswith(b"%PDF-"):
        raise ValueError("Jnotes PDF 记录不是合法 PDF：缺少 %PDF- 文件头")

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
        if name.casefold().startswith(jn.note_uuid.casefold()) and data.startswith(
            (b"\xff\xd8\xff", b"\x89PNG")
        ):
            return data
    for data in jn.covers.values():
        if data.startswith((b"\xff\xd8\xff", b"\x89PNG")):
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

# Hinote archive assembly


def _render_initial_thumbnail(
    jn: JNote,
    page: dict[str, Any],
    strokes: list[dict[str, Any]],
    images: list[tuple[dict[str, Any], bytes]],
    texts: list[dict[str, Any]],
    cover: bytes | None,
) -> bytes:
    """Render the temporary page preview before final archive normalization."""
    page_width, page_height, _ = _page_geometry(jn, page)
    return render_regular_thumbnail(
        page_width=page_width,
        page_height=page_height,
        strokes=strokes,
        images=images,
        texts=texts,
        cover=cover,
    )


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
        "version": __version__,
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
        page_files[thumbnail_name] = _render_initial_thumbnail(
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
                page_files[thumbnail_name] = _thumbnail_jpeg(cover)
        else:
            thumbnail_name = uuid32() + ".jpg"
            page_files[thumbnail_name] = _render_initial_thumbnail(
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
    return _result_metadata(
        jnotes_path, output, jn, pages_src, note_ratio, total_stats, page_results, source_info,
        pdf_stats=pdf_stats,
    )


def _convert_content(
    jnotes_path: Path,
    output: Path,
    page_limit: int | None = None,
) -> dict[str, Any]:
    """Convert a Jnotes file while accepting both known outer ZIP variants."""
    jn, source_info = parse_jnotes_with_info(jnotes_path)
    pages_src = jn.pages[:page_limit] if page_limit else jn.pages
    if not pages_src:
        raise ValueError("源笔记没有页面")

    assets, bindings, pdf_stats = _resolve_pdf_pages(jn, pages_src)
    if not bindings:
        return _convert_regular(jnotes_path, output, jn, pages_src, source_info, pdf_stats)
    return _convert_pdf(
        jnotes_path, output, jn, pages_src, source_info, assets, bindings, pdf_stats,
    )

# Final thumbnail and orientation normalization


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
            page_width, page_height, _ = _page_geometry(jn, source_page)
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
                    cover=find_cover_bytes(jn, source_page),
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
            name = _thumbnail_name(str(content.get("thumbnail", "")))
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
            if detail_map.get(name) != [file_info(name, data)]:
                raise ValueError(f"Hinote 缩略图 detailFileMap 哈希不正确：{name}")

def _convert_with_normalized_thumbnails(
    jnotes_path: Path,
    output: Path,
    page_limit: int | None = None,
) -> dict[str, Any]:
    """Convert a Jnotes file using orientation-safe native-quality thumbnails."""
    jn, _ = parse_jnotes_with_info(jnotes_path)
    pages_src = jn.pages[:page_limit] if page_limit else jn.pages
    if not pages_src:
        raise ValueError("源笔记没有页面")
    assets, bindings, _ = _resolve_pdf_pages(jn, pages_src)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.{uuid32()}.tmp")
    try:
        result = _convert_content(jnotes_path, temporary, page_limit=page_limit)
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
    result["output"] = str(output)
    result["outputBytes"] = output.stat().st_size
    first_width, first_height, _ = _page_geometry(jn, pages_src[0])
    result["pageRatio"], result["pageOrientation"] = _hinote_page_geometry(first_width, first_height)
    for source_page, page_stats in zip(pages_src, result.get("pageStats", [])):
        page_width, page_height, _ = _page_geometry(jn, source_page)
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

# Public conversion entry point


def ensure_hinote_suffix(path: Path) -> Path:
    """Append ``.hinote`` unless the path already has that final suffix."""
    path = Path(path)
    if path.suffix.casefold() == ".hinote":
        return path
    return path.with_name(path.name + ".hinote")


def _same_file(source: Path, destination: Path) -> bool:
    if source.resolve(strict=False) == destination.resolve(strict=False):
        return True
    try:
        return source.exists() and destination.exists() and os.path.samefile(source, destination)
    except OSError:
        return False


def convert(jnotes_path: Path, output: Path, page_limit: int | None = None) -> dict[str, Any]:
    """Convert a Jnotes notebook after validating the requested output path."""
    jnotes_path = Path(jnotes_path)
    output = ensure_hinote_suffix(Path(output))
    if _same_file(jnotes_path, output):
        raise ValueError("输出文件不能与源 Jnotes 文件相同")
    return _convert_with_normalized_thumbnails(jnotes_path, output, page_limit=page_limit)


__all__ = [
    "TESTED_HUAWEI_NOTES_VERSION",
    "TESTED_JNOTES_VERSION",
    "JNote",
    "JnotesContainerInfo",
    "PdfAsset",
    "PdfPageBinding",
    "convert",
    "ensure_hinote_suffix",
    "parse_jnotes",
    "parse_jnotes_with_info",
]

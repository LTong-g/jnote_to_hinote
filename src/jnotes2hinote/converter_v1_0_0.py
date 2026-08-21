#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Jnotes2Hinote v1.0.0 转换核心。

适用的逆向工程格式：
- Jideos 云记 3.2.3.2
- 华为笔记 15.0.14.295

本文件是冻结的 v1.0.0 转换核心。未来重构应放入新的版本化模块，
不要静默修改本文件。

转换器有意要求用户提供华为参考 `.hinote` 文件。本项目不附带华为应用
资产或私人笔记样本。
"""
from __future__ import annotations

import gzip
import hashlib
import html
import io
import json
import math
import struct
import time
import uuid
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageDraw

__version__ = "1.0.0"
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


def java_utf_read(data: bytes, pos: int) -> tuple[str, int]:
    if pos + 2 > len(data):
        raise EOFError
    n = struct.unpack_from(">H", data, pos)[0]
    pos += 2
    if pos + n > len(data):
        raise EOFError
    s = data[pos : pos + n].decode("utf-8", errors="replace")
    return s, pos + n


@dataclass
class JRecord:
    typ: str
    source: str
    object_id: str
    parent_id: str
    aux_path: str
    aux_size: str
    payload: bytes
    binary: bytes = b""


@dataclass
class JNote:
    note_uuid: str
    title: str
    width: float
    height: float
    note_meta: dict[str, Any]
    pages: list[dict[str, Any]]
    records: list[JRecord]
    strokes: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: defaultdict(list))
    images: dict[str, list[tuple[dict[str, Any], bytes]]] = field(default_factory=lambda: defaultdict(list))
    texts: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: defaultdict(list))
    covers: dict[str, bytes] = field(default_factory=dict)
    audio_records: list[JRecord] = field(default_factory=list)


def parse_jnotes(path: Path) -> JNote:
    """解析 v1.0.0 使用的 Jnotes 3.2.3.2 ZIP/Jzip 容器。"""
    with zipfile.ZipFile(path) as z:
        if "zip.Jzip" not in z.namelist():
            raise ValueError("不是受支持的 .Jnotes 压缩包：缺少 zip.Jzip")
        data = z.read("zip.Jzip")

    pos = 0
    magic, pos = java_utf_read(data, pos)
    if magic != "TRY":
        raise ValueError(f"Jzip 魔数异常：{magic!r}")
    if pos + 4 > len(data):
        raise EOFError
    _version = struct.unpack_from(">i", data, pos)[0]
    pos += 4
    note_uuid, pos = java_utf_read(data, pos)

    records: list[JRecord] = []
    while pos + 4 <= len(data):
        start = pos
        try:
            marker = struct.unpack_from(">i", data, pos)[0]
            pos += 4
            if marker != 1:
                pos = start
                break
            typ, pos = java_utf_read(data, pos)
            src, pos = java_utf_read(data, pos)
            oid, pos = java_utf_read(data, pos)
            if pos + 8 > len(data):
                raise EOFError
            payload_len = struct.unpack_from(">q", data, pos)[0]
            pos += 8
            parent, pos = java_utf_read(data, pos)
            aux_path, pos = java_utf_read(data, pos)
            aux_size, pos = java_utf_read(data, pos)
            if payload_len < 0 or pos + payload_len > len(data):
                raise ValueError("Jnotes 负载长度无效")
            payload = data[pos : pos + payload_len]
            pos += payload_len
            binary = b""
            if aux_size.isdigit():
                blen = int(aux_size)
                if pos + blen > len(data):
                    raise ValueError("Jnotes 嵌入二进制长度无效")
                binary = data[pos : pos + blen]
                pos += blen
            records.append(JRecord(typ, src, oid, parent, aux_path, aux_size, payload, binary))
        except (EOFError, struct.error, UnicodeDecodeError, ValueError):
            pos = start
            break

    note_meta: dict[str, Any] | None = None
    pages: list[dict[str, Any]] = []
    strokes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    images: dict[str, list[tuple[dict[str, Any], bytes]]] = defaultdict(list)
    texts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    covers: dict[str, bytes] = {}
    audio_records: list[JRecord] = []

    for r in records:
        if r.typ == "NOTE":
            note_meta = json.loads(r.payload.decode("utf-8"))
        elif r.typ == "PAGE":
            pages.append(json.loads(r.payload.decode("utf-8")))
        elif r.typ == "STROKE":
            strokes[r.parent_id].extend(json.loads(r.payload.decode("utf-8")))
        elif r.typ == "IMAGE":
            images[r.parent_id].append((json.loads(r.payload.decode("utf-8")), r.binary))
        elif r.typ == "TEXT":
            texts[r.parent_id].extend(json.loads(r.payload.decode("utf-8")))
        elif r.typ == "COVER":
            covers[r.object_id] = r.payload
        elif r.typ == "AUDIO_EX":
            audio_records.append(r)

    if not note_meta:
        raise ValueError("缺少 Jnotes NOTE 记录")

    title = str(note_meta.get("b") or path.stem)
    width = float(note_meta.get("j", 1240.0))
    height = float(note_meta.get("l", 1754.0))
    out = JNote(note_uuid, title, width, height, note_meta, pages, records)
    out.strokes = strokes
    out.images = images
    out.texts = texts
    out.covers = covers
    out.audio_records = audio_records
    return out


@dataclass(frozen=True)
class StrokeTemplate:
    style: bytes
    point_header: bytes
    points: tuple[bytes, ...]

    @property
    def count(self) -> int:
        return len(self.points)


@dataclass(frozen=True)
class ShapeTemplate:
    shape_code: int
    style: bytes
    point_header: bytes
    points: tuple[bytes, ...]

    @property
    def count(self) -> int:
        return len(self.points)


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


def _parse_shape_reference(data: bytes) -> list[tuple[int, int, int, int, int, int]]:
    """解析华为原生图形页面中的笔迹主体。

    原生图形页面可能在最后一条笔迹之后带有扩展 UUID 索引，因此笔迹数量
    取自 header+112，而不是扫描到标准的 12 字节尾标记。
    """
    if not data.startswith(b"PENCILENGINE"):
        raise ValueError("不是 PENCILENGINE 二进制文件")
    n = struct.unpack_from(">I", data, 112)[0]
    blocks: list[tuple[int, int, int, int, int, int]] = []
    pos = 196
    for _ in range(n):
        ph = pos + 108
        prefix, count, stride, reserved = struct.unpack_from(">IIII", data, ph)
        if prefix not in (0, 2) or not (2 <= count <= 20000) or stride != 36 or reserved != 0:
            raise ValueError(f"图形参考数据在 {pos} 处出现异常数据块")
        ps = ph + 16
        pe = ps + count * 36
        end = pe + 64
        blocks.append((pos, ph, count, ps, pe, end))
        pos = end
    return blocks


class HuaweiReferenceTemplates:
    """提取用户自己的华为二进制模板。

    普通参考文件应包含 pen_type 1/2/3/5 的示例。当源笔记包含 Jnotes
    type 6/7 几何图形时，图形参考文件应包含原生图形代码 0/7/10/16。
    """

    def __init__(self, normal_reference: Path, shape_reference: Path | None = None):
        self.normal_reference = normal_reference
        self.shape_reference = shape_reference
        self.header: bytes
        self.trailer: bytes
        self.pen_templates: dict[int, list[StrokeTemplate]] = defaultdict(list)
        self.shape_templates: dict[int, ShapeTemplate] = {}
        self._load_normal(normal_reference)
        if shape_reference is not None:
            self._load_shapes(shape_reference)

    @staticmethod
    def _all_bins(path: Path) -> list[bytes]:
        with zipfile.ZipFile(path) as z:
            return [z.read(n) for n in z.namelist() if n.startswith("files/") and n.endswith(".bin")]

    def _load_normal(self, path: Path) -> None:
        bins = self._all_bins(path)
        if not bins:
            raise ValueError("普通参考 .hinote 不包含 PENCILENGINE .bin 文件")

        first_good: bytes | None = None
        for data in bins:
            try:
                blocks = _parse_normal_pencilengine(data)
            except ValueError:
                continue
            if not blocks:
                continue
            first_good = first_good or data
            for ss, ph, count, ps, _pe, _end in blocks:
                style = data[ss:ph]
                pen_type = struct.unpack_from(">I", style, 56)[0]
                if pen_type not in (1, 2, 3, 4, 5, 11, 12, 13):
                    continue
                pts = tuple(data[ps + i * 36 : ps + (i + 1) * 36] for i in range(count))
                self.pen_templates[pen_type].append(StrokeTemplate(style, data[ph:ps], pts))

        if first_good is None:
            raise ValueError("无法从普通参考文件解析标准 PENCILENGINE 链")
        self.header = first_good[:196]
        self.trailer = first_good[-12:]

        required = {1, 2, 3, 5}
        missing = sorted(required.difference(self.pen_templates))
        if missing:
            raise ValueError(
                "普通参考文件缺少必需的华为笔型："
                + ", ".join(map(str, missing))
            )

    def _load_shapes(self, path: Path) -> None:
        bins = self._all_bins(path)
        for data in bins:
            try:
                blocks = _parse_shape_reference(data)
            except (ValueError, struct.error):
                continue
            for ss, ph, count, ps, _pe, _end in blocks:
                style = data[ss:ph]
                pen_type = struct.unpack_from(">I", style, 56)[0]
                shape_code = struct.unpack_from(">I", style, 8)[0]
                if pen_type != 2 or shape_code not in (0, 7, 10, 16):
                    continue
                if shape_code in self.shape_templates:
                    continue
                pts = tuple(data[ps + i * 36 : ps + (i + 1) * 36] for i in range(count))
                self.shape_templates[shape_code] = ShapeTemplate(shape_code, style, data[ph:ps], pts)

    def choose_pen(self, pen_type: int, desired_count: int) -> StrokeTemplate:
        choices = self.pen_templates.get(pen_type)
        if not choices:
            choices = self.pen_templates.get(2)
        if not choices:
            raise ValueError(f"没有可用于 pen_type={pen_type} 的华为模板")
        return min(choices, key=lambda t: abs(t.count - desired_count))

    def require_shapes(self, codes: Iterable[int]) -> None:
        missing = sorted(set(codes).difference(self.shape_templates))
        if missing:
            raise ValueError(
                "图形参考文件缺少必需的原生图形代码："
                + ", ".join(map(str, missing))
                + "。请创建/导出一份包含直线、曲线、矩形和圆图形的华为笔记，"
                "然后通过 --shape-reference-hinote 传入。"
            )


J_TO_HW_PEN = {
    1: 2,  # Jnotes 圆珠笔 -> 华为圆珠笔
    2: 1,  # Jnotes 钢笔 -> 华为钢笔
    3: 5,  # Jnotes 荧光笔 -> 华为荧光笔
    5: 3,  # Jnotes 铅笔 -> 华为 HB 铅笔
}

# Jnotes 规则化/显式几何图形 -> 华为原生几何图形代码。
J_GEOMETRY_TO_HW_SHAPE = {
    (6, 0): 0,   # 手写规则化为直线
    (6, 12): 16, # 手写规则化为曲线
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


def _resample_source_points(points: list[dict[str, Any]], n: int) -> list[dict[str, Any]]:
    if not points:
        return [{"x": 0.0, "y": 0.0, "p": 0.2}] * n
    if len(points) == 1:
        return [points[0]] * n
    return [points[round(i * (len(points) - 1) / (n - 1))] for i in range(n)]


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


def _build_normal_body(
    rec: dict[str, Any],
    refs: HuaweiReferenceTemplates,
    sx: float,
) -> tuple[bytes, int]:
    c = rec.get("c", {})
    pts = c.get("k") or []
    jtype = int(c.get("a", 2))
    htype = J_TO_HW_PEN.get(jtype, 1)
    desired = max(2, len(pts))
    tpl = refs.choose_pen(htype, desired)
    count = tpl.count
    sampled = _resample_source_points(pts, count)

    style = bytearray(tpl.style)
    style[0:4] = f32be(float(count - 1))
    style[4:8] = b"\x01\x00\x00\x00"
    style[8:12] = u32be(0xFFFFFFFF)
    style[56:60] = u32be(htype)
    _write_huawei_bgr(style, c)

    width = float(c.get("d", 4.0))
    if jtype == 3:
        # 已在华为笔记 15.0.14.295 上完成设备标定。
        width = width * 16.0 / 3.0
        opacity = min(80.0 / 255.0, _source_alpha(c) / 255.0)
        style[76:80] = f32be(opacity)  # 实际渲染透明度
        style[80:84] = f32be(opacity)  # 选择/界面透明度
    style[84:88] = f32be(width)

    ph = bytearray(tpl.point_header)
    ph[4:8] = u32be(count)
    ph[8:12] = u32be(36)
    ph[12:16] = u32be(0)

    body = bytearray(style)
    body.extend(ph)
    for proto, p in zip(tpl.points, sampled):
        pb = bytearray(proto)
        x = float(p.get("x", 0.0)) * sx
        y = float(p.get("y", 0.0)) * sx
        pressure = float(p.get("p", 0.2))
        if not math.isfinite(pressure):
            pressure = 0.2
        pressure = max(0.001, min(1.0, pressure))
        pb[4:8] = f32be(x)
        pb[8:12] = f32be(y)
        pb[16:20] = f32be(pressure)
        body.extend(pb)
    return bytes(body), count


def _circle_affine_coords(tpl: ShapeTemplate, source_points: list[dict[str, Any]], sx: float) -> list[tuple[float, float]]:
    ref_xy = [struct.unpack_from(">ff", p, 4) for p in tpl.points]
    rx0, rx1 = min(x for x, _ in ref_xy), max(x for x, _ in ref_xy)
    ry0, ry1 = min(y for _, y in ref_xy), max(y for _, y in ref_xy)
    xs = [float(p.get("x", 0.0)) * sx for p in source_points] or [0.0]
    ys = [float(p.get("y", 0.0)) * sx for p in source_points] or [0.0]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    coords: list[tuple[float, float]] = []
    for x, y in ref_xy:
        nx = (x - rx0) / (rx1 - rx0) if rx1 != rx0 else 0.5
        ny = (y - ry0) / (ry1 - ry0) if ry1 != ry0 else 0.5
        coords.append((x0 + nx * (x1 - x0), y0 + ny * (y1 - y0)))
    return coords


def _build_geometry_body(
    rec: dict[str, Any],
    refs: HuaweiReferenceTemplates,
    sx: float,
) -> tuple[bytes, int, bool]:
    c = rec.get("c", {})
    jt = int(c.get("a", -1))
    subtype = int(c.get("b", -1))
    shape_code = J_GEOMETRY_TO_HW_SHAPE.get((jt, subtype))

    if shape_code is None:
        # 未知几何子类型：将可见的 k[] 路径保留为圆珠笔笔迹。
        # 结果仍可编辑，但不宣称为原生几何图形。
        pseudo = {"c": dict(c)}
        pseudo["c"]["a"] = 1
        body, count = _build_normal_body(pseudo, refs, sx)
        style = bytearray(body[:108])
        style[84:88] = f32be(float(c.get("d", 3.0)) / 3.0)
        body = bytes(style) + body[108:]
        return body, count, False

    refs.require_shapes([shape_code])
    tpl = refs.shape_templates[shape_code]
    count = tpl.count
    style = bytearray(tpl.style)
    ph = bytearray(tpl.point_header)

    style[0:4] = f32be(float(count - 1))
    style[56:60] = u32be(2)  # 华为原生图形使用圆珠笔渲染器
    _write_huawei_bgr(style, c)
    style[76:80] = f32be(1.0)
    style[80:84] = f32be(1.0)
    style[84:88] = f32be(float(c.get("d", 3.0)) / 3.0)
    ph[4:8] = u32be(count)

    k = c.get("k") or []
    if shape_code == 0:
        l = c.get("l") or []
        if len(l) >= 2:
            coords = [
                (float(l[0].get("x", 0.0)) * sx, float(l[0].get("y", 0.0)) * sx),
                (float(l[-1].get("x", 0.0)) * sx, float(l[-1].get("y", 0.0)) * sx),
            ]
        elif k:
            coords = [
                (float(k[0].get("x", 0.0)) * sx, float(k[0].get("y", 0.0)) * sx),
                (float(k[-1].get("x", 0.0)) * sx, float(k[-1].get("y", 0.0)) * sx),
            ]
        else:
            coords = [(0.0, 0.0), (0.0, 0.0)]
    elif shape_code == 7:
        xs = [float(p.get("x", 0.0)) * sx for p in k] or [0.0]
        ys = [float(p.get("y", 0.0)) * sx for p in k] or [0.0]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        coords = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
    elif shape_code == 10:
        coords = _circle_affine_coords(tpl, k, sx)
    else:  # shape_code == 16 curve
        coords = [(x * sx, y * sx) for x, y in _resample_xy(k, count)]

    if len(coords) != count:
        raise ValueError(f"图形点数与 shape_code={shape_code} 不匹配")

    body = bytearray(style)
    body.extend(ph)
    for proto, (x, y) in zip(tpl.points, coords):
        pb = bytearray(proto)
        pb[4:8] = f32be(x)
        pb[8:12] = f32be(y)
        pb[16:20] = f32be(1.0)
        body.extend(pb)
    return bytes(body), count, True


def build_pencilengine(
    strokes: list[dict[str, Any]],
    refs: HuaweiReferenceTemplates,
    sx: float,
) -> tuple[bytes, dict[str, int]]:
    """从 Jnotes 笔迹对象构建带链接的 PENCILENGINE 文件。"""
    convertible = [r for r in strokes if int(r.get("c", {}).get("a", -1)) != 10]
    if not convertible:
        raise ValueError("没有可转换的手写笔迹")

    bodies: list[bytes] = []
    counts: list[int] = []
    ids: list[bytes] = []
    stats = {"normal": 0, "geometry": 0, "geometryFallback": 0, "paperTapeSkipped": len(strokes) - len(convertible)}

    for rec in convertible:
        jt = int(rec.get("c", {}).get("a", -1))
        if jt in (6, 7):
            body, count, native = _build_geometry_body(rec, refs, sx)
            stats["geometry" if native else "geometryFallback"] += 1
        else:
            body, count = _build_normal_body(rec, refs, sx)
            stats["normal"] += 1
        bodies.append(body)
        counts.append(count)
        ids.append(uuid.uuid4().bytes)

    header = bytearray(refs.header)
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
    root_seq = struct.unpack_from(">I", refs.header, 188)[0] or 162_474_429
    header[188:192] = u32be(root_seq)
    header[192:196] = u32be(0)

    body = bytearray()
    seq = root_seq + 1
    for i in range(len(bodies) - 1):
        body.extend(bodies[i])
        body.extend(_normal_tail(counts[i], counts[i + 1], ids[i], seq))
        seq += 1
    body.extend(bodies[-1])
    body.extend(_end_tail(counts[-1], ids[-1]))

    total_len = len(header) + len(body) + len(refs.trailer)
    header[88:92] = u32be(total_len - 124)
    header[116:120] = u32be(total_len - 196)
    result = bytes(header) + bytes(body) + refs.trailer

    # 结构自检：捕获早期实验文件只显示第一条笔迹的根链接/后续计数错误。
    blocks = _parse_normal_pencilengine(result)
    if len(blocks) != len(bodies):
        raise AssertionError("PENCILENGINE 笔迹数量验证失败")
    if struct.unpack_from(">I", result, 148)[0] != counts[0] * 36 + 140:
        raise AssertionError("PENCILENGINE 根指针 A 验证失败")
    if struct.unpack_from(">I", result, 180)[0] != counts[0] * 36 + 20:
        raise AssertionError("PENCILENGINE 根指针 B 验证失败")
    for i in range(len(blocks) - 1):
        pe = blocks[i][4]
        nc = blocks[i + 1][2]
        if struct.unpack_from(">I", result, pe + 16)[0] != nc * 36 + 140:
            raise AssertionError("PENCILENGINE 后续指针 A 验证失败")
        if struct.unpack_from(">I", result, pe + 48)[0] != nc * 36 + 20:
            raise AssertionError("PENCILENGINE 后续指针 B 验证失败")
    return result, stats


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
        if name.startswith(stem) and (data.startswith(b"\xff\xd8\xff") or data.startswith(b"\x89PNG")):
            return data
    return None


def file_info(name: str, data: bytes) -> dict[str, str]:
    return {"name": name, "hash": sha256_hex(data, True)}


def detail_map(files: dict[str, bytes]) -> str:
    m = {name: [file_info(name, data)] for name, data in files.items()}
    return json.dumps(m, ensure_ascii=False, separators=(",", ":"))


def render_thumbnail(
    jn: JNote,
    page: dict[str, Any],
    strokes: list[dict[str, Any]],
    images: list[tuple[dict[str, Any], bytes]],
    texts: list[dict[str, Any]],
    cover: bytes | None,
    out_w: int = 300,
) -> bytes:
    ratio = jn.width / jn.height
    out_h = max(1, round(out_w / ratio))
    im = Image.new("RGB", (out_w, out_h), "white")
    draw = ImageDraw.Draw(im, "RGBA")

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
        xy = [(float(p.get("x", 0)) / jn.width * out_w, float(p.get("y", 0)) / jn.height * out_h) for p in pts]
        wd = max(1, round(float(c.get("d", 3)) * out_w / jn.width))
        draw.line(xy, fill=(r, g, b, a), width=wd, joint="curve")

    for t in texts:
        x = round(float(t.get("x", 0)) / jn.width * out_w)
        y = round(float(t.get("y", 0)) / jn.height * out_h)
        draw.text((x, y), str(t.get("e", ""))[:100], fill=(0, 0, 0, 255))

    bio = io.BytesIO()
    im.save(bio, "JPEG", quality=75, optimize=True)
    return bio.getvalue()


def convert(
    jnotes_path: Path,
    normal_reference_hinote: Path,
    output: Path,
    shape_reference_hinote: Path | None = None,
    page_limit: int | None = None,
) -> dict[str, Any]:
    """将 `.Jnotes` 笔记转换为华为 `.hinote` 压缩包。"""
    jn = parse_jnotes(jnotes_path)
    refs = HuaweiReferenceTemplates(normal_reference_hinote, shape_reference_hinote)
    pages_src = jn.pages[:page_limit] if page_limit else jn.pages
    if not pages_src:
        raise ValueError("源笔记没有页面")

    # 如果存在受支持的几何图形但缺少原生图形参考文件，则尽早失败。
    required_shapes: set[int] = set()
    for p in pages_src:
        pid = str(p.get("a"))
        for rec in jn.strokes.get(pid, []):
            c = rec.get("c", {})
            code = J_GEOMETRY_TO_HW_SHAPE.get((int(c.get("a", -1)), int(c.get("b", -1))))
            if code is not None:
                required_shapes.add(code)
    if required_shapes:
        refs.require_shapes(required_shapes)

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
            bin_data, pstats = build_pencilengine(page_strokes, refs, sx)
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

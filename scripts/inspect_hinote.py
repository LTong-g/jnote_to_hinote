#!/usr/bin/env python3
from __future__ import annotations

import argparse
import collections
import gzip
import json
import struct
import zipfile
from pathlib import Path


def inspect_bin(data: bytes):
    n = struct.unpack_from(">I", data, 112)[0]
    pos = 196
    rows = []
    for i in range(n):
        ph = pos + 108
        try:
            prefix, count, stride, reserved = struct.unpack_from(">IIII", data, ph)
        except struct.error:
            break
        if prefix not in (0, 2) or stride != 36 or reserved != 0 or count < 2:
            break
        pen = struct.unpack_from(">I", data, pos + 56)[0]
        shape = struct.unpack_from(">I", data, pos + 8)[0]
        width = struct.unpack_from(">f", data, pos + 84)[0]
        rows.append((i + 1, pen, shape, count, width))
        pos = ph + 16 + count * 36 + 64
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description="检查 .hinote 中的华为 PENCILENGINE 记录")
    ap.add_argument("input", type=Path)
    args = ap.parse_args()

    pens = collections.Counter()
    shapes = collections.Counter()
    bins = 0
    pdf_files = []
    pdf_pages = []
    with zipfile.ZipFile(args.input) as z:
        names = z.namelist()
        pdf_files = [name for name in names if name.startswith("files/") and name.endswith("_pdf")]
        top_names = [
            name for name in names
            if name.endswith(".jhinote") and "/" not in name and name != "custom_md.jhinote"
        ]
        pdf_attachment_ids = set()
        if len(top_names) == 1:
            top = json.loads(gzip.decompress(z.read(top_names[0])))
            pdf_attachment_ids = {
                str(item.get("id"))
                for item in top.get("customNoteContent", {}).get("attachment", [])
                if item.get("attachType") == 3
            }
        for name in names:
            if not name.startswith("pages/"):
                continue
            page = json.loads(gzip.decompress(z.read(name))).get("customNotePageContent", {})
            if page.get("bkgAttachmentId") or page.get("bkgAttachmentIndex"):
                pdf_pages.append({
                    "page": page.get("pageNumber"),
                    "attachmentId": page.get("bkgAttachmentId"),
                    "pdfPageIndex": page.get("bkgAttachmentIndex"),
                })
        for name in z.namelist():
            if not (name.startswith("files/") and name.endswith(".bin")):
                continue
            bins += 1
            data = z.read(name)
            try:
                rows = inspect_bin(data)
            except Exception as exc:  # noqa: BLE001 - inspection continues after any malformed archive entry
                print(f"{name}：解析失败：{exc}")
                continue
            print(f"{name}：{len(rows)} 条笔迹主体")
            for _, pen, shape, count, width in rows:
                pens[pen] += 1
                if pen == 2 and shape != 0xFFFFFFFF:
                    shapes[shape] += 1
            print("  示例：", rows[:12])

    print("PENCILENGINE 文件数：", bins)
    print("pen_type 数量：", dict(sorted(pens.items())))
    print("图形代码数量：", dict(sorted(shapes.items())))
    print("PDF 文件数：", len(pdf_files))
    print("PDF 顶层附件数：", len(pdf_attachment_ids))
    print("PDF 背景页面数：", len(pdf_pages))
    if pdf_pages:
        pdf_pages.sort(key=lambda item: int(item.get("page") or 0))
        print("PDF 页面索引：", [item["pdfPageIndex"] for item in pdf_pages])


if __name__ == "__main__":
    main()

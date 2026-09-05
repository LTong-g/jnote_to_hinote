#!/usr/bin/env python3
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

from jnotes2hinote.current_core import parse_jnotes_with_info


def main() -> None:
    ap = argparse.ArgumentParser(description="检查 Jnotes 压缩包，但不执行转换")
    ap.add_argument("input", type=Path)
    args = ap.parse_args()

    jn, container = parse_jnotes_with_info(args.input)
    pdf_records = [record for record in jn.records if record.typ == "PDF"]
    pdf_names = {
        str(record.object_id).replace("\\", "/").rsplit("/", 1)[-1].casefold()
        for record in pdf_records
    }
    pdf_refs = collections.Counter(
        str(page.get("e", "")).replace("\\", "/").rsplit("/", 1)[-1].casefold()
        for page in jn.pages
        if str(page.get("e", "")).strip()
    )
    pen_types = collections.Counter()
    geometry = collections.Counter()
    paper_tape = 0
    total = 0
    for p in jn.pages:
        pid = str(p.get("a"))
        for rec in jn.strokes.get(pid, []):
            c = rec.get("c", {})
            t = int(c.get("a", -1))
            b = int(c.get("b", -1))
            total += 1
            pen_types[t] += 1
            if t in (6, 7):
                geometry[(t, b)] += 1
            if t == 10:
                paper_tape += 1

    print(json.dumps({
        "标题": jn.title,
        "数据入口": container.entry_name,
        "内层版本": container.stream_version,
        "内层字节数": container.stream_size,
        "尾部已识别": container.footer_recognized,
        "页数": len(jn.pages),
        "记录数": len(jn.records),
        "笔迹对象数": total,
        "笔迹类型": dict(sorted(pen_types.items())),
        "几何子类型": {f"{k[0]}:{k[1]}": v for k, v in sorted(geometry.items())},
        "图片数": sum(len(v) for v in jn.images.values()),
        "文本框数": sum(len(v) for v in jn.texts.values()),
        "音频记录数": len(jn.audio_records),
        "纸胶带对象数": paper_tape,
        "PDF记录数": len(pdf_records),
        "PDF页面引用数": sum(pdf_refs.values()),
        "PDF文件": [
            {
                "对象": str(record.object_id),
                "字节数": len(record.payload),
                "文件头正确": record.payload.startswith(b"%PDF-"),
                "页面引用数": pdf_refs.get(
                    str(record.object_id).replace("\\", "/").rsplit("/", 1)[-1].casefold(),
                    0,
                ),
            }
            for record in pdf_records
        ],
        "未匹配PDF引用数": sum(count for key, count in pdf_refs.items() if key not in pdf_names),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

from jnotes2hinote.converter_v1_0_0 import parse_jnotes


def main() -> None:
    ap = argparse.ArgumentParser(description="检查 Jnotes 压缩包，但不执行转换")
    ap.add_argument("input", type=Path)
    args = ap.parse_args()

    jn = parse_jnotes(args.input)
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
        "页数": len(jn.pages),
        "记录数": len(jn.records),
        "笔迹对象数": total,
        "笔迹类型": dict(sorted(pen_types.items())),
        "几何子类型": {f"{k[0]}:{k[1]}": v for k, v in sorted(geometry.items())},
        "图片数": sum(len(v) for v in jn.images.values()),
        "文本框数": sum(len(v) for v in jn.texts.values()),
        "音频记录数": len(jn.audio_records),
        "纸胶带对象数": paper_tape,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

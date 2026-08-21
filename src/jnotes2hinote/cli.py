from __future__ import annotations

import argparse
import json
from pathlib import Path

from .converter_v1_0_0 import convert


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="jnotes2hinote",
        description="将 Jideos 云记 .Jnotes 笔记转换为华为笔记 .hinote。",
    )
    p.add_argument("input", type=Path, help="输入的 .Jnotes 文件")
    p.add_argument("output", type=Path, help="输出的 .hinote 文件")
    p.add_argument(
        "--reference-hinote",
        type=Path,
        required=True,
        help="用户自己的华为 .hinote 文件，包含 pen_type 1/2/3/5 示例",
    )
    p.add_argument(
        "--shape-reference-hinote",
        type=Path,
        default=None,
        help="用户自己的华为 .hinote 文件，包含原生直线/曲线/矩形/圆图形；源文件包含支持的 type 6/7 几何图形时必需",
    )
    p.add_argument("--pages", type=int, default=0, help="只转换前 N 页；0 = 全部")
    p.add_argument("--report", type=Path, default=None, help="写入 JSON 转换报告")
    return p


def main() -> None:
    args = build_parser().parse_args()
    result = convert(
        args.input,
        args.reference_hinote,
        args.output,
        shape_reference_hinote=args.shape_reference_hinote,
        page_limit=args.pages or None,
    )
    text = json.dumps(result, ensure_ascii=False, indent=2)
    print(text)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()

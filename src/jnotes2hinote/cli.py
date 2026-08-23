from __future__ import annotations

import argparse
import json
from pathlib import Path

from .converter_v1_1_1 import convert


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="jnotes2hinote",
        description="将 Jideos 云记 .Jnotes 笔记转换为华为笔记 .hinote。",
    )
    p.add_argument("input", type=Path, help="输入的 .Jnotes 文件")
    p.add_argument("output", type=Path, help="输出的 .hinote 文件")
    p.add_argument("--pages", type=int, default=0, help="只转换前 N 页；0 = 全部")
    p.add_argument("--report", type=Path, default=None, help="写入 JSON 转换报告")
    return p


def main() -> None:
    args = build_parser().parse_args()
    result = convert(
        args.input,
        args.output,
        page_limit=args.pages or None,
    )
    text = json.dumps(result, ensure_ascii=False, indent=2)
    print(text)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()

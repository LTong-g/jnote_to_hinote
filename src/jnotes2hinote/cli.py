from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .batch import (
    CONFLICT_RENAME,
    collect_input_files,
    convert_batch,
    plan_output_paths,
)
from .converter_v1_1_1 import convert


def non_negative_int(value: str) -> int:
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("必须是大于等于 0 的整数")
    return number


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="jnotes2hinote",
        description="将一个或多个 Jnotes 文件转换为华为笔记 .hinote 文件。",
        epilog=(
            "单文件用法：jnotes2hinote input.Jnotes output.hinote；"
            "批量用法：jnotes2hinote 输入路径... 输出目录。"
        ),
    )
    p.add_argument(
        "inputs",
        nargs="+",
        type=Path,
        help="输入的 .Jnotes/.jnote 文件、目录或每行一个路径的 .txt 清单",
    )
    p.add_argument("output", type=Path, help="单文件输出的 .hinote 路径，或批量输出目录")
    p.add_argument("-r", "--recursive", action="store_true", help="递归搜索输入目录中的 Jnotes 文件")
    p.add_argument("--pages", type=non_negative_int, default=0, help="每个文件只转换前 N 页；0 = 全部")
    p.add_argument("--report", type=Path, default=None, help="写入单个结果或批量汇总 JSON 报告")
    p.add_argument("--version", action="version", version=f"jnotes2hinote {__version__}")
    return p


def _write_report(report_path: Path | None, payload: dict[str, Any] | list[Any]) -> None:
    if report_path is None:
        return
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _print_json(payload: dict[str, Any] | list[Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_intermixed_args(argv)
    input_is_batch = len(args.inputs) > 1 or any(
        path.is_dir() or path.suffix.lower() == ".txt" for path in args.inputs
    )
    output_is_directory = args.output.exists() and args.output.is_dir()
    batch_mode = input_is_batch or output_is_directory

    input_files, errors = collect_input_files(args.inputs, recursive=args.recursive)

    if not batch_mode and len(input_files) == 1 and not errors:
        result = convert(input_files[0], args.output, page_limit=args.pages or None)
        _write_report(args.report, result)
        _print_json(result)
        return 0

    if not batch_mode:
        for error in errors:
            print(f"输入错误：{error['path']}：{error['error']}", file=sys.stderr)
        if not input_files:
            return 1
        print("单文件模式只能提供一个有效的 Jnotes 文件。", file=sys.stderr)
        return 1

    if args.output.exists() and not args.output.is_dir():
        print(f"批量转换的输出路径必须是目录：{args.output}", file=sys.stderr)
        return 1
    if args.output.suffix.lower() == ".hinote" and not args.output.exists():
        print("批量转换时输出参数必须是目录，而不是 .hinote 文件。", file=sys.stderr)
        return 1
    if not input_files:
        for error in errors:
            print(f"跳过：{error['path']}：{error['error']}", file=sys.stderr)
        return 1

    summary = convert_batch(
        input_files,
        args.output,
        page_limit=args.pages or None,
        recursive=args.recursive,
        conflict_strategy=CONFLICT_RENAME,
        initial_errors=errors,
    )
    _write_report(args.report, summary)
    _print_json(summary)
    for error in summary["errors"]:
        print(f"跳过：{error['path']}：{error['error']}", file=sys.stderr)
    return 0 if summary["converted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "build_parser",
    "collect_input_files",
    "main",
    "plan_output_paths",
]

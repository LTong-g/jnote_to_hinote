from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from . import __version__
from .batch import (
    CONFLICT_RENAME,
    collect_input_files,
    convert_batch,
    plan_output_paths,
)
from .converter import convert
from .reporting import redact_report


def non_negative_int(value: str) -> int:
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("必须是大于等于 0 的整数")
    return number


def build_parser(
    program: str = "jnotes2hinote",
    source_name: str = "Jnotes",
    example_input: str = "input.Jnotes",
    input_extensions: str = ".Jnotes/.jnote",
    output_suffix: str = ".hinote",
) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog=program,
        description=f"将一个或多个 {source_name} 文件转换为 {output_suffix} 文件。",
        epilog=(
            f"单文件用法：{program} {example_input} output{output_suffix}；"
            f"批量用法：{program} 输入路径... 输出目录。"
        ),
    )
    p.add_argument(
        "inputs",
        nargs="+",
        type=Path,
        help=f"输入的 {input_extensions} 文件、目录或每行一个路径的 .txt 清单",
    )
    p.add_argument("output", type=Path, help=f"单文件输出的 {output_suffix} 路径，或批量输出目录")
    p.add_argument("-r", "--recursive", action="store_true", help=f"递归搜索输入目录中的 {source_name} 文件")
    p.add_argument("--pages", type=non_negative_int, default=0, help="每个文件只转换前 N 页；0 = 全部")
    p.add_argument("--report", type=Path, default=None, help="写入单个结果或批量汇总 JSON 报告")
    p.add_argument(
        "--redact-report",
        action="store_true",
        help="从 JSON 输出和报告中移除笔记标题及完整路径",
    )
    p.add_argument("--debug", action="store_true", help="转换失败时显示完整 Python 异常信息")
    p.add_argument("--version", action="version", version=f"{program} {__version__}")
    return p


def _write_report(report_path: Path | None, payload: dict[str, Any] | list[Any]) -> None:
    if report_path is None:
        return
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _print_json(payload: dict[str, Any] | list[Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _error_label(error: dict[str, str]) -> str:
    return {
        "conversion_failed": "转换失败",
        "input_error": "输入错误",
        "skipped": "跳过",
    }.get(error.get("kind", ""), "错误")


def run_cli(
    argv: list[str] | None,
    *,
    parser: argparse.ArgumentParser,
    collect_files: Callable[..., Any],
    convert_file: Callable[..., dict[str, Any]],
    run_batch: Callable[..., dict[str, Any]],
    source_name: str,
    output_suffixes: set[str],
) -> int:
    args = parser.parse_intermixed_args(argv)
    input_is_batch = len(args.inputs) > 1 or any(
        path.is_dir() or path.suffix.lower() == ".txt" for path in args.inputs
    )
    output_is_directory = args.output.exists() and args.output.is_dir()
    batch_mode = input_is_batch or output_is_directory

    input_files, errors = collect_files(args.inputs, recursive=args.recursive)

    if not batch_mode and len(input_files) == 1 and not errors:
        try:
            result = convert_file(input_files[0], args.output, page_limit=args.pages or None)
        except Exception as exc:
            if args.debug:
                raise
            print(f"转换失败：{exc}", file=sys.stderr)
            return 1
        payload = redact_report(result) if args.redact_report else result
        _write_report(args.report, payload)
        _print_json(payload)
        return 0

    if not batch_mode:
        for error in errors:
            print(f"输入错误：{error['path']}：{error['error']}", file=sys.stderr)
        if not input_files:
            return 1
        print(f"单文件模式只能提供一个有效的 {source_name} 文件。", file=sys.stderr)
        return 1

    if args.output.exists() and not args.output.is_dir():
        print(f"批量转换的输出路径必须是目录：{args.output}", file=sys.stderr)
        return 1
    if args.output.suffix.casefold() in output_suffixes and not args.output.exists():
        print(f"批量转换时输出参数必须是目录，而不是 {args.output.suffix} 文件。", file=sys.stderr)
        return 1
    if not input_files:
        for error in errors:
            print(f"跳过：{error['path']}：{error['error']}", file=sys.stderr)
        return 1

    summary = run_batch(
        input_files,
        args.output,
        page_limit=args.pages or None,
        recursive=args.recursive,
        conflict_strategy=CONFLICT_RENAME,
        initial_errors=errors,
    )
    payload = redact_report(summary) if args.redact_report else summary
    _write_report(args.report, payload)
    _print_json(payload)
    for error in summary["errors"]:
        print(f"{_error_label(error)}：{error['path']}：{error['error']}", file=sys.stderr)
    if summary.get("cancelled"):
        return 130
    problem_count = int(summary.get("failed", 0)) + int(summary.get("inputErrors", 0))
    if problem_count:
        return 2 if summary["converted"] else 1
    return 0 if summary["converted"] else 1


def main(argv: list[str] | None = None) -> int:
    return run_cli(
        argv, parser=build_parser(), collect_files=collect_input_files, convert_file=convert, run_batch=convert_batch,
        source_name="Jnotes", output_suffixes={".hinote"},
    )


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "build_parser",
    "collect_input_files",
    "main",
    "plan_output_paths",
]

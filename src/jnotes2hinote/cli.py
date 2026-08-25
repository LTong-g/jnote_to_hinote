from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .converter_v1_1_1 import convert

JNOTES_SUFFIXES = {".jnotes", ".jnote"}


def _is_jnotes_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in JNOTES_SUFFIXES


def _clean_manifest_line(line: str) -> str:
    value = line.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1].strip()
    return value


def _record_error(errors: list[dict[str, str]], path: str, exc: Exception) -> None:
    errors.append({"path": path, "error": str(exc) or exc.__class__.__name__})


def collect_input_files(
    input_paths: list[Path],
    *,
    recursive: bool = False,
) -> tuple[list[Path], list[dict[str, str]]]:
    """Collect Jnotes files from files, directories and text path lists.

    Directory traversal is one level deep by default. A text list uses paths
    relative to the text file's own directory; blank lines and lines beginning
    with ``#`` are ignored. Invalid paths are returned as errors so callers can
    continue with the remaining inputs.
    """

    files: list[Path] = []
    errors: list[dict[str, str]] = []
    seen: set[Path] = set()

    def add_file(path: Path) -> None:
        if not _is_jnotes_file(path):
            raise ValueError(f"不是受支持的 Jnotes 文件：{path}")
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            files.append(resolved)

    def visit(path: Path, label: str) -> None:
        path = path.expanduser()
        if path.is_file():
            if path.suffix.lower() == ".txt":
                listed = 0
                for line_number, raw_line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
                    value = _clean_manifest_line(raw_line)
                    if not value or value.startswith("#"):
                        continue
                    listed += 1
                    listed_path = Path(value)
                    if not listed_path.is_absolute():
                        listed_path = path.parent / listed_path
                    try:
                        visit(listed_path, f"{path}:{line_number}")
                    except Exception as exc:
                        _record_error(errors, f"{path}:{line_number}", exc)
                if listed == 0:
                    raise ValueError(f"路径清单为空：{path}")
                return
            add_file(path)
            return

        if path.is_dir():
            candidates = path.rglob("*") if recursive else path.iterdir()
            jnotes_files = sorted(
                (candidate for candidate in candidates if _is_jnotes_file(candidate)),
                key=lambda candidate: str(candidate).casefold(),
            )
            if not jnotes_files:
                level = "及其子目录" if recursive else "的直接子级"
                raise ValueError(f"目录{level}中没有 Jnotes 文件：{path}")
            for candidate in jnotes_files:
                add_file(candidate)
            return

        raise FileNotFoundError(f"输入路径不存在：{path}")

    for input_path in input_paths:
        try:
            visit(input_path, str(input_path))
        except Exception as exc:
            _record_error(errors, str(input_path), exc)

    return files, errors


def plan_output_paths(input_files: list[Path], output_dir: Path) -> dict[Path, Path]:
    """Plan flat batch output names and disambiguate duplicate stems."""

    planned: dict[Path, Path] = {}
    used_names: set[str] = set()
    for input_file in input_files:
        stem = input_file.stem or "output"
        name = f"{stem}.hinote"
        index = 2
        while name.casefold() in used_names:
            name = f"{stem}_{index}.hinote"
            index += 1
        used_names.add(name.casefold())
        planned[input_file] = output_dir / name
    return planned


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


def _write_report(report_path: Path | None, payload: dict | list) -> None:
    if report_path is None:
        return
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _print_json(payload: dict | list) -> None:
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

    args.output.mkdir(parents=True, exist_ok=True)
    output_paths = plan_output_paths(input_files, args.output)
    results: list[dict] = []
    for input_file in input_files:
        output_file = output_paths[input_file]
        try:
            results.append(convert(input_file, output_file, page_limit=args.pages or None))
        except Exception as exc:
            _record_error(errors, str(input_file), exc)

    summary = {
        "mode": "batch",
        "recursive": args.recursive,
        "outputDirectory": str(args.output),
        "converted": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors,
    }
    _write_report(args.report, summary)
    _print_json(summary)
    for error in errors:
        print(f"跳过：{error['path']}：{error['error']}", file=sys.stderr)
    return 0 if results else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""共享的批量输入、输出规划和转换执行逻辑。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import Any, Callable

from .current_core import convert

JNOTES_SUFFIXES = {".jnotes", ".jnote"}
CONFLICT_RENAME = "rename"
CONFLICT_SKIP = "skip"
CONFLICT_OVERWRITE = "overwrite"
CONFLICT_STRATEGIES = {CONFLICT_RENAME, CONFLICT_SKIP, CONFLICT_OVERWRITE}


@dataclass(frozen=True)
class BatchProgress:
    """A single progress update emitted while converting a batch."""

    index: int
    total: int
    source: Path
    output: Path | None
    status: str
    result: dict[str, Any] | None = None
    error: str | None = None


ProgressCallback = Callable[[BatchProgress], None]


def is_jnotes_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in JNOTES_SUFFIXES


def clean_manifest_line(line: str) -> str:
    value = line.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1].strip()
    return value


def record_error(errors: list[dict[str, str]], path: str, exc: Exception | str) -> None:
    if isinstance(exc, str):
        message = exc
    else:
        message = str(exc) or exc.__class__.__name__
    errors.append({"path": path, "error": message})


def collect_input_files(
    input_paths: list[Path],
    *,
    recursive: bool = False,
    source_counts: dict[str, int] | None = None,
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

    def add_file(path: Path, origin: str) -> None:
        if not is_jnotes_file(path):
            raise ValueError(f"不是受支持的 Jnotes 文件：{path}")
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            files.append(resolved)
            if source_counts is not None:
                source_counts[origin] = source_counts.get(origin, 0) + 1

    def visit(path: Path, origin: str) -> None:
        path = path.expanduser()
        if path.is_file():
            if path.suffix.lower() == ".txt":
                listed = 0
                for line_number, raw_line in enumerate(
                    path.read_text(encoding="utf-8-sig").splitlines(),
                    start=1,
                ):
                    value = clean_manifest_line(raw_line)
                    if not value or value.startswith("#"):
                        continue
                    listed += 1
                    listed_path = Path(value)
                    if not listed_path.is_absolute():
                        listed_path = path.parent / listed_path
                    try:
                        visit(listed_path, origin)
                    except Exception as exc:
                        record_error(errors, f"{path}:{line_number}", exc)
                if listed == 0:
                    raise ValueError(f"路径清单为空：{path}")
                return
            add_file(path, origin)
            return

        if path.is_dir():
            candidates = path.rglob("*") if recursive else path.iterdir()
            jnotes_files = sorted(
                (candidate for candidate in candidates if is_jnotes_file(candidate)),
                key=lambda candidate: str(candidate).casefold(),
            )
            if not jnotes_files:
                level = "及其子目录" if recursive else "的直接子级"
                raise ValueError(f"目录{level}中没有 Jnotes 文件：{path}")
            for candidate in jnotes_files:
                add_file(candidate, origin)
            return

        raise FileNotFoundError(f"输入路径不存在：{path}")

    for input_path in input_paths:
        try:
            visit(input_path, str(input_path))
        except Exception as exc:
            record_error(errors, str(input_path), exc)

    return files, errors


def _next_name(stem: str, used_names: set[str]) -> str:
    name = f"{stem}.hinote"
    index = 2
    while name.casefold() in used_names:
        name = f"{stem}_{index}.hinote"
        index += 1
    return name


def plan_output_paths(
    input_files: list[Path],
    output_dir: Path,
    *,
    conflict_strategy: str = CONFLICT_RENAME,
) -> dict[Path, Path | None]:
    """Plan flat output names and handle existing or duplicate names.

    ``rename`` appends a numeric suffix, ``skip`` leaves an existing or
    duplicated destination unplanned, and ``overwrite`` replaces existing
    files while still disambiguating duplicate inputs in the same batch.
    """

    if conflict_strategy not in CONFLICT_STRATEGIES:
        raise ValueError(f"未知的文件重名策略：{conflict_strategy}")

    planned: dict[Path, Path | None] = {}
    used_names: set[str] = set()
    existing_names = (
        {
            child.name.casefold()
            for child in output_dir.iterdir()
        }
        if output_dir.exists() and output_dir.is_dir()
        else set()
    )

    for input_file in input_files:
        stem = input_file.stem or "output"
        desired = f"{stem}.hinote"
        desired_key = desired.casefold()

        if conflict_strategy == CONFLICT_SKIP and (desired_key in existing_names or desired_key in used_names):
            planned[input_file] = None
            continue

        if conflict_strategy == CONFLICT_RENAME:
            name = _next_name(stem, existing_names | used_names)
        elif desired_key in used_names:
            name = _next_name(stem, used_names)
        else:
            name = desired

        used_names.add(name.casefold())
        planned[input_file] = output_dir / name

    return planned


def convert_batch(
    input_files: list[Path],
    output_dir: Path,
    *,
    page_limit: int | None = None,
    recursive: bool = False,
    conflict_strategy: str = CONFLICT_RENAME,
    initial_errors: list[dict[str, str]] | None = None,
    progress_callback: ProgressCallback | None = None,
    cancel_event: Event | None = None,
) -> dict[str, Any]:
    """Convert files sequentially and continue after per-file failures."""

    errors = list(initial_errors or [])
    results: list[dict[str, Any]] = []
    output_dir.mkdir(parents=True, exist_ok=True)
    output_paths = plan_output_paths(
        input_files,
        output_dir,
        conflict_strategy=conflict_strategy,
    )
    total = len(input_files)
    cancelled = False

    for index, input_file in enumerate(input_files, start=1):
        if cancel_event is not None and cancel_event.is_set():
            cancelled = True
            break

        output_file = output_paths[input_file]
        if output_file is None:
            message = "输出文件已存在，已跳过"
            record_error(errors, str(input_file), message)
            if progress_callback:
                progress_callback(BatchProgress(index, total, input_file, None, "skipped", error=message))
            continue

        try:
            result = convert(input_file, output_file, page_limit=page_limit)
        except Exception as exc:
            record_error(errors, str(input_file), exc)
            if progress_callback:
                progress_callback(BatchProgress(index, total, input_file, output_file, "failed", error=str(exc)))
            continue

        results.append(result)
        if progress_callback:
            progress_callback(BatchProgress(index, total, input_file, output_file, "converted", result=result))

    summary = {
        "mode": "batch",
        "recursive": recursive,
        "outputDirectory": str(output_dir),
        "conflictStrategy": conflict_strategy,
        "total": total,
        "converted": len(results),
        "failed": len(errors),
        "cancelled": cancelled,
        "results": results,
        "errors": errors,
    }
    return summary

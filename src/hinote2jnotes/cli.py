"""Command-line entry point for converting Huawei Notes to Jnotes."""

import argparse

from jnotes2hinote import cli

from .batch import collect_input_files, convert_batch
from .converter import convert
from .writer import OUTPUT_SUFFIX, OUTPUT_SUFFIXES


def build_parser() -> argparse.ArgumentParser:
    return cli.build_parser("hinote2jnotes", "华为笔记", "input.hinote", ".hinote/.hjnote", OUTPUT_SUFFIX)


def main(argv: list[str] | None = None) -> int:
    return cli.run_cli(
        argv, parser=build_parser(), collect_files=collect_input_files, convert_file=convert, run_batch=convert_batch,
        source_name="华为笔记", output_suffixes=OUTPUT_SUFFIXES,
    )


if __name__ == "__main__":
    raise SystemExit(main())

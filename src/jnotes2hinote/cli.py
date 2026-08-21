from __future__ import annotations

import argparse
import json
from pathlib import Path

from .converter_v1_0_0 import convert


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="jnotes2hinote",
        description="Convert Jideos Jnotes .Jnotes notebooks to Huawei Notes .hinote.",
    )
    p.add_argument("input", type=Path, help="Input .Jnotes file")
    p.add_argument("output", type=Path, help="Output .hinote file")
    p.add_argument(
        "--reference-hinote",
        type=Path,
        required=True,
        help="User-owned Huawei .hinote containing pen_type 1/2/3/5 examples",
    )
    p.add_argument(
        "--shape-reference-hinote",
        type=Path,
        default=None,
        help="User-owned Huawei .hinote containing native line/curve/rectangle/circle shapes; required when the source contains supported type 6/7 geometry",
    )
    p.add_argument("--pages", type=int, default=0, help="Convert only the first N pages; 0 = all")
    p.add_argument("--report", type=Path, default=None, help="Write a JSON conversion report")
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

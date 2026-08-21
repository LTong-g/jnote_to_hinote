#!/usr/bin/env python3
from __future__ import annotations

import argparse
import collections
import struct
import zipfile
from pathlib import Path


def inspect_bin(data: bytes):
    n = struct.unpack_from(">I", data, 112)[0]
    pos = 196
    rows = []
    for i in range(n):
        ph = pos + 108
        try:
            prefix, count, stride, reserved = struct.unpack_from(">IIII", data, ph)
        except struct.error:
            break
        if prefix not in (0, 2) or stride != 36 or reserved != 0 or count < 2:
            break
        pen = struct.unpack_from(">I", data, pos + 56)[0]
        shape = struct.unpack_from(">I", data, pos + 8)[0]
        width = struct.unpack_from(">f", data, pos + 84)[0]
        rows.append((i + 1, pen, shape, count, width))
        pos = ph + 16 + count * 36 + 64
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description="Inspect Huawei PENCILENGINE records in a .hinote")
    ap.add_argument("input", type=Path)
    args = ap.parse_args()

    pens = collections.Counter()
    shapes = collections.Counter()
    bins = 0
    with zipfile.ZipFile(args.input) as z:
        for name in z.namelist():
            if not (name.startswith("files/") and name.endswith(".bin")):
                continue
            bins += 1
            data = z.read(name)
            try:
                rows = inspect_bin(data)
            except Exception as exc:
                print(f"{name}: parse failed: {exc}")
                continue
            print(f"{name}: {len(rows)} stroke bodies")
            for _, pen, shape, count, width in rows:
                pens[pen] += 1
                if pen == 2 and shape != 0xFFFFFFFF:
                    shapes[shape] += 1
            print("  sample:", rows[:12])

    print("PENCILENGINE files:", bins)
    print("pen_type counts:", dict(sorted(pens.items())))
    print("shape-code counts:", dict(sorted(shapes.items())))


if __name__ == "__main__":
    main()

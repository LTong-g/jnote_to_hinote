#!/usr/bin/env python3
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

from jnotes2hinote.converter_v1_0_0 import parse_jnotes


def main() -> None:
    ap = argparse.ArgumentParser(description="Inspect a Jnotes archive without converting it")
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
        "title": jn.title,
        "pages": len(jn.pages),
        "records": len(jn.records),
        "strokeObjects": total,
        "strokeTypes": dict(sorted(pen_types.items())),
        "geometrySubtypes": {f"{k[0]}:{k[1]}": v for k, v in sorted(geometry.items())},
        "images": sum(len(v) for v in jn.images.values()),
        "textBoxes": sum(len(v) for v in jn.texts.values()),
        "audioRecords": len(jn.audio_records),
        "paperTapeObjects": paper_tape,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

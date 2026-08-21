# Huawei `.hinote` / PENCILENGINE format notes

These notes describe structures device-tested with **Huawei Notes 15.0.14.295**.

## `.hinote` archive

A `.hinote` export is a ZIP archive containing:

```text
<note-id>.jhinote
pages/<page-id>.jhinote
files/*
custom_md.jhinote
```

`.jhinote` payloads are GZIP-compressed JSON.

Handwriting lives in `files/*.bin` PENCILENGINE files.

## PENCILENGINE layout used by v15.0.14.295

The tested normal handwriting files use:

```text
196-byte file header

repeat for each stroke:
    108-byte Style Record
    16-byte Point Table Header
    N × 36-byte Point Data
    64-byte link/tail

12-byte trailer
```

This is newer/different from older public parsers that assume a shorter style record.

## Point data

For the tested 36-byte point stride:

| Offset from point | Type | Meaning |
|---:|---|---|
| +4 | big-endian float | x |
| +8 | big-endian float | y |
| +16 | big-endian float | pressure |

## Style record fields used by v1.0.0

| Offset | Meaning in tested files |
|---:|---|
| +8 | sentinel for ordinary ink; also shape code in native geometry records |
| +56 | `pen_type` |
| +64 | B color float |
| +68 | G color float |
| +72 | R color float |
| +76 | effective/render opacity for tested highlighter |
| +80 | selection/UI opacity for tested highlighter |
| +84 | width/base-width field |

### Color order

Huawei Notes 15.0.14.295 stores the tested stroke RGB channels as **B, G, R**, not R, G, B.

For source color `#364C7E`, v1.0.0 writes approximately:

```text
+64 = 0x7E / 255
+68 = 0x4C / 255
+72 = 0x36 / 255
```

## Pen types observed

| Huawei `pen_type` | Tool |
|---:|---|
| 1 | Fountain/steel pen |
| 2 | Ballpoint |
| 3 | HB pencil |
| 4 | Marker |
| 5 | Highlighter |
| 11 | 2B pencil |
| 12 | Xiuli / calligraphy pen |
| 13 | Brush |

v1.0.0 only needs 1/2/3/5 for the tested source notebook, plus ballpoint-rendered native geometry.

## Linked-list structure

A key reverse-engineering result is that the 196-byte header acts like a root link into stroke 1, and each 64-byte stroke tail links to the next stroke.

For a normal continuation tail:

```text
tail + 16 = next_point_count × 36 + 140
tail + 48 = next_point_count × 36 + 20
```

The converter rebuilds these values for every generated stroke.

### Header → first stroke

Equivalent root fields include:

```text
header + 136 = 48
header + 144 = 65538
header + 148 = first_point_count × 36 + 140
header + 168 = 68
header + 172 = 52
header + 176 = 120
header + 180 = first_point_count × 36 + 20
```

A UUID-like 16-byte field is stored at `header+152..167`, and a sequence-like value is stored at `header+188` in the tested layout.

Failure to rebuild the header root pointer produced files where each page displayed only its first stroke during experimentation.

## END tail

The last stroke uses a distinct END layout rather than a normal continuation tail. v1.0.0 writes one END record per PENCILENGINE page.

## Native geometry

Huawei geometry-tool output is also stored inside PENCILENGINE. Controlled samples showed geometry records using ballpoint rendering (`pen_type=2`) with compact canonical point sets, for example:

| Huawei shape code | Tested geometry | Typical count in reference |
|---:|---|---:|
| 0 | Straight line | 2 |
| 7 | Rectangle | 5 |
| 10 | Circle / ellipse | 361 |
| 16 | Curve | 101 |

Some native-shape pages also include an extended UUID index after the final stroke. A/B device testing found no user-visible selection/transform behavior difference when that index was omitted, so v1.0.0 does not require it.

## SHA-256 metadata

Observed checksum behavior uses ordinary SHA-256:

- `fileMdStr`: uppercase SHA-256 of file content;
- `fileNameMdStr`: lowercase SHA-256 of the basename string.

Page metadata also carries a `detailFileMap` containing file hashes.

# Jnotes `.Jnotes` format notes

These notes describe the structures observed in **Jideos Jnotes / 云记 3.2.3.2**.

## Outer container

A `.Jnotes` file is a ZIP archive containing:

```text
zip.Jzip
```

`zip.Jzip` is a custom sequential container. Observed files begin with a Java-style UTF string:

```text
TRY
```

followed by a version integer and note UUID.

Records are then stored sequentially. The tested notebook contained record families including:

- `NOTE`
- `PAGE`
- `STROKE`
- `IMAGE`
- `TEXT`
- `COVER`
- `AUDIO_EX`

The end of the container includes a short footer containing `Lucky` in observed samples.

## Handwriting

Stroke payloads are plaintext JSON. Important observed fields inside the nested `c` object include:

| Field | Meaning |
|---|---|
| `a` | tool/object type |
| `c` | signed ARGB color integer |
| `d` | width-like internal value |
| `k[]` | sampled final path |

Each point in `k[]` contains at least x/y and pressure-like data in the tested format.

### Confirmed type mapping in controlled samples

| Jnotes `a` | Meaning |
|---:|---|
| 1 | Ballpoint pen |
| 2 | Fountain/steel pen |
| 3 | Highlighter |
| 5 | Pencil |
| 6 | Handwriting-recognized / regularized geometry |
| 7 | Explicit geometry-tool object |
| 10 | Paper tape |

## Type 6 geometry

Controlled samples confirmed:

- `a=6, b=0`: handwriting regularized into a straight line;
- `a=6, b=12`: handwriting regularized into a curve.

The large validated notebook also contained `a=6, b=4`, treated as an ellipse/circle-like recognized shape by v1.0.0.

`l[]` can store a small set of defining/control points while `k[]` stores the final regularized display path.

## Type 7 geometry

A controlled geometry-tool page confirmed that `a=7` means an explicit geometry-tool object, with `b` selecting a subtype. Observed Jnotes subtype values included:

| `b` | Observed shape |
|---:|---|
| 0 | Solid line |
| 1 | Dashed line |
| 3 | Rectangle |
| 4 | Circle / ellipse |
| 5 | Triangle |
| 6 | Right triangle |
| 11 | Wavy line |
| 13 | One-way arrow |
| 14 | Two-way arrow |
| 15 | Hexagon |
| 16 | Five-point star |
| 17 | Cylinder |
| 18 | Triangular prism |
| 19 | Cube |

v1.0.0 has native Huawei mappings only for the subtypes exercised by the device-tested notebook. Other subtypes fall back to editable ink-path preservation.

## Paper tape

Observed `a=10` objects have their own path and style fields. Important observations:

- width-like field `d`;
- color field `c`;
- style selector `y`;
- opaque/outline-like behavior selector `z`;
- path in `k[]`.

No Huawei native equivalent has been confirmed. v1.0.0 skips paper tape rather than pretending it is a normal pen stroke.

## Images and stickers

Jnotes image records can carry raw PNG/JPEG bytes. Controlled sticker samples were ordinary RGBA PNG images, which maps naturally to Huawei image elements.

## Audio

`AUDIO_EX` records were observed to contain raw MP3 data with metadata such as filename, duration and page geometry. The format is documented for future work, but v1.0.0 does not enable audio conversion.

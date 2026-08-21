# Jnotes → Huawei mapping rules in v1.0.0

These are the rules implemented by the frozen v1.0.0 converter core.

## Pen types

| Jnotes type | Jnotes meaning | Huawei `pen_type` |
|---:|---|---:|
| 1 | Ballpoint | 2 |
| 2 | Fountain/steel pen | 1 |
| 3 | Highlighter | 5 |
| 5 | Pencil | 3 (HB) |

## Colors

Jnotes stores signed ARGB integers. Huawei Notes 15.0.14.295 stores tested stroke color floats in BGR order:

```text
style+64 = B / 255
style+68 = G / 255
style+72 = R / 255
```

## Highlighter

Device-calibrated rules retained in v1.0.0:

```text
Huawei width = Jnotes d × 16 / 3
style+76 = min(80/255, source_alpha/255)
style+80 = min(80/255, source_alpha/255)
```

Examples from the validated notebook:

| Jnotes `d` | Huawei width |
|---:|---:|
| 3 | 16 |
| 3.68 | 19.6267 |
| 6 | 32 |

## Geometry

The tested notebook used these mappings:

| Jnotes | Meaning | Huawei shape code |
|---|---|---:|
| type 6, `b=0` | regularized straight line | 0 |
| type 6, `b=12` | regularized curve | 16 |
| type 6, `b=4` | recognized ellipse | 10 |
| type 7, `b=3` | rectangle | 7 |
| type 7, `b=4` | circle / ellipse | 10 |

Geometry is rendered using Huawei ballpoint geometry records (`pen_type=2`).

Final geometry width rule:

```text
Huawei geometry width = Jnotes d / 3
```

Unsupported type 6/type 7 subtypes are preserved as editable ballpoint-path fallback rather than being dropped.

## Paper backgrounds

Huawei templates confirmed from a controlled note:

| Huawei background | Meaning |
|---|---|
| `base1` | Blank |
| `base4` | Wide horizontal lines |
| `base5` | Narrow horizontal lines |
| `base6` | Dots |
| `base3` | Small/narrow grid |
| `base2` | Medium/wide grid |

Jnotes mapping used by v1.0.0:

- `White_Line_paper_1_Paper`, UI size 1–2 → `base5`
- `White_Line_paper_1_Paper`, UI size 3+ → `base4`
- other horizontal-line templates (including `v-narrow-line-white`) → `base4`
- `White_Graph_Paper`, UI size 1–4 → `base3`
- `White_Graph_Paper`, UI size 5+ → `base2`
- `White_Wide_Grid_Paper` → `base2`
- dotted paper → `base6`
- blank / cover underneath → `base1`

In controlled Jnotes samples, UI paper size can be derived from:

```text
UI size = horParts + 3
```

for the observed parameterized templates (`-2 → 1`, `0 → 3`, `3 → 6`).

## Images and stickers

Jnotes PNG/JPEG image bytes are copied into Huawei `files/` and referenced by `elementType=1` page elements. Image-based stickers therefore use the same mapping.

## Text

Jnotes text is mapped to Huawei `elementType=0` with HTML-like rich-text markup for the supported attributes. Font metrics and wrapping are not guaranteed to match exactly.

## Paper tape

No confirmed Huawei native object. Frozen v1.0.0 skips Jnotes type 10 paper-tape strokes and reports how many were skipped.

## Audio

Not enabled in v1.0.0.

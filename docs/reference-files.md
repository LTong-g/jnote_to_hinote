# Creating Huawei reference files

Jnotes2Hinote v1.0.0 does not bundle Huawei binary templates. Create small reference notes in **your own Huawei Notes app** and export them as `.hinote`.

The validated target version is **Huawei Notes 15.0.14.295**.

## 1. Normal pen reference

Create one note and draw at least one stroke with each of these tools:

1. Fountain/steel pen
2. Ballpoint pen
3. HB pencil
4. Highlighter

More than one stroke per tool is useful because the converter chooses a template whose point count is close to the source stroke.

Export this note as, for example:

```text
reference.hinote
```

The converter expects the exported PENCILENGINE data to contain Huawei pen types:

| Huawei pen | `pen_type` |
|---|---:|
| Fountain/steel pen | 1 |
| Ballpoint | 2 |
| HB pencil | 3 |
| Highlighter | 5 |

## 2. Shape reference

If a source Jnotes notebook contains supported type 6/type 7 geometry, create another Huawei note containing at least:

- a straight line;
- a curve;
- a rectangle;
- a circle or ellipse.

Export it as:

```text
shape-reference.hinote
```

The v1.0.0 converter uses the following Huawei shape codes:

| Geometry | Huawei shape code |
|---|---:|
| Straight line | 0 |
| Rectangle | 7 |
| Circle / ellipse | 10 |
| Curve | 16 |

## Inspecting a reference

Use:

```bash
python scripts/inspect_hinote.py reference.hinote
python scripts/inspect_hinote.py shape-reference.hinote
```

The script reports observed pen types, shape codes and point counts.

## Privacy

Use a synthetic note with no personal content. Reference files are ignored by the repository `.gitignore` and should not be committed.

# Jnotes2Hinote

Convert **Jideos Jnotes / 云记 `.Jnotes`** notebooks into **Huawei Notes / 华为笔记 `.hinote`** while preserving native editable handwriting where the reverse-engineered formats allow it.

> **Validated compatibility:** Jnotes **3.2.3.2** → Huawei Notes **15.0.14.295**. Other versions are currently unverified.

Chinese documentation: [README.zh-CN.md](README.zh-CN.md)

## What v1.0.0 preserves

- Multi-page notebook structure
- Native editable Huawei PENCILENGINE handwriting
- Stroke coordinates and per-point pressure
- Stroke color using Huawei's BGR float layout
- Ballpoint, fountain/steel pen, HB pencil and highlighter mappings used by the tested notebook
- Device-calibrated highlighter width and opacity
- Supported Jnotes type 6 / type 7 geometry as Huawei geometry-style PENCILENGINE strokes
- Images and image-based stickers
- Basic editable text boxes
- Cover images
- Huawei native paper backgrounds

## Important: reference `.hinote` files are required

The public repository intentionally does **not** bundle Huawei binary assets or personal note exports. The converter extracts structural PENCILENGINE templates from notes that **you export from your own Huawei Notes installation**.

You need:

1. `reference.hinote` — a tiny Huawei note containing examples of:
   - fountain/steel pen (`pen_type=1`)
   - ballpoint (`pen_type=2`)
   - HB pencil (`pen_type=3`)
   - highlighter (`pen_type=5`)
2. `shape-reference.hinote` — required when the source contains the supported Jnotes type 6/7 geometry. Create a Huawei note containing at least:
   - straight line
   - curve
   - rectangle
   - circle/ellipse

See [docs/reference-files.md](docs/reference-files.md).

## Installation

```bash
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\Activate.ps1
pip install -e .
```

macOS/Linux:

```bash
source .venv/bin/activate
pip install -e .
```

## Usage

```bash
jnotes2hinote input.Jnotes output.hinote \
  --reference-hinote reference.hinote \
  --shape-reference-hinote shape-reference.hinote \
  --report conversion-report.json
```

Or:

```bash
python -m jnotes2hinote input.Jnotes output.hinote \
  --reference-hinote reference.hinote \
  --shape-reference-hinote shape-reference.hinote
```

Convert only the first 5 pages while testing:

```bash
jnotes2hinote input.Jnotes test.hinote \
  --reference-hinote reference.hinote \
  --shape-reference-hinote shape-reference.hinote \
  --pages 5
```

## Known limitations

- **Paper tape:** no confirmed Huawei native equivalent; v1.0.0 skips it rather than rasterizing it silently.
- **Audio:** Jnotes audio storage and Huawei generic attachment storage were reverse-engineered, but audio conversion is not enabled in v1.0.0.
- **Typography:** text is editable, but font metrics, wrapping and line spacing may differ.
- **Pen widths:** highlighter width is device-calibrated. Ordinary pen-family visual width equivalence is not fully calibrated.
- **Compatibility:** only Jnotes 3.2.3.2 → Huawei Notes 15.0.14.295 is device-tested.

Read [docs/limitations.md](docs/limitations.md) before converting important notebooks.

## Reverse-engineering notes

The repository documents the file-format findings used by the converter:

- [Jnotes format](docs/format-jnotes.md)
- [Huawei `.hinote` / PENCILENGINE format](docs/format-hinote.md)
- [Mapping rules](docs/mapping.md)
- [Compatibility](docs/compatibility.md)
- [Reverse-engineering timeline](docs/reverse-engineering.md)
- [v1.0.0 validation summary](docs/validation-v1.0.0.md)

## Safety / backups

Always keep the original `.Jnotes` and export/backup your Huawei Notes before importing converted files. This is an unofficial interoperability project based on reverse engineering, not a Huawei or Jideos product.

## Development

```bash
pip install -e ".[dev]"
pytest
```

The v1.0.0 core is intentionally frozen in:

```text
src/jnotes2hinote/converter_v1_0_0.py
```

Future behavioral changes should use a new versioned core instead of rewriting the device-tested implementation.

## License

MIT. See [LICENSE](LICENSE).

## Disclaimer

This project is independent and unofficial. It is not affiliated with, endorsed by, or sponsored by Jideos or Huawei. Product and company names are used only to describe file-format interoperability.

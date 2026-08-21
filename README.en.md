# Jnotes2Hinote

Chinese documentation: [README.md](README.md)

Convert **Jideos Jnotes / 云记 `.Jnotes`** notebooks into **Huawei Notes / 华为笔记 `.hinote`** while preserving native editable handwriting within the currently validated format range.

> **Validated compatibility:** Jnotes **3.2.3.2** → Huawei Notes **15.0.14.295**. Other versions are currently unverified.

## What v1.1.0 preserves

- Multi-page notebook structure
- Native editable Huawei PENCILENGINE handwriting
- Stroke coordinates and per-point pressure
- Stroke color using Huawei's BGR float layout
- Ballpoint, fountain/steel pen, HB pencil and highlighter mappings used by the validation notebook
- Device-calibrated highlighter width and opacity
- Supported lines, curves, rectangles and circles mapped to native editable Huawei geometry where possible
- Some translucent smooth curves mapped to native Huawei highlighter strokes while preserving transparency
- Images and image-based stickers
- Basic editable text boxes
- Cover images
- Huawei native paper backgrounds

## v1.1.0: no Huawei reference note required

Starting with v1.1.0, the converter generates the handwriting and geometry data required by Huawei Notes 15.0.14.295 directly in code. You no longer need to export `reference.hinote` or `shape-reference.hinote` from Huawei Notes.

The legacy v1.0.0 conversion core remains unchanged in `src/jnotes2hinote/converter_v1_0_0.py`.

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
jnotes2hinote input.Jnotes output.hinote
```

Or:

```bash
python -m jnotes2hinote input.Jnotes output.hinote
```

Write a JSON conversion report:

```bash
jnotes2hinote input.Jnotes output.hinote --report conversion-report.json
```

Convert only the first 5 pages while testing:

```bash
jnotes2hinote input.Jnotes test.hinote --pages 5
```

## Known limitations

- **Paper tape:** no confirmed Huawei native equivalent; v1.1.0 skips it rather than rasterizing it silently.
- **Audio:** Jnotes audio and Huawei attachment storage were studied, but audio conversion is not enabled in v1.1.0.
- **Text layout:** text remains editable, but font appearance, wrapping and line spacing may differ.
- **Ordinary pen widths:** highlighter width is device-calibrated; the final visual thickness of other pen types may differ from the source.
- **Geometry widths:** supported geometry uses device-validated fixed width tiers (2, 4 or 8); every source width cannot be matched exactly.
- **Compatibility:** only Jnotes 3.2.3.2 → Huawei Notes 15.0.14.295 is device-tested.

Read [docs/limitations.md](docs/limitations.md) before converting important notebooks, and keep backups of the original files.

## Reverse-engineering notes

- [Jnotes format](docs/format-jnotes.md)
- [Huawei `.hinote` / PENCILENGINE format](docs/format-hinote.md)
- [Mapping rules](docs/mapping.md)
- [Compatibility](docs/compatibility.md)
- [Reverse-engineering timeline](docs/reverse-engineering.md)
- [v1.0.0 validation summary](docs/validation-v1.0.0.md)
- [v1.1.0 validation summary](docs/validation-v1.1.0.md)

## Safety / backups

Always keep the original `.Jnotes` and export/backup your Huawei Notes before importing converted files. This is an unofficial interoperability project based on reverse engineering, not a Huawei or Jideos product.

## Development

```bash
pip install -e ".[dev]"
pytest
```

The versioned cores are kept separately:

```text
src/jnotes2hinote/converter_v1_0_0.py  # frozen legacy core that uses reference files
src/jnotes2hinote/converter_v1_1_0.py  # current self-contained core
```

Add a new versioned core for future behavior changes; do not rewrite the frozen v1.0.0 core.

## License

MIT. See [LICENSE](LICENSE).

## Disclaimer

This project is independent and unofficial. It is not affiliated with, endorsed by, or sponsored by Jideos or Huawei. Product and company names are used only to describe file-format interoperability.

# Jnotes2Hinote

Chinese documentation: [README.md](README.md)

Convert **Jideos Jnotes / 云记 `.Jnotes`** notebooks into **Huawei Notes / 华为笔记 `.hinote`** while preserving native editable handwriting within the reverse-engineered format range.

> **Device-tested compatibility baseline:** Jnotes **3.2.3.2** → Huawei Notes **15.0.14.295**. Other versions are currently unverified.

## What v1.1.1 supports

- Multi-page notebook structure
- Native editable Huawei PENCILENGINE handwriting
- Stroke coordinates and per-point pressure
- Stroke color using Huawei's BGR float layout
- Ballpoint, fountain/steel pen, HB pencil and highlighter mappings used by the validation notebook
- Device-calibrated highlighter width and opacity
- Supported Jnotes type 6 / type 7 geometry as Huawei geometry-style PENCILENGINE strokes
- Highlighter-derived translucent type 6/subtype 12 curves as native Huawei highlighter strokes
- Images and image-based stickers
- Basic editable text boxes
- Cover images
- Huawei native paper backgrounds

## v1.1.1: no Huawei reference note required

The converter generates the validated Huawei Notes 15.0.14.295 PENCILENGINE header, style records, point records, stroke links and supported geometry structures directly in code. You no longer need to create `reference.hinote` or `shape-reference.hinote`.

The legacy reference-based v1.0.0 implementation remains unchanged in `src/jnotes2hinote/converter_v1_0_0.py`.

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

- **Paper tape:** no confirmed Huawei native equivalent; v1.1.1 skips it rather than rasterizing it silently.
- **Audio:** Jnotes audio storage and Huawei generic attachment storage were reverse-engineered, but audio conversion is not enabled in v1.1.1.
- **Typography:** text remains editable, but font metrics, wrapping and line spacing may differ.
- **Pen widths:** highlighter width is device-calibrated. Ordinary pen-family visual width equivalence is not fully calibrated.
- **Geometry widths:** ordinary opaque type 6/type 7 geometry uses the same direct width mapping as ordinary handwriting: Jnotes `d` is written directly to Huawei `style+84`, including fractional values.
- **Compatibility:** only Jnotes 3.2.3.2 → Huawei Notes 15.0.14.295 is device-tested.

Read [docs/limitations.md](docs/limitations.md) before converting important notebooks and keep backups of the original files.

## Reverse-engineering notes

- [Jnotes format](docs/format-jnotes.md)
- [Huawei `.hinote` / PENCILENGINE format](docs/format-hinote.md)
- [Mapping rules](docs/mapping.md)
- [Compatibility](docs/compatibility.md)
- [Reverse-engineering timeline](docs/reverse-engineering.md)
- [v1.0.0 validation summary](docs/validation-v1.0.0.md)
- [v1.1.0 validation summary](docs/validation-v1.1.0.md)
- [v1.1.1 validation summary](docs/validation-v1.1.1.md)

## Safety / backups

Always keep the original `.Jnotes` file and export or back up your Huawei Notes before importing converted files. This is an unofficial interoperability project based on reverse engineering, not a Huawei or Jideos product.

## Development

```bash
pip install -e ".[dev]"
pytest
```

Versioned cores are kept separately:

```text
src/jnotes2hinote/converter_v1_0_0.py  # frozen legacy reference-based core
src/jnotes2hinote/converter_v1_1_0.py  # historical v1.1.0 self-contained core
src/jnotes2hinote/converter_v1_1_1.py  # current self-contained core
```

Add a new versioned core for future behavior changes; do not rewrite historical versioned cores.

## License

MIT. See [LICENSE](LICENSE).

## Disclaimer

This project is independent and unofficial. It is not affiliated with, endorsed by, or sponsored by Jideos or Huawei. Product and company names are used only to describe file-format interoperability.

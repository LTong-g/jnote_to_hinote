# Jnotes2Hinote

Convert **Jideos Jnotes / 云记 `.Jnotes` notebooks** into **Huawei Notes `.hinote` files**, while preserving editable handwriting, images and text within the supported format range.

> **Currently device-tested compatibility:** Jnotes 3.2.3.2 → Huawei Notes 15.0.14.295. Other versions are unverified and may produce different results.

Current release: **v1.3.0**. In addition to command-line batch conversion, it provides a desktop GUI for everyday users.

Chinese documentation: [README.md](README.md)

## What this project is for

If you have a `.Jnotes` file exported from Jnotes and want to continue viewing or editing it in Huawei Notes, use this project to create a `.hinote` file and then import it into Huawei Notes.

## What is converted

- Multi-page notebooks
- Editable handwriting, including common pen types, colors and per-point pressure
- Some lines, curves, rectangles and circles
- Images, image-based stickers and covers
- Basic text boxes
- Common blank, ruled, dotted and grid paper backgrounds

The result is saved as a Huawei Notes file rather than flattening the whole page into a single image.

## Installation

Python 3.10 or newer is required. Open a terminal in the project root.

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
```

Start the desktop GUI:

```bash
jnotes2hinote-gui
```

You can also start it as a Python module:

```bash
python -m jnotes2hinote.gui
```

The GUI supports multiple `.Jnotes`/`.jnote` files, folders and TXT path lists, optional recursive scanning, progress, results and error logs. See the [GUI guide](docs/gui.en.md) for details.

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Convert a notebook

Basic usage:

```bash
jnotes2hinote input.Jnotes output.hinote
```

You can also run it as a Python module:

```bash
python -m jnotes2hinote input.Jnotes output.hinote
```

## Batch conversion

When the input is a directory, the default behavior converts `.Jnotes`/`.jnote` files directly inside that directory. The output argument must be a directory:

```bash
jnotes2hinote notes output
```

To recursively convert files in the directory and all of its subdirectories:

```bash
jnotes2hinote notes output --recursive
```

You can also provide multiple files or directories in one command:

```bash
jnotes2hinote notes-a notes-b one.Jnotes output
```

Alternatively, provide a text file containing one input path per line. Blank lines and lines beginning with `#` are ignored. Relative paths in the list are resolved relative to the list file's directory:

```text
notes-a
notes-b/meeting.Jnotes
```

```bash
jnotes2hinote paths.txt output --recursive
```

Batch conversion continues with the remaining paths when a path cannot be read, is invalid, or fails to convert. Errors are printed to the terminal and included in the batch report when `--report` is used. Output files use the source filename; duplicate names receive an automatic numeric suffix.

Write a JSON conversion report:

```bash
jnotes2hinote input.Jnotes output.hinote --report conversion-report.json
```

Convert only the first 5 pages for a quick test:

```bash
jnotes2hinote input.Jnotes test.hinote --pages 5
```

The converter reads the input file and writes to the output path you specify. Keep the original `.Jnotes` file, and do not use the same path for input and output.

## Import into Huawei Notes

After conversion, import the generated `.hinote` file into Huawei Notes and check important pages, images, text and handwriting. Before converting a complete notebook, use `--pages` to test a small number of pages first.

## Important limitations

- Only Jnotes 3.2.3.2 → Huawei Notes 15.0.14.295 is currently device-tested.
- Paper tape objects are not currently converted.
- Audio is not currently converted.
- Text remains editable, but fonts, wrapping and line spacing may differ from the source.
- Ordinary pen widths may not look exactly the same as in the source notebook.
- Some shapes or special objects may not retain their original appearance completely.
- Back up the original `.Jnotes` file and your existing Huawei Notes before importing important notebooks.

This is an unofficial interoperability tool based on reverse engineering, not a Huawei or Jideos product. Test with copies before processing important material.

## Technical documentation

Most users can start with the installation and conversion steps above. The following documents are for readers and developers who want more information about formats, compatibility or conversion details:

- [Limitations and compatibility](docs/limitations.md)
- [Compatibility record](docs/compatibility.md)
- [GUI guide](docs/gui.en.md)
- [Jnotes file format](docs/format-jnotes.md)
- [Huawei Notes file format](docs/format-hinote.md)
- [Conversion mapping rules](docs/mapping.md)
- [v1.0.0 validation summary](docs/validation-v1.0.0.md)
- [v1.1.0 validation summary](docs/validation-v1.1.0.md)
- [v1.1.1 validation summary](docs/validation-v1.1.1.md)

## Development

Install development dependencies and run the tests:

```bash
pip install -e ".[dev]"
pytest
```

Before contributing format research or code, read [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT. See [LICENSE](LICENSE).

# Jnotes2Hinote

Convert Jnotes notebooks (`.Jnotes` / `.jnote`) into Huawei Notes `.hinote` files, so you can import them into Huawei Notes and continue viewing and editing them.

The currently device-tested version combination is **Jnotes 3.2.3.2 → Huawei Notes 15.0.14.295**. Other versions have not been verified and may produce different results.

Current version: **v1.5.0**. The project provides a desktop GUI as well as command-line batch conversion.

Chinese version: [README.md](README.md)

## Recommended: use the desktop GUI

If you simply want to convert notebooks, use the GUI. It can add multiple files, folders or a text path list, and shows conversion progress, successful results and errors.

### Using the Windows packaged version

If you have the Windows packaged version, run:

```text
dist/Jnotes2Hinote/Jnotes2Hinote.exe
```

Keep the other files in the `Jnotes2Hinote` folder. Do not copy only the exe file. The packaged version does not require a separate Python installation.

### Running from source

Python 3.10 or newer is required. Open a terminal in the project root and run:

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
jnotes2hinote-gui
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python -m jnotes2hinote.gui
```

### Basic workflow

1. Click “Add files”, “Add folder” or “Add TXT list”, or drop those inputs onto the input list.
2. Enable recursive scanning if files in all subfolders should be included.
3. Choose an output folder, select how to handle duplicate names, and start the conversion.

The GUI uses a two-column layout: inputs and output settings are on the left, while conversion results and the run log are on the right. Drag the splitters to adjust the available space.

The GUI recognizes `.Jnotes` and `.jnote` files. A TXT list contains one file or folder path per line; blank lines and lines beginning with `#` are ignored. If a path cannot be read or a file fails to convert, the error is recorded and the remaining paths continue to be processed.

See the [GUI guide](docs/gui.en.md) for complete instructions.

## Command-line usage

The command line is useful for scripts and batch jobs. After installing the project, use the `jnotes2hinote` command. You can also replace `jnotes2hinote` in the examples below with `python -m jnotes2hinote`.

### Convert one file

```bash
jnotes2hinote input.Jnotes output.hinote
```

### Convert a folder

By default, only files directly inside the folder are processed:

```bash
jnotes2hinote notes output
```

To include all subfolders, add `--recursive`:

```bash
jnotes2hinote notes output --recursive
```

### Provide multiple paths

You can mix files and folders in one command:

```bash
jnotes2hinote notes-a notes-b meeting.Jnotes output
```

### Use a TXT path list

Write one file or folder path per line:

```text
notes-a
notes-b/meeting.Jnotes
```

Then pass the TXT file as an input:

```bash
jnotes2hinote paths.txt output --recursive
```

Relative paths in the list are resolved relative to the folder containing the TXT file. Batch conversion skips invalid paths, unreadable paths and files that fail to convert, then continues with the remaining inputs. Errors are printed in the terminal and can also be written to a report.

### Common options

Write a JSON conversion report:

```bash
jnotes2hinote notes output --recursive --report conversion-report.json
```

Convert the first 5 pages as a quick test:

```bash
jnotes2hinote input.Jnotes test.hinote --pages 5
```

For batch conversion, the output argument must be a folder. Output files use the source filename by default; the command-line converter adds a numeric suffix when names conflict. Do not use the same path for input and output, and keep the original `.Jnotes` files.

## Converted content and limitations

Within the supported range, the result keeps editable Huawei Notes content instead of flattening each page into a single image. Current support includes:

- Multi-page notebooks
- Original PDF pages for PDF-backed notebooks; PDF content is not rasterized
- Editable handwriting, including common pen types, colors and per-point pressure
- Some lines, curves, rectangles and circles
- Images, image-based stickers and page thumbnails
- Basic text boxes
- Common blank, ruled, dotted and grid paper backgrounds

The following content may not be converted or may look different from the source:

- Paper tape objects and audio are not currently converted
- PDF notebooks depend on Huawei Notes' imported-PDF support; encrypted PDFs and mixed multi-PDF pages are not device-tested yet
- Text remains editable, but fonts, wrapping and line spacing may change
- Ordinary pen widths may look different from the source
- Some shapes or special objects may not retain their original appearance completely

After conversion, check important pages, images, text and handwriting in Huawei Notes. Back up the original notebooks and test with copies before processing important material.

This is an unofficial interoperability tool based on reverse engineering, not an official Huawei or Jideos product.

## Further documentation

- [GUI guide](docs/gui.en.md)
- [Limitations and compatibility](docs/limitations.md)
- [Compatibility record](docs/compatibility.md)
- [Jnotes file format](docs/format-jnotes.md)
- [Huawei Notes file format](docs/format-hinote.md)
- [Conversion mapping rules](docs/mapping.md)
- [v1.0.0 validation summary](docs/validation-v1.0.0.md)
- [v1.1.0 validation summary](docs/validation-v1.1.0.md)
- [v1.1.1 fix validation summary](docs/validation-v1.1.1.md)
- [v1.1.2 fix validation summary](docs/validation-v1.1.2.md)
- [v1.2.0 PDF conversion validation summary](docs/validation-v1.2.0.md)

## Development

Install development dependencies and run the tests:

```bash
pip install -e ".[dev]"
pytest
```

Before contributing format research or code, read [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT. See [LICENSE](LICENSE).

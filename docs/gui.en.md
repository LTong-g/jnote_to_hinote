# GUI guide

## Start the GUI

After installing the project, run:

```bash
jnotes2hinote-gui
```

You can also run:

```bash
python -m jnotes2hinote.gui
```

The GUI starts in Simplified Chinese and can be switched to English from the top-right language selector.

## Add inputs

The input area accepts three source types:

- **Files**: one or more `.Jnotes`/`.jnote` files;
- **Folders**: direct children are scanned by default;
- **TXT lists**: one file or folder path per line.

Blank lines and lines beginning with `#` are ignored. Relative paths in a TXT list are resolved relative to the list file. Sources can be mixed, and the same file is converted only once.

Enable **Include files in subdirectories** to recursively scan folders found directly in the input list or in a TXT list.

## Output settings

The output directory receives the generated `.hinote` files. For name conflicts, choose one of these strategies:

- **Add numeric suffix**: create `note.hinote`, `note_2.hinote`, and so on;
- **Skip existing files**: do not replace files that already exist;
- **Overwrite existing files**: replace existing files, while duplicate inputs in the same batch still receive suffixes.

Set **Pages** to `0` to convert all pages. A positive value converts only the first few pages for a quick check.

When the JSON report option is enabled, the default path is `conversion_report.json` in the output directory. The report contains successful, failed and skipped files together with conversion results.

## Conversion flow

After clicking **Start conversion**, the application scans all inputs and shows the number of discovered files. If a path is missing, unreadable or contains no supported files, the problem is shown and the application asks whether the remaining valid files should continue.

Conversion runs in a background thread, so the window remains responsive. The result table and log show:

- the current file;
- generated output files;
- failed or skipped files and their reasons;
- overall progress.

A failure for one file does not stop the remaining files. Clicking **Stop** requests a safe stop after the current file; existing output files are kept.

## Remembered settings

The application remembers the recent output directory, recursive-scan choice, page limit, report settings, conflict strategy, language and window size. Settings are stored in the user configuration directory, not in the repository, and note contents are never uploaded.

## Windows build

Install the optional build dependency and run:

```powershell
./scripts/build_windows.ps1
```

The script produces a no-console Windows application directory. Run `dist/Jnotes2Hinote/Jnotes2Hinote.exe` and keep the runtime files in the `dist/Jnotes2Hinote` directory. The packaged application uses the current v1.2.0 conversion core.

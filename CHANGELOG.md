# Changelog

All notable changes to this project are documented here.

## [1.0.0] - 2026-08-21

First device-tested public release.

### Validation environment

- Source app: **Jideos Jnotes / 云记 3.2.3.2**
- Target app: **Huawei Notes / 华为笔记 15.0.14.295**
- Validation method: generated `.hinote` files were imported and checked on a Huawei device.

### Supported in v1.0.0

- Multi-page `.Jnotes` → `.hinote`
- Native editable PENCILENGINE handwriting
- Ballpoint pen, fountain/steel pen, HB pencil and highlighter mappings
- BGR color conversion used by Huawei Notes 15.0.14.295
- Device-calibrated highlighter width and render/UI opacity
- Jnotes type 6 / type 7 geometry for the subtypes exercised by the test notebook
- Images and image-based stickers
- Basic editable text boxes
- Cover image migration
- Native Huawei blank / horizontal / dotted / grid paper templates
- SHA-256 metadata rebuilding (`fileMdStr`, `fileNameMdStr`, `detailFileMap`)

### Known limitations

- Paper tape has no confirmed Huawei native equivalent and is skipped by the frozen v1.0.0 core.
- Audio format was reverse-engineered, but audio conversion is not enabled in v1.0.0.
- Text layout can differ in font metrics, line spacing and wrapping.
- Ordinary pen-width visual equivalence is not fully calibrated across all pen families.
- Compatibility with app versions other than the validated pair is unverified.

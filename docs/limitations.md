# Limitations

## Paper tape

Jnotes paper tape is structurally distinct from normal handwriting and supports visual styles such as solid/grid/hearts/dots and opaque/outline-like modes. No Huawei native equivalent has been identified.

The frozen v1.0.0 core **skips paper tape** and records the count in the JSON report. A future release may offer an explicit rasterization fallback.

## Audio

Jnotes `AUDIO_EX` and Huawei generic attachment storage were investigated, but audio conversion is intentionally disabled in v1.0.0 because it has not completed the same end-to-end device-validation bar as handwriting.

## Text fidelity

Text is migrated as editable text, but these can differ:

- font family availability;
- line spacing;
- wrapping;
- exact box height;
- baseline metrics.

## Ordinary pen-width fidelity

The highlighter has a device-calibrated mapping. Ordinary pen-family visual widths were not exhaustively calibrated across the full UI range. v1.0.0 preserves the current tested internal-width behavior rather than claiming perfect cross-engine visual equivalence.

## Geometry coverage

Native geometry mappings are implemented for the subtypes present in the validated large notebook. Other Jnotes type 6/type 7 subtypes use editable ink-path fallback.

## Version dependence

All byte offsets and behavior are based on Jnotes 3.2.3.2 and Huawei Notes 15.0.14.295. A different app release may change the format.

## No official support

This is an unofficial reverse-engineered interoperability tool. Keep backups and test a few pages before importing an important full notebook.

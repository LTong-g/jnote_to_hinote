# v1.0.0 validation summary

The v1.0.0 implementation was exercised against a large real-world Jnotes 3.2.3.2 notebook and structurally regenerated for Huawei Notes 15.0.14.295.

Validation dataset summary (content not distributed):

- 171 pages
- 44,828 ink/geometry strokes
- 48 images/stickers
- 35 text boxes
- 245 Jnotes type 6/type 7 geometry records
- no paper tape in the final large validation notebook
- no audio in the final large validation notebook

Structural smoke test of the repository converter reproduced:

- 171 output pages
- 44,828 converted ink/geometry records
- 44,583 ordinary pen records
- 245 native geometry records
- 48 images
- 35 text boxes
- native paper-template distribution used by the validation notebook:
  - `base1`: 133 pages
  - `base4`: 25 pages
  - `base5`: 9 pages
  - `base3`: 3 pages
  - `base2`: 1 page

Device-testing during the reverse-engineering process verified that converted PENCILENGINE strokes can be displayed, selected and erased in Huawei Notes. A 688-stroke page was used as an important chain-link stress test before the whole-notebook migration.

The validation notebook itself is intentionally not committed to this repository.

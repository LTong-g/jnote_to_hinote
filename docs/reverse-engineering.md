# Reverse-engineering notes and validation milestones

This document records the main findings behind v1.0.0 so that future changes can be evaluated against known device behavior.

## 1. Jnotes is not raster-only

The tested `.Jnotes` archive contains plaintext stroke JSON with x/y/pressure, color, width and tool type. This made native handwriting migration possible.

## 2. First native handwriting proof of concept

A generated `.hinote` containing converted Jnotes handwriting was imported into Huawei Notes. The converted strokes could be selected with lasso and erased, proving that migration into Huawei native PENCILENGINE records was viable.

## 3. Newer 108-byte style layout

The target Huawei version used a 108-byte style record rather than the shorter layout assumed by some older public parsers.

## 4. The chain-pointer bug

Early generated pages physically contained hundreds of blocks but Huawei stopped rendering at an existing END boundary. Later, a whole-book build showed only the first stroke of almost every page.

The critical finding was that both the file header and every stroke tail form a linked structure. The root and continuation sizes must match the next stroke's point count:

```text
header+148 = first_count × 36 + 140
header+180 = first_count × 36 + 20

tail+16 = next_count × 36 + 140
tail+48 = next_count × 36 + 20
```

After rebuilding those links, a 688-stroke page and then the 171-page notebook displayed correctly.

## 5. BGR color order

Writing source RGB into `style+64/+68/+72` produced swapped colors. Controlled Huawei samples showed that the target app interprets them as B, G, R.

## 6. Highlighter opacity has two fields

Setting only `style+80` changed the property shown after selection, but rendering stayed at the old opacity. Device tests showed that `style+76` affects actual rendering while `style+80` reflects the UI/selection property. v1.0.0 writes both.

## 7. Highlighter width calibration

On a controlled page, Jnotes highlighter `d=6` visually matched Huawei highlighter width 32. The retained v1.0.0 rule is:

```text
Huawei width = Jnotes d × 16/3
```

## 8. Geometry

Controlled Jnotes samples separated:

- type 6: handwriting that was recognized/regularized after drawing;
- type 7: explicit geometry-tool shapes.

A Huawei native-shape export showed that geometry is also PENCILENGINE data, generally using ballpoint rendering and compact canonical point sets. Native circle/line experiments remained selectable after conversion.

An A/B test that removed the extra shape UUID index from half the circles showed no user-visible behavior difference; geometry in Huawei also becomes fixed after creation and does not expose editable construction handles again.

## 9. Paper templates

A controlled Huawei note established the `base1`–`base6` background IDs. A controlled Jnotes notebook established how paper template families and size parameters are stored, enabling direct native background mapping instead of raster fallback for the standard templates used by the validated notebook.

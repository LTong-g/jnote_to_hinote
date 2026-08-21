# Compatibility

## Device-tested matrix

| Source app | Source version | Target app | Target version | Status |
|---|---:|---|---:|---|
| Jideos Jnotes / 云记 | **3.2.3.2** | Huawei Notes / 华为笔记 | **15.0.14.295** | **Device-tested** |
| Jnotes | other | Huawei Notes | 15.0.14.295 | Unverified |
| Jnotes | 3.2.3.2 | Huawei Notes | other | Unverified |
| Jnotes | other | Huawei Notes | other | Unverified |

The binary layout described in this repository should not be assumed stable across app versions.

## What “device-tested” means

The reverse-engineering process generated `.hinote` files and imported them into Huawei Notes on a Huawei device. Tests included:

- native editable strokes that could be selected and erased;
- hundreds of strokes in one PENCILENGINE page;
- a 171-page notebook with 44,828 strokes;
- BGR color conversion;
- highlighter width and opacity;
- images, text and paper backgrounds;
- Jnotes type 6 / type 7 geometry represented with Huawei geometry-style PENCILENGINE records.

This is not the same as exhaustive compatibility testing across devices or firmware builds.

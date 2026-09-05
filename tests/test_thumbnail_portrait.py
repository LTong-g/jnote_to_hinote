import io

from PIL import Image, JpegImagePlugin

from jnotes2hinote.thumbnail import (
    THUMBNAIL_MAX_EDGE,
    render_regular_thumbnail,
    thumbnail_dimensions,
)


def test_native_thumbnail_dimensions_match_observed_hinote_samples():
    assert thumbnail_dimensions(675, 1080) == (675, 1080)
    assert thumbnail_dimensions(0.706, 1) == (762, 1080)


def test_regular_thumbnail_uses_native_resolution_and_jpeg_quality():
    thumbnail = render_regular_thumbnail(
        page_width=1240,
        page_height=1754,
        strokes=[{
            "c": {
                "a": 2,
                "c": -16777216,
                "d": 3,
                "k": [{"x": 20, "y": 30}, {"x": 1100, "y": 1500}],
            },
        }],
        images=[],
        texts=[{"x": 40, "y": 100, "g": 40, "e": "中文 English"}],
        cover=None,
    )

    image = Image.open(io.BytesIO(thumbnail))
    image.load()
    assert image.format == "JPEG"
    assert image.size == (round(1240 / 1754 * THUMBNAIL_MAX_EDGE), THUMBNAIL_MAX_EDGE)
    assert JpegImagePlugin.get_sampling(image) == 2
    assert {value for table in image.quantization.values() for value in table} == {1}
    assert image.convert("L").getextrema()[0] < 240


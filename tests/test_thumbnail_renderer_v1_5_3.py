import io

from PIL import Image, JpegImagePlugin

from jnotes2hinote.thumbnail_renderer_v1_5_3 import (
    THUMBNAIL_MAX_EDGE,
    render_regular_thumbnail,
    thumbnail_dimensions,
)


def test_thumbnail_longest_edge_is_limited_for_both_orientations():
    assert thumbnail_dimensions(675, 1080) == (675, 1080)
    assert thumbnail_dimensions(0.706, 1) == (762, 1080)
    assert thumbnail_dimensions(4, 3) == (1080, 810)
    assert thumbnail_dimensions(1.4142856382232933, 1) == (1080, 764)


def test_regular_thumbnail_keeps_native_quality_with_longest_edge_limit():
    thumbnail = render_regular_thumbnail(
        page_width=1754,
        page_height=1240,
        strokes=[{
            "c": {
                "a": 2,
                "c": -16777216,
                "d": 3,
                "k": [{"x": 20, "y": 30}, {"x": 1500, "y": 1100}],
            },
        }],
        images=[],
        texts=[{"x": 40, "y": 100, "g": 40, "e": "中文 English"}],
        cover=None,
    )

    image = Image.open(io.BytesIO(thumbnail))
    image.load()
    assert image.format == "JPEG"
    assert image.size == (THUMBNAIL_MAX_EDGE, round(1240 / 1754 * THUMBNAIL_MAX_EDGE))
    assert JpegImagePlugin.get_sampling(image) == 2
    assert {value for table in image.quantization.values() for value in table} == {1}
    assert image.convert("L").getextrema()[0] < 240
